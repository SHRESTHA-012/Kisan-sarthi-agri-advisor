import ollama
from backend.retriever import retrieve_context
from backend.crop_engine import get_crops
from backend.weather_service import get_weather


def generate_response(user_query, session=None):

    # ✅ Use session if available, else fallback
    district = session.get("district", "Patna") if session else "Patna"
    season = "Kharif"

    # Get dynamic data
    crops = get_crops(district, season)
    weather = get_weather(district)

    # Retrieve RAG context
    retrieved_context = retrieve_context(user_query)

    # ✅ Fallback if no context found
    if not retrieved_context.strip():
        retrieved_context = "कोई अतिरिक्त संदर्भ उपलब्ध नहीं है।"

    # Build context
    context = f"""
कृषि जानकारी:
{retrieved_context}

उपलब्ध फसलें: {crops}
मौसम: {weather}
"""

    # ✅ Improved system prompt (more controlled)
    system_prompt = """
आप बिहार के किसानों के लिए एक अनुभवी कृषि विशेषज्ञ हैं।

नियम:
- केवल शुद्ध हिंदी (देवनागरी लिपि) में उत्तर दें
- कोई अंग्रेजी या हिंग्लिश शब्द न लिखें
- उत्तर 3-4 छोटे वाक्यों में दें
- किसान को "किसान भाई" कहकर संबोधित करें
- सलाह व्यावहारिक और आसान हो
- अनावश्यक लंबा उत्तर न दें
- यदि जानकारी संदर्भ में उपलब्ध नहीं है, तो सामान्य कृषि ज्ञान से मदद करें
"""

    # ✅ Cleaner user prompt
    user_prompt = f"""
संदर्भ:
{context}

किसान का प्रश्न:
{user_query}

निर्देश:
- उत्तर केवल हिंदी में दें
- सरल और स्पष्ट भाषा का उपयोग करें
"""

    response = ollama.chat(
        model="mistral",
        options = {"num_ctx": 2048}
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    return response["message"]["content"]
