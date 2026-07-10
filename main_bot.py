"""
Entry point for the Telegram bot.

Usage:
    python main_bot.py
"""
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

from src.bot.server import bot

if __name__ == "__main__":
    uvicorn.run(
        "src.bot.server:bot",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
    )
