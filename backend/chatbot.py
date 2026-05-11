import ollama
from backend.retriever import retrieve_context
from backend.crop_engine import get_crops
from backend.weather_service import get_weather
import re
from datetime import datetime


def is_hindi(text):
    return bool(re.search(r'[\u0900-\u097F]', text))


def get_current_season() -> str:
    """Automatically detect Bihar farming season from current month."""
    month = datetime.now().month
    if month in [6, 7, 8, 9]:
        return "Kharif"      # Paddy, Maize, Soybean
    elif month in [10, 11, 12, 1, 2, 3]:
        return "Rabi"        # Wheat, Mustard, Potato
    else:
        return "Zaid"        # Vegetables, Watermelon


def build_chat_history(chat_history: list, use_hindi: bool) -> list:
    """Convert app.py session messages to ollama message format."""
    if not chat_history:
        return []

    messages = []
    # Only send last 4 exchanges (8 messages) to stay within context window
    recent = chat_history[-8:]
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    return messages


def generate_response(user_query: str, district: str = "Patna", chat_history: list = None, session: dict = None) -> str:
    """
    Generate a farming advisory response.

    Accepts both:
    - New style: generate_response(query, district="Patna", chat_history=[...])  ← from app.py
    - Old style: generate_response(query, session={"district": "Patna"})         ← legacy
    """

    # ── Resolve district ───────────────────────────────────────────────────────
    if session and "district" in session:
        district = session["district"]

    # ── Season (auto-detected) ─────────────────────────────────────────────────
    season = get_current_season()

    # ── Language detection ─────────────────────────────────────────────────────
    use_hindi = is_hindi(user_query)

    # ── Dynamic data ───────────────────────────────────────────────────────────
    crops   = get_crops(district, season)
    weather = get_weather(district)

    weather_str = (
        f"{weather['temp']}°C, नमी {weather['humidity']}%, {weather['description']}"
        if use_hindi else
        f"{weather['temp']}°C, nami {weather['humidity']}%, {weather['description']}"
    )

    # ── RAG context ────────────────────────────────────────────────────────────
    retrieved_context = retrieve_context(user_query)
    if not retrieved_context.strip():
        retrieved_context = (
            "कोई अतिरिक्त जानकारी उपलब्ध नहीं है।"
            if use_hindi else
            "Koi additional jaankari uplabdh nahi hai."
        )

    # ── Build context block ────────────────────────────────────────────────────
    if use_hindi:
        context = f"""जिला: {district} | मौसम: {season}
मौसम की स्थिति: {weather_str}
मौसम सलाह: {weather['advisory']}
उपलब्ध फसलें: {crops}

ज्ञान संदर्भ:
{retrieved_context}"""
    else:
        context = f"""Jila: {district} | Season: {season}
Mausam: {weather_str}
Mausam salah: {weather['advisory']}
Uplabdh faslen: {crops}

Jaankari:
{retrieved_context}"""

    # ── System prompt ──────────────────────────────────────────────────────────
    if use_hindi:
        system_prompt = """आप बिहार के किसानों के लिए एक अनुभवी कृषि सलाहकार हैं।

नियम:
- उत्तर शुद्ध और सरल हिंदी (देवनागरी) में दें
- किसान को "किसान भाई" कहकर संबोधित करें
- 3-4 छोटे वाक्यों में उत्तर दें
- व्यावहारिक सलाह दें (कब, कैसे, कितना)
- मौसम और जिले की जानकारी को उत्तर में शामिल करें
- पिछली बातचीत का संदर्भ याद रखें"""
    else:
        system_prompt = """Aap Bihar ke kisanon ke liye ek anubhavshali krishi salahakar hain.

Niyam:
- Hamesha Roman Hindi (English letters mein Hindi) use karein
- "Kisan bhai" se shuru karein
- 3-4 chhote vakya likhein
- Practical salah dein (kab, kaise, kitna)
- Mausam aur jile ki jaankari shamil karein
- Pichli baatcheet ka sandarbh yaad rakhein"""

    # ── User prompt ────────────────────────────────────────────────────────────
    if use_hindi:
        user_prompt = f"""संदर्भ:
{context}

किसान का प्रश्न: {user_query}

निर्देश: हिंदी में सरल और व्यावहारिक उत्तर दें।"""
    else:
        user_prompt = f"""Sandarbh:
{context}

Kisan ka prashn: {user_query}

Nirdesh: Roman Hindi me simple aur practical jawab dein."""

    # ── Build messages with history ────────────────────────────────────────────
    history_messages = build_chat_history(chat_history or [], use_hindi)

    messages = (
        [{"role": "system", "content": system_prompt}]
        + history_messages
        + [{"role": "user", "content": user_prompt}]
    )

    # ── LLM call ───────────────────────────────────────────────────────────────
    try:
        response = ollama.chat(
            model="mistral",
            options={
                "num_ctx": 2048,
                "temperature": 0.4,
                "top_p": 0.9
            },
            messages=messages
        )
        return response["message"]["content"]

    except Exception as e:
        print(f"LLM error: {e}")
        return (
            "सर्वर में समस्या है, कृपया बाद में प्रयास करें।"
            if use_hindi else
            "Server me problem hai, baad me try karein."
        )
