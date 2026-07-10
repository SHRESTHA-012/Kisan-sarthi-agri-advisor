"""
Telegram bot server — FastAPI app + lifespan.
Entry point: main_bot.py at project root.
"""
import logging
import asyncio
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from src.api import telegram_router, session_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agriadvisor.telegram")


# ── Webhook auto-registration ──────────────────────────────────────────────────

async def _get_ngrok_url() -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp    = await client.get("http://localhost:4040/api/tunnels")
            tunnels = resp.json().get("tunnels", [])
            for tunnel in tunnels:
                url = tunnel.get("public_url", "")
                if url.startswith("https://"):
                    return url
    except Exception as e:
        logger.warning("Could not reach ngrok API: %s", e)
    return None


async def _register_webhook(public_url: str) -> bool:
    token       = os.getenv("TELEGRAM_BOT_TOKEN", "")
    webhook_url = f"{public_url}/webhook/telegram"
    secret      = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

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
        logger.error("❌ Webhook registration failed: %s", result)
        return False
    except Exception as e:
        logger.error("❌ Webhook registration error: %s", e)
        return False


async def _auto_register_webhook():
    for attempt in range(1, 4):
        logger.info("🔍 Looking for ngrok tunnel (attempt %d/3)…", attempt)
        url = await _get_ngrok_url()
        if url:
            logger.info("🌐 ngrok tunnel found: %s", url)
            await _register_webhook(url)
            return
        await asyncio.sleep(3)

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


# ── App ────────────────────────────────────────────────────────────────────────

bot = FastAPI(
    title="AgriAdvisor Bihar — Telegram Bot",
    version="1.0.0",
    lifespan=lifespan,
)

bot.include_router(telegram_router)


@bot.get("/")
def root():
    return {"service": "AgriAdvisor Telegram Bot", "status": "running"}


@bot.get("/health")
def health():
    return {
        "status":    "ok",
        "sessions":  session_manager.stats()["active_sessions"],
        "token_set": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
    }
