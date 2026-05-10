from backend.retriever import retrieve_context

queries = [
    "धान में कीड़े लग गए हैं क्या करें?",
    "dhaan me keede lag gaye kya kare",
    "rice pest problem",
    "धान में रोग"
]

for query in queries:
    print("\n" + "="*50)
    print("🔍 Query:", query)

    context = retrieve_context(query)

    print("\n📄 Retrieved Context:\n")
    print(context)
