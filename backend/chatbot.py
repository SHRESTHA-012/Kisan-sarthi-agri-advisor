import ollama
from backend.retriever import retrieve_context
from backend.crop_engine import get_crops
from backend.weather_service import get_weather
import re


def is_hindi(text):
    # Check if Devanagari characters exist
    return bool(re.search(r'[\u0900-\u097F]', text))


def generate_response(user_query, session=None):

    # Use session if available, else fallback
    district = session.get("district", "Patna") if session else "Patna"
    season = "Kharif"

    # Detect language
    use_hindi = is_hindi(user_query)

    # Get dynamic data
    crops = get_crops(district, season)
    weather = get_weather(district)

    # Retrieve RAG context
    retrieved_context = retrieve_context(user_query)

    if not retrieved_context.strip():
        retrieved_context = "कोई अतिरिक्त जानकारी उपलब्ध नहीं है।" if use_hindi else "Koi additional jaankari uplabdh nahi hai."

    # Build context
    context = f"""
Krishi jaankari:
{retrieved_context}

Upalabdh faslen: {crops}
Mausam: {weather}
"""

    # 🔥 Dynamic system prompt
    if use_hindi:
        system_prompt = """
आप बिहार के किसानों के लिए एक अनुभवी कृषि सलाहकार हैं।

नियम:
- उत्तर शुद्ध और सरल हिंदी (देवनागरी) में दें
- किसान को "किसान भाई" कहकर संबोधित करें
- 3-4 छोटे वाक्यों में उत्तर दें
- व्यावहारिक सलाह दें (कब, कैसे, कितना)

उदाहरण:
प्रश्न: गेहूं की खेती कब करें?
उत्तर: किसान भाई, गेहूं की बुवाई अक्टूबर के अंत से नवंबर तक करें।
खेत को पहले अच्छी तरह तैयार करें।
पहली सिंचाई के समय यूरिया डालें।
इससे पैदावार अच्छी होगी।
"""
    else:
        system_prompt = """
Aap Bihar ke kisanon ke liye ek anubhavshali krishi salahakar hain.

Bhasha:
- Hamesha Roman Hindi (English letters mein Hindi) use karein

Niyam:
- "Kisan bhai" se shuru karein
- 3-4 chhote vakya likhein
- Practical salah dein (kab, kaise, kitna)

Udaharan:
Prashn: Gehu ki kheti kab karein?
Uttar: Kisan bhai, gehu ki bowaai October ke end se November tak karein.
Beej bone se pehle khet ko taiyar karein.
Pehli irrigation ke samay urea daalein.
Isse paidavaar achhi hogi.
"""

    # User prompt
    if use_hindi:
        user_prompt = f"""
संदर्भ:
{context}

किसान का प्रश्न:
{user_query}

निर्देश:
- उत्तर हिंदी में दें
- सरल और स्पष्ट भाषा का उपयोग करें
"""
    else:
        user_prompt = f"""
Sandarbh:
{context}

Kisan ka prashn:
{user_query}

Nirdesh:
- Roman Hindi me jawab dein
- Simple aur practical rakhein
"""

    try:
        response = ollama.chat(
            model="mistral",
            options={
                "num_ctx": 2048,
                "temperature": 0.4,
                "top_p": 0.9
            },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response["message"]["content"]

    except Exception:
        return "सर्वर में समस्या है, कृपया बाद में प्रयास करें।" if use_hindi else "Server me problem hai, baad me try karein."
