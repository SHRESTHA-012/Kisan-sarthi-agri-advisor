from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import os

# ── Only these 2 paths changed from your original ─────────────────────────────
BASE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE, "knowledge_base", "raw_docs")   # ← was data/knowledge
DB_PATH   = os.path.join(BASE, "faiss_index")                  # ← stays at root


def create_vector_store():
    documents = []

    # Load all .txt files
    for file in os.listdir(DATA_PATH):
        if file.endswith(".txt"):
            filepath = os.path.join(DATA_PATH, file)
            try:
                loader = TextLoader(filepath, encoding="utf-8")
                docs   = loader.load()
                # Tag each doc with its source filename
                for doc in docs:
                    doc.metadata["source"] = file
                documents.extend(docs)
                print(f"  ✅ Loaded: {file}")
            except Exception as e:
                print(f"  ❌ Failed to load {file}: {e}")

    if not documents:
        print("❌ No documents found. Check DATA_PATH:", DATA_PATH)
        return

    # RecursiveCharacterTextSplitter respects --- separators in your txt files
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["---", "\n\n", "\n", " "]
    )

    docs = splitter.split_documents(documents)
    print(f"\n📦 Total chunks created: {len(docs)}")

    # Multilingual embeddings — same model as retriever.py
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    db = FAISS.from_documents(docs, embeddings)
    db.save_local(DB_PATH)

    print(f"✅ FAISS index saved at: {DB_PATH}")
    print(f"🔢 Total vectors: {db.index.ntotal}")


if __name__ == "__main__":
    create_vector_store()
