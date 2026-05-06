from backend.chatbot import generate_response


query = "गेहूं में एफिड्स लग गए हैं क्या करें?"

response = generate_response(query)

print("\nAI Response:\n")
print(response)
