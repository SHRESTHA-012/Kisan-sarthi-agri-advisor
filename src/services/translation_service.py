from deep_translator import GoogleTranslator
from langdetect import detect
from src.utils.logger import get_logger

logger = get_logger(__name__)


def translate_to_english(text: str) -> str:
    """Translate Hindi (or auto-detected language) to English."""
    try:
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        logger.info(f"Translated to English: {translated}")
        return translated
    except Exception as e:
        logger.error(f"Translation to English failed: {e}")
        return text  # fallback to original


def translate_to_hindi(text: str) -> str:
    """Translate English response back to Hindi for the farmer."""
    try:
        translated = GoogleTranslator(source="en", target="hi").translate(text)
        logger.info(f"Translated to Hindi: {translated}")
        return translated
    except Exception as e:
        logger.error(f"Translation to Hindi failed: {e}")
        return text  # fallback to original


def detect_language(text: str) -> str:
    """Returns detected language code e.g. 'hi', 'en'."""
    try:
        lang = detect(text)
        return lang
    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        return "unknown"
