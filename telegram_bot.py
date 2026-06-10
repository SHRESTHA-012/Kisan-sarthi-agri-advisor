
import logging
import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from api import telegram_router, session_manager

# ── Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agriadvisor.telegram")


# ── Auto-register webhook ──────────────────────────────────────────────────────

async def _get_ngrok_url() -> str | None:
    """
    Ask ngrok's local API for the current public HTTPS tunnel URL.
    ngrok exposes this at http://localhost:4040/api/tunnels while running.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://localhost:4040/api/tunnels")
            tunnels = resp.json().get("tunnels", [])
            for tunnel in tunnels:
                url = tunnel.get("public_url", "")
                if url.startswith("https://"):
                    return url
    except Exception as e:
        logger.warning("Could not reach ngrok API: %s", e)
    return None


async def _register_webhook(public_url: str) -> bool:
    """Register the webhook URL with Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    webhook_url = f"{public_url}/webhook/telegram"
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

    payload = {
        "url": webhook_url,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True,
    }
    if secret:
        payload["secret_token"] = secret

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json=payload,
            )
        result = resp.json()
        if result.get("ok"):
            logger.info("✅ Webhook registered: %s", webhook_url)
            return True
        else:
            logger.error("❌ Webhook registration failed: %s", result)
            return False
    except Exception as e:
        logger.error("❌ Webhook registration error: %s", e)
        return False


async def _auto_register_webhook():
    """
    Try to detect ngrok and auto-register webhook.
    Retries a few times in case ngrok hasn't fully started yet.
    """
    for attempt in range(1, 4):
        logger.info("🔍 Looking for ngrok tunnel (attempt %d/3)…", attempt)
        url = await _get_ngrok_url()
        if url:
            logger.info("🌐 ngrok tunnel found: %s", url)
            await _register_webhook(url)
            return
        await asyncio.sleep(3)  # wait and retry

    logger.warning(
        "⚠️  ngrok tunnel not found. Register webhook manually:\n"
        "    GET http://localhost:8000/webhook/telegram/set"
        "?webhook_url=https://<your-ngrok-url>/webhook/telegram"
    )


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌾 AgriAdvisor Telegram Bot starting…")

    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        logger.warning("⚠️  TELEGRAM_BOT_TOKEN is not set in .env!")

    # Auto-register webhook if ngrok is running
    asyncio.create_task(_auto_register_webhook())

    async def _cleanup():
        while True:
            await asyncio.sleep(600)
            n = session_manager.cleanup_expired()
            if n:
                logger.info("Cleaned %d expired sessions", n)

    task = asyncio.create_task(_cleanup())
    yield
    task.cancel()
    logger.info("Telegram Bot shut down.")


# ── App

bot = FastAPI(
    title="AgrAdvisor Bihar — Telegram Bot",
    version="1.0.0",
    lifespan=lifespan,
)

bot.include_router(telegram_router)


@bot.get("/")
def root():
    return {"service": "AgrAdvisor Telegram Bot", "status": "running"}


@bot.get("/health")
def health():
    return {
        "status": "ok",
        "sessions": session_manager.stats()["active_sessions"],
        "token_set": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
    }


# ── Run 

if __name__ == "__main__":
    uvicorn.run(
        "telegram_bot:bot",
        host="0.0.0.0",
        port=int(os.getenv("TELEGRAM_PORT", 8000)),
        reload=True,
    )
