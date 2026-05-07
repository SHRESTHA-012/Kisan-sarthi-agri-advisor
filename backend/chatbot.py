import ollama
from backend.retriever import retrieve_context


def generate_response(user_query):

    context = retrieve_context(user_query)

    system_prompt = """
आप एक कृषि विशेषज्ञ हैं जो केवल बिहार के किसानों को सलाह देते हैं।

नियम:
- हमेशा केवल हिंदी (देवनागरी लिपि) में उत्तर दें
- कोई अंग्रेजी शब्द नहीं
- सरल और व्यावहारिक सलाह दें
- उत्तर छोटा और स्पष्ट हो
"""

    user_prompt = f"""
कृषि जानकारी:
{context}

किसान का प्रश्न:
{user_query}
"""

    response = ollama.chat(
        model="llama3",   # better than mistral for instruction following
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    return response["message"]["content"]
