import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

BASE     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE, "faiss_index")


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


db = None


def get_db():
    global db
    if db is None:
        if not os.path.exists(DB_PATH):
            print("FAISS index not found. Please rebuild it first.")
            return None
        embeddings = get_embeddings()
        try:
            db = FAISS.load_local(
                DB_PATH,
                embeddings,
                allow_dangerous_deserialization=True,
                index_name="index",
            )
            print("FAISS DB loaded successfully")
            print("Index size:", db.index.ntotal)
        except Exception as e:
            print("Error loading FAISS DB:", repr(e))
            db = None
    return db


def detect_crop(query: str) -> str | None:
    q = query.lower()
    if any(w in q for w in ["धान", "dhaan", "rice"]):
        return "rice"
    elif any(w in q for w in ["गेहूं", "gehu", "wheat"]):
        return "wheat"
    elif any(w in q for w in ["मक्का", "makka", "maize"]):
        return "maize"
    elif any(w in q for w in ["सब्ज", "vegetable", "sabzi"]):
        return "vegetables"
    return None


def retrieve_context(query: str, k: int = 3) -> str:
    try:
        database = get_db()
        if database is None:
            return "No FAISS database available."
        if not query or not query.strip():
            return "Empty query received."

        query = query.strip()
        crop  = detect_crop(query)

        docs = database.similarity_search(query, k=8)
        if not docs:
            return "No relevant agricultural information found."

        if crop:
            filtered = [d for d in docs if crop in d.page_content.lower()]
            docs = filtered if filtered else docs

        context = "\n\n".join([d.page_content for d in docs[:k]])
        return context

    except Exception as e:
        print("Error in retrieval:", repr(e))
        return "Retrieval failed due to unexpected error."
