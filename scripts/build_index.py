"""
Rebuild the FAISS vector index from knowledge_base/raw_docs/.

Usage:
    python scripts/build_index.py
"""
from src.core.vector_store import create_vector_store

if __name__ == "__main__":
    create_vector_store()
