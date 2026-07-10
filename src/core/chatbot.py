import re
from datetime import datetime

from src.core.retriever import retrieve_context
from src.core.crop_engine import get_crops
from src.core.weather_service import get_weather
from src.core.pest_detection import analyze_pest
from src.services.llm_service import chat as llm_chat


def is_hindi(text: str) -> bool:
    return bool(re.search(r'[\u0900-\u097F]', text))


def get_current_season() -> str:
    month = datetime.now().month
    if month in [6, 7, 8, 9]:
        return "Kharif"
    elif month in [10, 11, 12, 1, 2, 3]:
        return "Rabi"
    return "Zaid"


def build_chat_history(chat_history: list, use_hindi: bool) -> list:
    if not chat_history:
        return []
    messages = []
    for msg in chat_history[-8:]:
        role    = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    return messages


_PEST_TRIGGER_KEYWORDS = [
    "कीट", "रोग", "बीमारी", "कीड़ा", "कीड़े", "माहू", "दीमक",
    "छेदक", "लपेटक", "आर्मीवर्म", "इल्ली", "सुंडी", "फंगस",
    "फफूंद", "पीला", "सूखना", "मुरझाना", "धब्बा", "छेद",
    "pest", "disease", "insect", "borer", "hopper", "aphid",
    "termite", "fungus", "yellowing", "wilting", "rot", "damage",
    "spray", "dawai", "dawa", "keeda", "rog", "bimari",
]


def _is_pest_query(query: str) -> bool:
    return any(kw in query.lower() for kw in _PEST_TRIGGER_KEYWORDS)


def generate_response(
    user_query: str,
    district: str = "Patna",
    chat_history: list = None,
    session: dict = None,
    image_path: str = None,
) -> str:

    if session and "district" in session:
        district = session["district"]

    season    = get_current_season()
    use_hindi = is_hindi(user_query)

    # ── Pest detection (fast path, before LLM) ────────────────────────────────
    if _is_pest_query(user_query) or image_path:
        pest_result = analyze_pest(query=user_query, image_path=image_path)
        if pest_result:
            weather = get_weather(district)
            if weather["humidity"] > 80:
                pest_result += (
                    f"\n\n🌦️ *मौसम सतर्कता:* आज नमी {weather['humidity']}% है — "
                    "कीट/रोग फैलने का खतरा अधिक है। तुरंत उपचार करें।"
                    if use_hindi else
                    f"\n\n🌦️ Aaj nami {weather['humidity']}% hai — "
                    "keeton ka khatra zyada hai. Turant upchar karein."
                )
            return pest_result

    # ── Dynamic context ───────────────────────────────────────────────────────
    crops   = get_crops(district, season)
    weather = get_weather(district)

    weather_str = (
        f"{weather['temp']}°C, नमी {weather['humidity']}%, {weather['description']}"
        if use_hindi else
        f"{weather['temp']}°C, nami {weather['humidity']}%, {weather['description']}"
    )

    retrieved_context = retrieve_context(user_query)
    if not retrieved_context.strip():
        retrieved_context = (
            "कोई अतिरिक्त जानकारी उपलब्ध नहीं है।"
            if use_hindi else
            "Koi additional jaankari uplabdh nahi hai."
        )

    # ── Prompt building ───────────────────────────────────────────────────────
    if use_hindi:
        context = (
            f"जिला: {district} | मौसम: {season}\n"
            f"मौसम की स्थिति: {weather_str}\n"
            f"मौसम सलाह: {weather['advisory']}\n"
            f"उपलब्ध फसलें: {crops}\n\n"
            f"ज्ञान संदर्भ:\n{retrieved_context}"
        )
        system_prompt = (
            "आप बिहार के किसानों के लिए एक अनुभवी कृषि सलाहकार हैं।\n\n"
            "नियम:\n"
            "- उत्तर शुद्ध और सरल हिंदी (देवनागरी) में दें\n"
            "- किसान को \"किसान भाई\" कहकर संबोधित करें\n"
            "- 3-4 छोटे वाक्यों में उत्तर दें\n"
            "- व्यावहारिक सलाह दें (कब, कैसे, कितना)\n"
            "- मौसम और जिले की जानकारी को उत्तर में शामिल करें\n"
            "- पिछली बातचीत का संदर्भ याद रखें"
        )
        user_prompt = f"संदर्भ:\n{context}\n\nकिसान का प्रश्न: {user_query}\n\nनिर्देश: हिंदी में सरल और व्यावहारिक उत्तर दें।"
    else:
        context = (
            f"Jila: {district} | Season: {season}\n"
            f"Mausam: {weather_str}\n"
            f"Mausam salah: {weather['advisory']}\n"
            f"Uplabdh faslen: {crops}\n\n"
            f"Jaankari:\n{retrieved_context}"
        )
        system_prompt = (
            "Aap Bihar ke kisanon ke liye ek anubhavshali krishi salahakar hain.\n\n"
            "Niyam:\n"
            "- Hamesha Roman Hindi use karein\n"
            "- \"Kisan bhai\" se shuru karein\n"
            "- 3-4 chhote vakya likhein\n"
            "- Practical salah dein (kab, kaise, kitna)\n"
            "- Mausam aur jile ki jaankari shamil karein\n"
            "- Pichli baatcheet ka sandarbh yaad rakhein"
        )
        user_prompt = f"Sandarbh:\n{context}\n\nKisan ka prashn: {user_query}\n\nNirdesh: Roman Hindi me simple aur practical jawab dein."

    history_messages = build_chat_history(chat_history or [], use_hindi)
    messages = (
        [{"role": "system", "content": system_prompt}]
        + history_messages
        + [{"role": "user", "content": user_prompt}]
    )

    # ── LLM call ──────────────────────────────────────────────────────────────
    try:
        return llm_chat(messages)
    except Exception as e:
        print(f"LLM error: {e}")
        return (
            "सर्वर में समस्या है, कृपया बाद में प्रयास करें।"
            if use_hindi else
            "Server me problem hai, baad me try karein."
        )
