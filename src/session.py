"""
src/session.py
--------------
Thin coordinator for per-video RAG sessions.

Does NOT rewrite any RAG logic — it only wires existing src/ modules
together and manages per-video FAISS paths.

Integration points:
    ingestion.py  → get_transcript()
    splitter.py   → split_text()
    retriever.py  → get_retriever()
    rag.py        → get_rag_chain()
"""

import os
import logging
from pathlib import Path

from langchain_community.vectorstores import FAISS

from src.ingestion import get_transcript
from src.splitter import split_text
from src.retriever import get_retriever
from src.rag import get_rag_chain

logger = logging.getLogger(__name__)

VECTOR_DB_ROOT = "vector_db"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _faiss_path(video_id: str) -> str:
    """Return the filesystem path for a video's FAISS index directory."""
    return os.path.join(VECTOR_DB_ROOT, video_id)


def index_exists(video_id: str) -> bool:
    """Return True if a persisted FAISS index exists for this video_id."""
    path = _faiss_path(video_id)
    return os.path.exists(os.path.join(path, "index.faiss"))


# ---------------------------------------------------------------------------
# Session builders
# ---------------------------------------------------------------------------

def build_session(video_id: str, embedding_model, llm) -> dict:
    """
    Full ingestion pipeline for a new video_id:
      1. Fetch YouTube transcript  (ingestion.py)
      2. Chunk & extract timestamps (splitter.py)
      3. Embed & persist FAISS      (FAISS.from_documents)
      4. Build retriever            (retriever.py)
      5. Build LCEL rag chain       (rag.py)

    Returns a session dict with keys: retriever, chain, vectorstore, chunks.
    """
    logger.info("[%s] Building new session — ingesting transcript...", video_id)

    transcript = get_transcript(video_id)
    
    # Handle graceful failure from ingestion.py
    if isinstance(transcript, dict) and transcript.get("status") == "failed":
        return transcript
        
    chunks = split_text(transcript)

    faiss_path = _faiss_path(video_id)
    Path(faiss_path).mkdir(parents=True, exist_ok=True)

    # Embed and persist with the per-video path
    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embedding_model,
    )
    vector_store.save_local(faiss_path)

    logger.info(
        "[%s] FAISS index saved → %s  (%d chunks)",
        video_id, faiss_path, len(chunks),
    )

    retriever = get_retriever(vector_store, llm)
    chain = get_rag_chain(retriever)

    return {
        "retriever": retriever,
        "chain": chain,
        "vectorstore": vector_store,
        "chunks": len(chunks),
    }


def load_session(video_id: str, embedding_model, llm) -> dict:
    """
    Load an existing persisted FAISS index and rebuild the retriever + chain
    on top of it.  No re-ingestion needed.
    """
    faiss_path = _faiss_path(video_id)
    logger.info("[%s] Loading FAISS from disk → %s", video_id, faiss_path)

    vector_store = FAISS.load_local(
        faiss_path,
        embedding_model,
        allow_dangerous_deserialization=True,
    )

    retriever = get_retriever(vector_store, llm)
    chain = get_rag_chain(retriever)

    logger.info("[%s] Session loaded from disk.", video_id)

    return {
        "retriever": retriever,
        "chain": chain,
        "vectorstore": vector_store,
        "chunks": None,   # unknown for pre-built indexes
    }
