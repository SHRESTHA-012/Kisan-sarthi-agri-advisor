from backend.retriever import retrieve_context

query = "धान में कीड़े लग गए हैं क्या करें?"

context = retrieve_context(query)

print("\n=== Retrieved Context ===\n")
print(context)
