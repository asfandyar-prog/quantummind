# ── app/core/vectorstore.py ──────────────────────────────────
# The one place that opens the course-material vector store (ChromaDB) and the
# embedding model behind it. /upload writes through it; the RAG workflow reads
# through it.
#
# The embedding model (all-MiniLM-L6-v2 on CPU, ~80 MB plus torch) is loaded once
# per process and reused. Before, every call built a new HuggingFaceEmbeddings,
# which reloads the model each time. All of this is blocking: call it from a
# worker thread (asyncio.to_thread), never directly on the event loop.

import os
from functools import lru_cache

from app.core.config import settings

COLLECTION = "quantummind_course"
CHROMA_DIR = settings.chroma_dir


def _client_settings():
    # Chroma sends anonymous usage telemetry (PostHog) unless told not to.
    from chromadb.config import Settings
    return Settings(anonymized_telemetry=False, is_persistent=True, persist_directory=CHROMA_DIR)


@lru_cache(maxsize=1)
def get_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_vectorstore():
    """The course collection, with the shared embedding model."""
    from langchain_community.vectorstores import Chroma
    os.makedirs(CHROMA_DIR, exist_ok=True)
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=get_embeddings(),
        collection_name=COLLECTION,
        client_settings=_client_settings(),
    )


def collection_count() -> int:
    """How many chunks are stored, without loading the embedding model.

    Lets the RAG workflow skip retrieval entirely while nothing has been uploaded
    (always the case on a fresh Railway container, whose disk is wiped on deploy).
    """
    if not os.path.isdir(CHROMA_DIR):
        return 0
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_DIR, settings=_client_settings())
    try:
        return client.get_collection(COLLECTION).count()
    except Exception:   # the collection doesn't exist yet
        return 0
