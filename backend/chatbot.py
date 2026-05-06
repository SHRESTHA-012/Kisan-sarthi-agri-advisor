import ollama

from backend.retriever import retrieve_context


def generate_response(user_query):

    # Retrieve relevant farming context
    context = retrieve_context(user_query)

    # Strong Hindi-focused prompt
    prompt = f"""
आप बिहार के किसानों के लिए कृषि विशेषज्ञ हैं।

आपको हमेशा केवल हिंदी में उत्तर देना है।

नियम:
1. उत्तर केवल हिंदी में दें
2. आसान भाषा का प्रयोग करें
3. छोटे और स्पष्ट उत्तर दें
4. कृषि सलाह व्यावहारिक होनी चाहिए
5. अंग्रेजी का प्रयोग न करें
6. यदि जानकारी उपलब्ध न हो तो साफ बताएं

कृषि जानकारी:
{context}

किसान का प्रश्न:
{user_query}

हिंदी में उत्तर:
"""

    response = ollama.chat(
        model="mistral",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]
