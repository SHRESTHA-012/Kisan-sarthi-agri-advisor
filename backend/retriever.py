import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

DB_PATH = "faiss_index"

#  Embeddings (stable + multilingual)
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
            print(" FAISS index not found. Please rebuild it first.")
            return None

        embeddings = get_embeddings()

        try:
            db = FAISS.load_local(
                DB_PATH,
                embeddings,
                allow_dangerous_deserialization=True,
                index_name="index"
            )

            print(" FAISS DB loaded successfully")
            print(" Index size:", db.index.ntotal)
            print(" Model:", embeddings.model_name)

        except Exception as e:
            print(" Error loading FAISS DB:", repr(e))
            db = None
            return None

    return db


#  NEW: Crop detection logic
def detect_crop(query):
    q = query.lower()

    if any(word in q for word in ["धान", "dhaan", "rice"]):
        return "rice"
    elif any(word in q for word in ["गेहूं", "gehu", "wheat"]):
        return "wheat"
    elif any(word in q for word in ["मक्का", "makka", "maize"]):
        return "maize"
    elif any(word in q for word in ["सब्ज", "vegetable", "sabzi"]):
        return "vegetables"
    
    return None


def retrieve_context(query, k=3):
    try:
        database = get_db()

        if database is None:
            return "No FAISS database available."

        if not query or query.strip() == "":
            return "Empty query received."

        query = query.strip()
        print(f"\n Query: {query}")

        # 🔍 Detect crop
        crop = detect_crop(query)
        print(" Detected crop:", crop)

        #  Step 1: Retrieve more docs
        try:
            docs = database.similarity_search(query, k=8)
        except Exception as e:
            print(" FAISS search failed:", repr(e))
            return "Retrieval system error."

        if not docs:
            return "No relevant agricultural information found."

        print(f" Retrieved {len(docs)} documents (before filtering)")

        #  Step 2: Filter based on crop
        if crop:
            filtered_docs = [
                doc for doc in docs
                if crop in doc.page_content.lower()
            ]

            # fallback if nothing matches
            if len(filtered_docs) == 0:
                print(" No crop-specific match, using original docs")
                filtered_docs = docs
        else:
            filtered_docs = docs

        #  Step 3: Take top-k after filtering
        final_docs = filtered_docs[:k]

        print(f" Final selected documents: {len(final_docs)}")

        context = "\n\n".join([doc.page_content for doc in final_docs])

        print("\n Context Preview:")
        print(context[:300])

        return context

    except Exception as e:
        print(" Error in retrieval:", repr(e))
        return "Retrieval failed due to unexpected error."
