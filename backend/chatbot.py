import ollama
from backend.retriever import retrieve_context
from backend.crop_engine import get_crops
from backend.weather_service import get_weather


def generate_response(user_query):

    # Define context variables properly
    district = "Patna"
    season = "Kharif"

    # Get dynamic data
    crops = get_crops(district, season)
    weather = get_weather(district)

    # Retrieve knowledge
    retrieved_context = retrieve_context(user_query)

    # Combine everything
    context = f"""
कृषि जानकारी:
{retrieved_context}

उपलब्ध फसलें: {crops}
मौसम: {weather}
"""

    system_prompt = """
आप एक कृषि विशेषज्ञ हैं जो केवल बिहार के किसानों को सलाह देते हैं।

नियम:
- हमेशा केवल हिंदी (देवनागरी लिपि) में उत्तर दें
- कोई अंग्रेजी शब्द नहीं
- सरल और व्यावहारिक सलाह दें
- उत्तर छोटा और स्पष्ट हो
"""

    user_prompt = f"""
{context}

किसान का प्रश्न:
{user_query}
"""

    response = ollama.chat(
        model="llama3",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    return response["message"]["content"]
