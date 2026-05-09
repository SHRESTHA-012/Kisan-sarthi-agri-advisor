from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

import os

DATA_PATH = "data/knowledge"
DB_PATH = "faiss_index"


def create_vector_store():

    documents = []

    for file in os.listdir(DATA_PATH):

        if file.endswith(".txt"):

            loader = TextLoader(
                os.path.join(DATA_PATH, file),
                encoding="utf-8"
            )

            documents.extend(loader.load())

    splitter = CharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    docs = splitter.split_documents(documents)

    print(f"Loaded {len(docs)} chunks")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )

    db = FAISS.from_documents(docs, embeddings)

    db.save_local(DB_PATH)

    print("FAISS database created successfully")


if __name__ == "__main__":
    create_vector_store()
