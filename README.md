# 🎥 YouTube RAG (Retrieval-Augmented Generation)

A production-ready AI pipeline converting YouTube videos into interactive, searchable knowledge bases using LLMs and Vector Search.

---

## Project Overview

**The Problem:** Finding specific information in lengthy YouTube videos requires tedious scrubbing.  
**The Solution:** This project employs **Retrieval-Augmented Generation (RAG)** to extract video transcripts, convert them to vector embeddings, and ground an LLM to answer questions using only the video's content—complete with clickable timestamp citations.

---

## Features

- **Automated Ingestion:** Fetches closed captions natively via the YouTube Transcript API (with auto-translation fallback).
- **Local FAISS Vector DB:** Stores and groups embedded chunks persistently.
- **MMR-Based Semantic Search:** Balances relevance and diversity during retrieval, preventing redundant context.
- **Timestamped Citations:** Appends clickable YouTube links to answers for instant verification.
- **Real-Time Streaming:** Uses Server-Sent Events (SSE) via FastAPI to stream responses instantly.
- **Chrome Extension UI:** Query videos directly from the YouTube page.
- **Robustness:** Two-tier caching and exponential backoff ensure high availability and prevent IP bans.

---

## Tech Stack

| Technology | Purpose | Used In |
|------------|----------|---------|
| **Python / FastAPI** | High-performance async web framework | `app.py` |
| **LangChain** | Orchestrates the RAG pipeline | `src/` |
| **FAISS** | Vector database for similarity search | `src/vectorstore.py` |
| **HuggingFace** | `all-MiniLM-L6-v2` embedding model | `src/embeddings.py` |
| **Groq (Llama-3.3-70B)** | Blazing-fast LLM inference | `src/llm.py` |
| **HTML/CSS/JS** | Chrome Extension UI | `extension/` |

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

1. **Ingestion & Processing:** The video transcript is fetched, injected with timestamp markers (`[[14.5]]`), and split into overlapping chunks (500 chars). Timestamps are saved to metadata.
2. **Embedding:** Chunks are embedded via HuggingFace and persisted locally in FAISS.
3. **Retrieval:** User queries are embedded, and the `MultiQueryRetriever` fetches the most relevant chunks using Maximal Marginal Relevance (MMR).
4. **Generation:** LangChain bundles the retrieved chunks into a prompt. Groq streams the generated answer back to the user alongside exact timestamp links.

---

## API Endpoints

- **`POST /load-video`**: Initializes the RAG session. Checks local FAISS disk, or executes full ingestion.
- **`POST /ask`**: Streams the LLM response via SSE (`text/event-stream`), returning tokens and final source citations.
- **`GET /health`**: Health check and active session monitoring.

---

## Installation & Usage

1. **Clone & Setup Environment:**
   ```bash
   git clone https://github.com/KhushSonani/youtube-rag-assistant.git
   cd youtube-rag-assistant
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Configure Variables:** Add your API key to a `.env` file:
   ```env
   GROQ_API_KEY=gsk_your_key
   ```
3. **Run Server:** `uvicorn app:app --reload --port 8000`
4. **Load Extension:** Go to `chrome://extensions/`, enable "Developer mode", click "Load unpacked", and select the `extension/` folder.
5. **Usage:** Open a YouTube video, click the extension, load the video, and ask a question!

---

## Advanced Implementation Details (Optional)

- **MMR Retrieval Strategy:** Standard similarity search often retrieves identical, redundant chunks from long videos. MMR is used to balance relevance and diversity, drastically improving the LLM's context coverage.
- **Timestamp Citation System:** During ingestion, timestamps are extracted via regex and embedded natively as LangChain Document `metadata`. Upon LLM completion, these metadata tags generate exact deep links (`youtu.be/id?t=X`).
- **Caching Mechanism:** A two-tier cache prevents YouTube IP bans. Raw transcripts are cached in `cache/transcripts/`, and FAISS indexes are serialized to `vector_db/`.
- **Error Handling:** 
  - `youtube_transcript_api` utilizes exponential backoff (1s, 2s, 4s) to bypass temporary API drops.
  - Failures are intercepted gracefully as standard dictionaries, preventing server crashes and alerting the frontend instantly.

---

## Project Structure

```text
Youtube_RAG/
├── app.py                  # FastAPI routing & SSE streaming
├── cache/ & vector_db/     # Auto-generated persistence directories
├── extension/              # Chrome Extension frontend
└── src/                    
    ├── ingestion.py        # Transcript fetching & caching
    ├── splitter.py         # Chunking & metadata extraction
    ├── retriever.py        # MMR MultiQueryRetriever configuration
    ├── rag.py              # LCEL (LangChain) pipeline
    ├── session.py          # Workflow orchestration
    └── embeddings.py, llm.py, vectorstore.py
```

---

## Resume Highlights & Future Improvements

- **Highlights:** Built a local, persistent RAG pipeline using LangChain and FAISS. Implemented MMR-based retrieval, SSE streaming, and a proprietary timestamp metadata system to link generative answers directly to video moments.
- **Future Goals:** Hybrid Search (BM25 + FAISS), Whisper fallback for missing transcripts, and Redis caching for distributed deployment.
