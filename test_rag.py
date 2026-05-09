from backend.retriever import retrieve_context

query = "धान की खेती कैसे करें"

context = retrieve_context(query)

print("\n🔍 QUERY:")
print(query)

print("\n📚 RETRIEVED CONTEXT:")
print(context)
