import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 📁 Paths
DATA_PATH = "knowledge_base/raw_docs"
DB_PATH = "faiss_index"

# 🧠 Embedding model (multilingual → supports Hindi + Hinglish)
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)

def load_documents():
    documents = []

    for file in os.listdir(DATA_PATH):
        if file.endswith(".txt"):
            file_path = os.path.join(DATA_PATH, file)

            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()

                documents.append({
                    "text": text,
                    "source": file
                })

    print(f"📄 Loaded {len(documents)} documents")
    return documents


def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,      # 🔥 IMPORTANT (better retrieval)
        chunk_overlap=50
    )

    chunks = []

    for doc in documents:
        split_texts = splitter.split_text(doc["text"])

        for chunk in split_texts:
            chunks.append({
                "text": chunk,
                "source": doc["source"]
            })

    print(f"✂️ Created {len(chunks)} chunks")
    return chunks


def create_faiss_index(chunks):
    texts = [chunk["text"] for chunk in chunks]

    print("🧠 Generating embeddings...")

    db = FAISS.from_texts(texts, embedding_model)

    print("💾 Saving FAISS index...")
    db.save_local(DB_PATH)

    print("✅ FAISS index created successfully!")


if __name__ == "__main__":
    docs = load_documents()
    chunks = split_documents(docs)
    create_faiss_index(chunks)
