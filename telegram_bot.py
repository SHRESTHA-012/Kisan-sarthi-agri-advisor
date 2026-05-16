
import logging
import asyncio
import os
from contextlib import asynccontextmanager

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


# ── Lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌾 AgrAdvisor Telegram Bot starting…")


    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        logger.warning("⚠️  TELEGRAM_BOT_TOKEN is not set in .env!")


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
