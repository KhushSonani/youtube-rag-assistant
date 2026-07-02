# 🎥 YouTube RAG Assistant

**A production-ready Retrieval-Augmented Generation (RAG) pipeline that turns any YouTube video into an interactive, searchable knowledge base.**

Ask questions about a video and get answers grounded strictly in its transcript — complete with clickable, timestamped citations that jump you straight to the moment the answer came from.

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-blue">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-async-009688">
  <img alt="LangChain" src="https://img.shields.io/badge/LangChain-RAG-1c3c3c">
  <img alt="FAISS" src="https://img.shields.io/badge/VectorDB-FAISS-orange">
</p>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Core RAG Workflow](#core-rag-workflow)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Installation & Usage](#installation--usage)
- [Advanced Implementation Details](#advanced-implementation-details)
- [Future Improvements](#future-improvements)
- [Resume Highlights](#resume-highlights)

---

## Overview

**The Problem:** Finding a specific moment in a long YouTube video — a lecture, podcast, or tutorial — means tedious scrubbing and skimming.

**The Solution:** This project uses **Retrieval-Augmented Generation (RAG)** to extract a video's transcript, convert it into vector embeddings, and ground an LLM so it can only answer using the video's actual content — never general knowledge. Every answer comes with clickable timestamp citations pointing to the exact second in the video.

**How it's different from a normal chatbot:** A standard chatbot has no knowledge of the specific video you're watching. This system is strictly grounded to that video's transcript, and it preserves timestamps so it can cite its sources precisely.

---

## Features

| Feature | Description |
|---|---|
| 🔗 **Automated Ingestion** | Fetches closed captions via the YouTube Transcript API, with automatic language-translation fallback |
| 🗂️ **Local FAISS Vector DB** | Stores and groups embedded transcript chunks persistently, per video ID |
| 🎯 **MMR-Based Semantic Search** | Uses Maximal Marginal Relevance to balance relevance and diversity, avoiding redundant retrieved context |
| ⏱️ **Timestamped Citations** | Appends clickable `youtu.be/id?t=X` links to every answer for instant source verification |
| ⚡ **Real-Time Streaming** | Streams LLM responses token-by-token via Server-Sent Events (SSE) through FastAPI |
| 🧩 **Chrome Extension UI** | Query any YouTube video directly from the page you're watching |
| 🛡️ **Two-Tier Caching + Backoff** | Caches transcripts and vector indexes separately, with exponential backoff to prevent IP bans and API failures |

---

## Tech Stack

| Technology | Purpose | Used In |
|------------|----------|---------|
| **Python / FastAPI** | High-performance async web framework | `app.py` |
| **LangChain** | Orchestrates the end-to-end RAG pipeline (LCEL) | `src/rag.py`, `src/session.py` |
| **FAISS** | Local vector database for similarity search | `src/vectorstore.py` |
| **HuggingFace (`all-MiniLM-L6-v2`)** | Embedding model | `src/embeddings.py` |
| **Groq (Llama-3.3-70B)** | Low-latency LLM inference | `src/llm.py` |
| **youtube-transcript-api** | Fetches native closed captions | `src/ingestion.py` |
| **HTML / CSS / JS** | Chrome Extension UI | `extension/` |

---

## System Architecture

```text
[ Chrome Extension ] --> (POST /load-video) --> [ FastAPI ]
                                                     |
  [ Timestamp Citations ]                         [ Ingestion & Caching ]
            ^                                        |
  [ Streamed LLM Answer ]                         [ Chunking & Metadata ]
            ^                                        |
  [ Prompt Construction ] <--- (POST /ask) --->   [ FAISS Vector DB ]
            ^                                        |
            +------------- [ MMR Retriever ] <-------+
```

---

## Core RAG Workflow

1. **Ingestion & Processing** — The transcript is fetched, timestamp markers (`[[14.5]]`) are injected inline, and the text is split into overlapping 500-character chunks. Timestamps are extracted and saved to chunk metadata.
2. **Embedding** — Each chunk is embedded via the HuggingFace MiniLM model and persisted locally in a FAISS index.
3. **Retrieval** — The user's query is embedded, and a `MultiQueryRetriever` fetches the most relevant chunks using **Maximal Marginal Relevance (MMR)** to reduce redundancy.
4. **Generation** — LangChain assembles the retrieved chunks into a prompt; Groq streams the generated answer back alongside exact timestamp links.

---

## Project Structure

```text
youtube-rag-assistant/
├── .env                     # Secret keys (GROQ_API_KEY, etc.)
├── requirements.txt         # Python dependencies
├── app.py                   # FastAPI app: routing, lifespan, SSE streaming
│
├── cache/                   # Auto-generated cache
│   └── transcripts/         # Raw transcripts, cached to avoid re-fetching & rate limits
│
├── vector_db/                # Auto-generated FAISS indexes
│   └── <video_id>/          # Per-video persisted vector index
│
├── extension/                # Chrome Extension (frontend)
│   ├── manifest.json         # Extension configuration
│   ├── popup.html            # UI layout
│   └── popup.js               # Frontend logic & API calls
│
└── src/                      # Core RAG business logic
    ├── ingestion.py           # Transcript fetching, caching, translation fallback
    ├── splitter.py            # Chunking + timestamp metadata extraction
    ├── embeddings.py           # HuggingFace embedding model config
    ├── vectorstore.py          # FAISS save/load operations
    ├── retriever.py             # MMR-based MultiQueryRetriever config
    ├── llm.py                   # Groq (Llama-3.3-70B) LLM connection
    ├── prompt.py                 # System prompt template
    ├── rag.py                    # LangChain LCEL answer-generation chain
    └── session.py                 # Orchestrates ingestion → retrieval → generation per video
```

---

## API Endpoints

### `POST /load-video`
Initializes a RAG session for a given video. Checks the local FAISS index first; if missing, runs full ingestion.

**Request:**
```json
{ "url": "https://www.youtube.com/watch?v=..." }
```

**Response:**
```json
{
  "status": "success",
  "video_id": "dQw4w9WgXcQ",
  "chunks": 45,
  "source": "ingested"   // or "disk" / "memory"
}
```

### `POST /ask`
Queries the loaded video via **Server-Sent Events**.

**Request:**
```json
{ "video_id": "dQw4w9WgXcQ", "question": "What is this video about?" }
```

**Response:** `text/event-stream` — streamed tokens, followed by a final JSON array of timestamp source citations.

### `GET /health`
Health check; lists currently active in-memory sessions.

---

## Installation & Usage

**1. Clone & set up the environment**
```bash
git clone https://github.com/KhushSonani/youtube-rag-assistant.git
cd youtube-rag-assistant
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure environment variables**

Create a `.env` file in the root directory:
```env
GROQ_API_KEY=gsk_your_api_key_here
```
> Get a free key at [console.groq.com](https://console.groq.com).

**3. Run the FastAPI server**
```bash
uvicorn app:app --reload --port 8000
```

**4. Load the Chrome Extension**
- Go to `chrome://extensions/`
- Enable **Developer mode**
- Click **Load unpacked** → select the `extension/` folder

**5. Use it**
Open any YouTube video → click the extension icon → **Load Video** → ask a question → click the timestamped citation to jump straight to that moment.

---

## Advanced Implementation Details

- **MMR Retrieval Strategy** — Standard similarity search on long videos often returns near-duplicate chunks. MMR balances relevance and diversity, giving the LLM broader, less redundant context.
- **Timestamp Citation System** — Timestamps are extracted via regex during ingestion and stored as native LangChain `Document` metadata. After the LLM finishes streaming, this metadata is used to generate exact deep links (`youtu.be/id?t=X`).
- **Two-Tier Caching** — Raw transcripts are cached in `cache/transcripts/`; FAISS indexes are serialized to `vector_db/`. This avoids repeated network calls and prevents YouTube IP bans on repeated requests.
- **Resilient Error Handling** — `youtube_transcript_api` calls use exponential backoff (1s → 2s → 4s) to absorb transient failures. All failures return structured dictionaries rather than raising, so the server never crashes mid-ingestion and the frontend is notified gracefully.

---

## Future Improvements

- [ ] **Hybrid Search** — combine keyword search (BM25) with FAISS semantic search for better precision on names/nouns.
- [ ] **Whisper Fallback** — transcribe audio locally with OpenAI Whisper when captions are unavailable.
- [ ] **Cross-Video / Playlist Chat** — query across an entire channel or playlist, not just one video.
- [ ] **Redis-Backed Sessions** — move in-memory session state to Redis for horizontal scaling across workers.

---

## Resume Highlights

- Built a local, persistent **RAG pipeline** using **LangChain** and **FAISS**, grounding LLM responses strictly in retrieved video transcript context.
- Implemented **MMR-based retrieval** to reduce redundant context and improve answer quality on long-form video content.
- Integrated **Server-Sent Events (SSE)** in FastAPI for real-time, token-by-token response streaming to a custom Chrome Extension.
- Designed a proprietary **timestamp citation system**, linking generated answers directly back to exact moments in the source video.
- Engineered a resilient ingestion pipeline with **exponential backoff retries**, **multi-language translation fallback**, and **two-tier local caching**.

---

<p align="center">Built with Python, FastAPI, LangChain & FAISS</p>
