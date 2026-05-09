from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import os

DB_PATH = "faiss_index"

# ✅ Embeddings (stable + multilingual)
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

db = None

def get_db():
    global db

    if db is None:
        if not os.path.exists(DB_PATH):
            print("❌ FAISS index not found. Please rebuild it first.")
            return None

        embeddings = get_embeddings()

        try:
            db = FAISS.load_local(
                DB_PATH,
                embeddings,
                allow_dangerous_deserialization=True,
                index_name="index"
            )

            print("✅ FAISS DB loaded successfully")
            print("📦 Index size:", db.index.ntotal)
            print("🧠 Model:", embeddings.model_name)

        except Exception as e:
            print("❌ Error loading FAISS DB:", repr(e))
            db = None
            return None

    return db


def retrieve_context(query, k=3):
    try:
        database = get_db()

        if database is None:
            return "No FAISS database available."

        if not query or query.strip() == "":
            return "Empty query received."

        query = query.strip()
        print(f"\n🔍 Query: {query}")

        try:
            docs = database.similarity_search(query, k=k)
        except Exception as e:
            print("❌ FAISS search failed:", repr(e))
            return "Retrieval system error (check embedding/index mismatch)."

        if not docs:
            return "No relevant agricultural information found."

        print(f"📄 Retrieved {len(docs)} documents")

        context = "\n\n".join([doc.page_content for doc in docs])

        print("\n📚 Context Preview:")
        print(context[:300])

        return context

    except Exception as e:
        print("❌ Error in retrieval:", repr(e))
        return "Retrieval failed due to unexpected error."
