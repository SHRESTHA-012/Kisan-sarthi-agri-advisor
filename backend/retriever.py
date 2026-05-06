from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


DB_PATH = "faiss_index"


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

db = FAISS.load_local(
    DB_PATH,
    embeddings,
    allow_dangerous_deserialization=True
)


def retrieve_context(query, k=3):

    docs = db.similarity_search(query, k=k)

    context = "\n\n".join([doc.page_content for doc in docs])

    return context
