import os
import logging
import httpx
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

from .message_router import route_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Telegram"])

# ── Config ─────────────────────────────────────────────────────────────────────

BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")  # Optional extra security

_processed_update_ids = set()
_MAX_TRACKED_IDS = 1000


# ── Webhook endpoint ───────────────────────────────────────────────────────────

@router.post("/telegram")
async def telegram_webhook(request: Request, background: BackgroundTasks):
    """
    Telegram sends all updates here as POST JSON.
    We ack immediately (200) and process in background to avoid timeouts.
    """
    # Optional: verify secret token header set during setWebhook
    if WEBHOOK_SECRET:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret")

    update = await request.json()
    logger.debug("Telegram update received: %s", update)

    background.add_task(_process_update, update)
    return {"ok": True}


# ── Setup endpoint ─────────────────────────────────────────────────────────────

@router.get("/telegram/set")
async def set_webhook(webhook_url: str):
    """
    Register the webhook URL with Telegram.
    Call once: GET /webhook/telegram/set?webhook_url=https://yourdomain.com/webhook/telegram
    """
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not set")

    payload = {
        "url": webhook_url,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True,
    }
    if WEBHOOK_SECRET:
        payload["secret_token"] = WEBHOOK_SECRET

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{TELEGRAM_API}/setWebhook", json=payload)
    result = resp.json()
    logger.info("setWebhook response: %s", result)
    return result


@router.get("/telegram/info")
async def webhook_info():
    """Check currently registered webhook."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{TELEGRAM_API}/getWebhookInfo")
    return resp.json()


@router.delete("/telegram/delete")
async def delete_webhook():
    """Remove the webhook (switch back to polling mode)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{TELEGRAM_API}/deleteWebhook")
    return resp.json()


# ── Core update processor ──────────────────────────────────────────────────────

async def _process_update(update: dict):
    """
    Parse the Telegram Update object and call route_message.
    Handles: text, photo, voice messages.
    """
    update_id = update.get("update_id")
    if update_id is not None:
        if update_id in _processed_update_ids:
            logger.info("Duplicate update_id %s — skipping", update_id)
            return
        _processed_update_ids.add(update_id)
        if len(_processed_update_ids) > _MAX_TRACKED_IDS:
            _processed_update_ids.clear()

    try:
        message = update.get("message") or update.get("edited_message")
        if not message:
            logger.debug("No message in update (callback_query?), skipping.")
            return

        chat_id  = message["chat"]["id"]
        user     = message.get("from", {})
        user_id  = user.get("id", chat_id)
        username = user.get("username") or user.get("first_name")

        # ── Determine message type ─────────────────────────────────────────
        msg_type = "text"
        content  = None
        caption  = message.get("caption")

        if "text" in message:
            msg_type = "text"
            content  = message["text"]

        elif "photo" in message:
            msg_type = "photo"
            # Telegram sends multiple sizes; pick the largest
            file_id  = message["photo"][-1]["file_id"]
            content  = await _download_file(file_id)

        elif "voice" in message:
            msg_type = "voice"
            file_id  = message["voice"]["file_id"]
            content  = await _download_file(file_id)

        else:
            # Unsupported message type (sticker, document, etc.)
            await _send_message(chat_id, "🙏 कृपया टेक्स्ट, फोटो या आवाज़ संदेश भेजें।")
            return

        # ── Route and reply ────────────────────────────────────────────────
        reply = await route_message(
            user_id=user_id,
            username=username,
            message_type=msg_type,
            content=content,
            caption=caption,
        )

        if reply:
            await _send_message(chat_id, reply)

    except Exception as exc:
        logger.exception("PROCESS_UPDATE EXCEPTION: %s", exc)
        import traceback
        traceback.print_exc()

        try:
          chat_id = update.get("message", {}).get("chat", {}).get("id")
          if chat_id:
            await _send_message(chat_id, "⚠️ Kuch gadbad hui, thodi der me try karein.")
        except Exception:
           pass


# ── Telegram API helpers ───────────────────────────────────────────────────────

async def _send_message(chat_id: int, text: str, parse_mode: str = "Markdown"):
    """Send a text message back to the farmer."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set — cannot send message")
        return

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
            if not resp.json().get("ok"):
                logger.warning("sendMessage failed: %s", resp.json())
    except Exception as exc:
        logger.error("sendMessage exception: %s", exc)


async def _send_photo(chat_id: int, photo_bytes: bytes, caption: Optional[str] = None):
    """Send an image back (e.g. weather map, crop chart)."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            files  = {"photo": ("image.jpg", photo_bytes, "image/jpeg")}
            data   = {"chat_id": str(chat_id)}
            if caption:
                data["caption"] = caption
            await client.post(f"{TELEGRAM_API}/sendPhoto", data=data, files=files)
    except Exception as exc:
        logger.error("sendPhoto exception: %s", exc)


async def _download_file(file_id: str) -> bytes:
    """Download a file (photo/voice) from Telegram servers."""
    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: get file path
        resp = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        file_path = resp.json()["result"]["file_path"]

        # Step 2: download actual content
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        dl = await client.get(file_url)
        return dl.content
