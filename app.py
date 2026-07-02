"""
app.py — FastAPI Production Server for YouTube RAG
----------------------------------------------------

Endpoints:
  POST /load-video   — ingest or load a video's FAISS index
  POST /ask          — streaming SSE answer with source citations
  GET  /health       — server liveness + active session list

All RAG logic lives in src/ (unchanged).
This file adds HTTP transport + session management only.

Run:
    uvicorn app:app --reload --port 8000
"""

import json
import logging
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.embeddings import get_embedding_model
from src.llm import get_llm
from src.session import build_session, index_exists, load_session

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan — load heavy models ONCE at startup
# ---------------------------------------------------------------------------
embedding_model = None
llm = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global embedding_model, llm
    logger.info("Loading embedding model (MiniLM)...")
    embedding_model = get_embedding_model()
    logger.info("Loading LLM (Groq Llama 3.3-70B)...")
    llm = get_llm()
    logger.info("All models ready. Server is live.")
    yield
    logger.info("Shutting down...")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="YouTube RAG API",
    description="Ask questions about any YouTube video, powered by LangChain + Groq.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — open to chrome-extension:// origins (and localhost for testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# In-memory session store
#   video_sessions[video_id] = {
#       "retriever": <MultiQueryRetriever>,
#       "chain":     <LCEL chain>,
#       "vectorstore": <FAISS>,
#       "chunks":    <int | None>,
#   }
# ---------------------------------------------------------------------------
video_sessions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_video_id(url: str) -> str | None:
    """Extract 11-char YouTube video ID from any recognisable URL format."""
    patterns = [
        r"[?&]v=([A-Za-z0-9_-]{11})",          # youtube.com/watch?v=
        r"youtu\.be/([A-Za-z0-9_-]{11})",       # youtu.be/
        r"/embed/([A-Za-z0-9_-]{11})",           # youtube.com/embed/
        r"/shorts/([A-Za-z0-9_-]{11})",          # youtube.com/shorts/
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    # Last resort: maybe the caller passed the raw ID directly
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()
    return None


def format_timestamp(seconds: float) -> str:
    """Convert float seconds → HH:MM:SS string."""
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


def sse(payload: dict) -> str:
    """Wrap a dict as a Server-Sent Event line."""
    return f"data: {json.dumps(payload)}\n\n"


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class LoadVideoRequest(BaseModel):
    url: str


class AskRequest(BaseModel):
    question: str
    video_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/load-video")
async def load_video(req: LoadVideoRequest):
    """
    Accepts a YouTube URL, extracts the video_id, and either:
      - Returns the in-memory session (fastest)
      - Loads the persisted FAISS index from disk
      - Ingests the transcript from scratch (slowest)
    """
    video_id = extract_video_id(req.url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail=f"Could not extract a video_id from: '{req.url}'. "
                   "Please provide a valid YouTube URL.",
        )

    logger.info("[%s] /load-video called.", video_id)

    # ① Already in memory — fastest path
    if video_id in video_sessions:
        logger.info("[%s] Session already in memory — skipping rebuild.", video_id)
        session = video_sessions[video_id]
        return {
            "status": "success",
            "video_id": video_id,
            "chunks": session.get("chunks"),
            "source": "memory",
        }

    try:
        # ② FAISS exists on disk — load it
        if index_exists(video_id):
            logger.info("[%s] Loading existing FAISS index from disk.", video_id)
            session = load_session(video_id, embedding_model, llm)
            source = "disk"
        # ③ Fresh ingestion
        else:
            logger.info("[%s] No index found — running full ingestion pipeline.", video_id)
            session = build_session(video_id, embedding_model, llm)
            
            # Handle graceful failure gracefully!
            if session.get("status") == "failed":
                logger.warning("[%s] Ingestion failed gracefully: %s", video_id, session.get("reason"))
                return session
                
            source = "ingested"

        video_sessions[video_id] = session
        logger.info("[%s] Session ready (source=%s).", video_id, source)

        return {
            "status": "success",
            "video_id": video_id,
            "chunks": session.get("chunks"),
            "source": source,
        }

    except Exception as exc:
        logger.exception("[%s] Failed to load video: %s", video_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ask")
async def ask(req: AskRequest):
    """
    Streams the LLM answer token-by-token via Server-Sent Events.

    SSE event types emitted:
      {"type":"token",   "content":"..."}   — each streamed token
      {"type":"sources", "sources":[...]}   — after full answer
      {"type":"done"}                       — stream end sentinel
      {"type":"error",   "message":"..."}   — on any exception
    """
    video_id = req.video_id
    question = req.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    if video_id not in video_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' is not loaded. Call POST /load-video first.",
        )

    chain = video_sessions[video_id]["chain"]
    logger.info("[%s] /ask — question: %s", video_id, question[:80])

    async def event_stream() -> AsyncGenerator[str, None]:
        sources = []
        try:
            # rag_chain.stream() yields dicts: {question}, {source_documents}, {answer}
            for chunk in chain.stream(question):
                # Capture source documents (emitted once by the parallel chain)
                if "source_documents" in chunk:
                    sources = chunk["source_documents"]

                # Stream answer tokens as they arrive from Groq
                if "answer" in chunk and chunk["answer"]:
                    yield sse({"type": "token", "content": chunk["answer"]})

            # After answer is complete, emit formatted source citations
            formatted_sources = []
            for doc in sources:
                start = doc.metadata.get("start")
                end = doc.metadata.get("end")
                if start is not None:
                    formatted_sources.append({
                        "start": start,
                        "end": end,
                        "formatted": format_timestamp(start),
                        "url": f"https://youtu.be/{video_id}?t={int(start)}s",
                        "snippet": doc.page_content[:200].strip(),
                    })

            yield sse({"type": "sources", "sources": formatted_sources})
            yield sse({"type": "done"})
            logger.info("[%s] Stream complete. %d sources.", video_id, len(formatted_sources))

        except Exception as exc:
            logger.exception("[%s] Streaming error: %s", video_id, exc)
            yield sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/health")
async def health():
    """Liveness check + active session list."""
    return {
        "status": "ok",
        "active_sessions": list(video_sessions.keys()),
        "session_count": len(video_sessions),
    }
