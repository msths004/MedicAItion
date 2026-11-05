import chromadb
import os
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.getenv("CHROMA_PATH", "data/chroma")

_client = None
_collections = {}


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_collection(name: str):
    global _collections
    if name not in _collections:
        client = get_client()
        _collections[name] = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
    return _collections[name]


def collection_exists_and_populated(name: str) -> bool:
    try:
        col = get_collection(name)
        return col.count() > 0
    except Exception:
        return False
