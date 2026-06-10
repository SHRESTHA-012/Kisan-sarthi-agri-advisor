
import logging
from typing import Optional

from .session_manager import session_manager, State

logger = logging.getLogger(__name__)


# ── Command map ────────────────────────────────────────────────────────────────

COMMANDS = {
    "/start":   "handle_start",
    "/help":    "handle_help",
    "/reset":   "handle_reset",
    "/crop":    "handle_crop_command",
    "/weather": "handle_weather_command",
    "/price":   "handle_price_command",
    "/scheme":  "handle_scheme_command",
    "/lang":    "handle_lang_command",
}

# ── Main router ────────────────────────────────────────────────────────────────

async def route_message(
    user_id: int,
    username: Optional[str],
    message_type: str,          # "text" | "voice" | "photo" | "document"
    content,                    # str for text, bytes for voice/photo
    caption: Optional[str] = None,
) -> str:
    """
    Central routing function.
    Returns the reply string to send back to the farmer.
    """

    session = session_manager.get(user_id)
    if username:
        session.username = username

    try:
        # ── 1. Photo / pest image ────────────────────────────────────────────
        if message_type == "photo":
            return await _handle_photo(session, content, caption)

        # ── 2. Voice message ─────────────────────────────────────────────────
        if message_type == "voice":
            return await _handle_voice(session, content)

        # ── 3. Text message ──────────────────────────────────────────────────
        if message_type == "text":
            text: str = content.strip()

            # Commands take priority
            command = text.split()[0].lower() if text.startswith("/") else None
            if command and command in COMMANDS:
                return await _dispatch_command(command, text, session)

            # State-based routing
            return await _handle_text_by_state(session, text)

    except Exception as exc:
        logger.exception("Error routing message from user %s: %s", user_id, exc)
        return _err_reply(session.language)

    finally:
        session_manager.update(session)

    return _err_reply(session.language)


# ── Command handlers ───────────────────────────────────────────────────────────

async def _dispatch_command(command: str, full_text: str, session) -> str:
    args = full_text.split()[1:]  # words after the command

    if command == "/start":
        session.reset()
        return _localize(session.language, {
            "hi": (
                "🌾 *नमस्ते! AgriAdvisor Bihar में आपका स्वागत है।*\n\n"
                "मैं आपकी खेती से जुड़ी हर समस्या में मदद करूँगा:\n"
                "• फसल सलाह\n• मौसम जानकारी\n• कीट पहचान (फोटो भेजें)\n"
                "• MSP मूल्य\n• सरकारी योजनाएँ\n\n"
                "बस मुझसे हिंदी में पूछें! 😊\n\n"
                "_/help टाइप करें पूरी सूची देखने के लिए।_"
            ),
            "en": (
                "🌾 *Welcome to AgriAdvisor Bihar!*\n\n"
                "I can help you with:\n"
                "• Crop advice  • Weather updates\n"
                "• Pest detection (send a photo)\n"
                "• MSP prices  • Govt schemes\n\n"
                "Just ask me anything! Type /help for all commands."
            ),
        })

    if command == "/help":
        return _localize(session.language, {
            "hi": (
                "📋 *उपलब्ध कमांड:*\n\n"
                "/crop — फसल सलाह लें\n"
                "/weather — आज का मौसम देखें\n"
                "/price — MSP मूल्य जानें\n"
                "/scheme — सरकारी योजनाएँ\n"
                "/lang — भाषा बदलें (hi/en)\n"
                "/reset — बातचीत दोबारा शुरू करें\n\n"
                "या सीधे फोटो भेजें कीट/रोग पहचान के लिए 📸"
            ),
            "en": (
                "📋 *Available Commands:*\n\n"
                "/crop — Crop advisory\n"
                "/weather — Today's weather\n"
                "/price — MSP prices\n"
                "/scheme — Govt schemes\n"
                "/lang — Change language (hi/en)\n"
                "/reset — Restart conversation\n\n"
                "Or just send a photo for pest/disease detection 📸"
            ),
        })

    if command == "/reset":
        session.reset()
        return _localize(session.language, {
            "hi": "✅ बातचीत रीसेट हो गई। क्या पूछना चाहते हैं?",
            "en": "✅ Conversation reset. What would you like to know?",
        })

    if command == "/lang":
        lang = args[0].lower() if args else ""
        if lang in ("hi", "en", "bho"):
            session.language = lang
            return f"✅ Language set to *{lang}*."
        return "Usage: /lang hi  or  /lang en"

    if command == "/weather":
        district = args[0] if args else session.district or "patna"
        return await _fetch_weather(district, session)

    if command == "/price":
        crop = " ".join(args) if args else session.current_crop
        if not crop:
            session.state = State.AWAITING_CROP
            session.context["next_action"] = "price"
            return _localize(session.language, {
                "hi": "कौन सी फसल का MSP जानना है?",
                "en": "Which crop's MSP price do you want?",
            })
        return await _fetch_price(crop, session)

    if command == "/scheme":
        return await _fetch_schemes(session)

    if command == "/crop":
        session.state = State.AWAITING_CROP
        session.context["next_action"] = "advisory"
        return _localize(session.language, {
            "hi": "आप किस फसल के बारे में सलाह चाहते हैं?",
            "en": "Which crop would you like advice on?",
        })

    return _err_reply(session.language)


# ── State-based text routing ───────────────────────────────────────────────────

async def _handle_text_by_state(session, text: str) -> str:
    state = session.state

    if state == State.AWAITING_CROP:
        session.current_crop = text
        next_action = session.context.get("next_action", "advisory")
        session.reset()
        session.current_crop = text  # keep crop after reset

        if next_action == "price":
            return await _fetch_price(text, session)
        return await _fetch_advisory(text, session)

    # Default: free-form RAG chatbot
    return await _rag_chat(text, session)


# ── Media handlers ─────────────────────────────────────────────────────────────

async def _handle_photo(session, photo_bytes: bytes, caption: Optional[str]) -> str:
    try:
        from backend.pest_detection import detect_pest
        result = await detect_pest(photo_bytes)
        name     = result.get("pest_name", "अज्ञात")
        severity = result.get("severity", "-")
        remedy   = result.get("remedy", "")
        return (
            f"🔍 *पहचाना गया:* {name}\n"
            f"⚠️ *गंभीरता:* {severity}\n\n"
            f"💊 *उपाय:*\n{remedy}"
        )
    except ImportError:
        logger.warning("pest_detection backend not available")
        return "📸 फोटो मिली। कीट पहचान सेवा जल्द उपलब्ध होगी।"
    except Exception as exc:
        logger.error("Pest detection error: %s", exc)
        return _err_reply(session.language)


async def _handle_voice(session, audio_bytes: bytes) -> str:
    try:
        from backend.voice_service import transcribe
        text = await transcribe(audio_bytes, lang=session.language)
        logger.info("Voice transcribed: %s", text)
        # Route the transcribed text normally
        return await _handle_text_by_state(session, text)
    except ImportError:
        logger.warning("voice_service backend not available")
        return "🎤 आवाज़ संदेश मिला। कृपया टेक्स्ट में भी लिखें।"
    except Exception as exc:
        logger.error("Voice error: %s", exc)
        return _err_reply(session.language)


# ── Backend calls ──────────────────────────────────────────────────────────────

async def _rag_chat(text: str, session) -> str:
    try:
        from backend.chatbot import generate_response
        # Matches your existing generate_response(query, district, chat_history) signature
        return generate_response(
            text,
            district=session.district,
            chat_history=session.context.get("chat_history", []),
        )
    except ImportError:
        return "🤖 " + text  # Echo fallback during development


async def _fetch_advisory(crop: str, session) -> str:
    try:
        from backend.advisory_engine import get_crop_advisory
        return get_crop_advisory(crop=crop, district=session.district)
    except ImportError:
        return f"🌱 *{crop}* की सलाह जल्द उपलब्ध होगी।"


async def _fetch_weather(district: str, session) -> str:
    try:
        from backend.weather_service import get_weather
        # Matches your existing get_weather(district) → dict signature
        w = get_weather(district)
        return (
            f"🌤️ *{district} मौसम*\n"
            f"🌡️ तापमान: {w['temp']}°C\n"
            f"💧 नमी: {w['humidity']}%\n"
            f"☁️ {w['description']}\n\n"
            f"📢 {w['advisory']}"
        )
    except ImportError:
        return f"🌤️ {district} का मौसम डेटा जल्द उपलब्ध होगा।"


async def _fetch_price(crop: str, session) -> str:
    try:
        import json, os
        path = os.path.join("data", "msp_prices.json")
        with open(path) as f:
            prices = json.load(f)
        entry = prices.get(crop.lower())
        if entry:
            return f"💰 *{crop} MSP:* ₹{entry['msp']}/क्विंटल ({entry['year']})"
        return f"'{crop}' का MSP डेटा नहीं मिला।"
    except Exception:
        return f"💰 {crop} का MSP डेटा अभी उपलब्ध नहीं।"


async def _fetch_schemes(session) -> str:
    try:
        import json, os
        path = os.path.join("data", "govt_schemes.json")
        with open(path) as f:
            schemes = json.load(f)
        lines = ["📋 *बिहार किसान योजनाएँ:*\n"]
        for s in schemes[:5]:
            lines.append(f"• *{s['name']}*: {s['benefit']}")
        return "\n".join(lines)
    except Exception:
        return "📋 योजना जानकारी जल्द उपलब्ध होगी।"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _localize(lang: str, strings: dict) -> str:
    return strings.get(lang, strings.get("hi", list(strings.values())[0]))


def _err_reply(lang: str) -> str:
    return _localize(lang, {
        "hi": "⚠️ कुछ गड़बड़ हो गई। कृपया दोबारा कोशिश करें।",
        "en": "⚠️ Something went wrong. Please try again.",
    })
