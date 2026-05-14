import os
import requests
from utils.config import TELEGRAM_BOT_TOKEN
from utils.logger import get_logger

logger = get_logger(__name__)

TEMP_DIR = "temp_media"
os.makedirs(TEMP_DIR, exist_ok=True)

TELEGRAM_FILE_URL = "https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
TELEGRAM_DOWNLOAD_URL = "https://api.telegram.org/file/bot{token}/{file_path}"


def _get_file_path(file_id: str) -> str | None:
    """Get Telegram file path from file_id."""
    url = TELEGRAM_FILE_URL.format(token=TELEGRAM_BOT_TOKEN, file_id=file_id)
    response = requests.get(url)
    data = response.json()
    if data.get("ok"):
        return data["result"]["file_path"]
    logger.error(f"Failed to get file path for file_id {file_id}: {data}")
    return None


def download_image(file_id: str) -> str | None:
    """Download an image from Telegram and return local file path."""
    try:
        file_path = _get_file_path(file_id)
        if not file_path:
            return None

        url = TELEGRAM_DOWNLOAD_URL.format(token=TELEGRAM_BOT_TOKEN, file_path=file_path)
        response = requests.get(url)

        local_path = os.path.join(TEMP_DIR, file_path.split("/")[-1])
        with open(local_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Image downloaded to {local_path}")
        return local_path

    except Exception as e:
        logger.error(f"Image download failed: {e}")
        return None


def download_voice(file_id: str) -> str | None:
    """Download a voice message (OGG) from Telegram and return local file path."""
    try:
        file_path = _get_file_path(file_id)
        if not file_path:
            return None

        url = TELEGRAM_DOWNLOAD_URL.format(token=TELEGRAM_BOT_TOKEN, file_path=file_path)
        response = requests.get(url)

        local_path = os.path.join(TEMP_DIR, file_path.split("/")[-1])
        with open(local_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Voice message downloaded to {local_path}")
        return local_path

    except Exception as e:
        logger.error(f"Voice download failed: {e}")
        return None


def cleanup_file(file_path: str):
    """Delete temp file after processing."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.error(f"Cleanup failed for {file_path}: {e}")
