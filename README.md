# 🎥 YouTube RAG (Retrieval-Augmented Generation)

A production-ready AI pipeline that converts any YouTube video into an interactive, searchable knowledge base using Large Language Models (LLMs) and Vector Search.

---

## 2. Project Overview

**The Problem:** Video content is notoriously difficult to search. If you are watching a 2-hour lecture or podcast, finding the exact moment a specific topic was discussed requires tedious scrubbing and skimming. 

**The Solution:** This project solves that by employing **Retrieval-Augmented Generation (RAG)**. By extracting a video's transcript and transforming it into vector embeddings, the system creates a semantic knowledge base. When a user asks a question, the application doesn't just rely on general AI knowledge; it retrieves the exact transcript chunks relevant to the question and feeds them to an LLM.

**What makes it different from a normal chatbot?**
A standard chatbot (like ChatGPT) relies purely on its pre-trained data and has no direct knowledge of the specific YouTube video you are currently watching. This project is strictly grounded to the video's content. It also preserves original timestamps, allowing the AI to cite its sources and immediately jump the user to the exact second in the video where the answer originated.

---

## 3. Features

- **YouTube URL Input:** Automatically handles various YouTube URL formats (standard, shorts, youtu.be, embed).
- **Intelligent Transcript Fetching:** Uses the YouTube Transcript API to fetch closed captions natively.
- **Automatic Language Fallback:** Attempts to fetch English transcripts; automatically falls back to translating Hindi or other available auto-generated languages to English.
- **Local Transcript Caching:** Saves fetched transcripts to the local disk to avoid repetitive API requests and prevent rate-limiting/IP-blocking.
- **FAISS Vector Database:** Stores embedded chunks in a persistent, locally saved vector database, grouped per video ID.
- **Semantic Search:** Uses HuggingFace embeddings to understand the true meaning of the user's question, rather than just exact keyword matching.
- **MultiQueryRetriever:** Generates multiple variations of a user's question to maximize the chances of retrieving the correct context.
- **LLM-Powered Answers:** Utilizes Groq's blazing-fast Llama-3.3-70b-versatile model to synthesize natural, accurate answers.
- **Streaming Responses (SSE):** Answers stream token-by-token back to the user instantly (Server-Sent Events), eliminating long loading screens.
- **Timestamped Citations:** Preserves start and end times during text splitting, appending clickable timestamp links to the generated answer.
- **Chrome Extension UI:** A sleek frontend allowing users to query the video directly from the YouTube page.
- **FastAPI Backend:** A highly asynchronous, production-grade Python server handling orchestration.
- **Robust Error Handling:** Exponential backoff retries and graceful failure dicts ensure the API never crashes during ingestion.
- **Detailed Logging:** System logs cache hits, fetch counts, chunk counts, and source languages for easy debugging.

---

## 4. Tech Stack

| Technology | Purpose | Used In |
|------------|----------|---------|
| **Python** | Core programming language. | Entire Backend |
| **FastAPI** | High-performance async web framework. | `app.py` |
| **LangChain** | Orchestrates the RAG pipeline (splitters, retrievers, LCEL). | `src/splitter.py`, `src/rag.py`, `src/session.py` |
| **FAISS** | Facebook AI Similarity Search vector database. | `src/vectorstore.py` |
| **Groq (ChatGroq)** | Lightning-fast inference provider for LLMs. | `src/llm.py` |
| **Llama-3.3-70B** | The Large Language Model generating the final answers. | `src/llm.py` |
| **HuggingFace** | Provides the `all-MiniLM-L6-v2` embedding model. | `src/embeddings.py` |
| **youtube-transcript-api** | Extracts closed captions directly from YouTube. | `src/ingestion.py` |
| **Server Sent Events (SSE)** | Streams the LLM output token-by-token over HTTP. | `app.py` |
| **JavaScript/HTML/CSS** | Frontend interface for the end-user. | `extension/` |
| **dotenv** | Environment variable management. | `src/llm.py`, `.env` |
| **Logging** | Tracks application flow and catches errors. | `app.py`, `src/ingestion.py` |

---

## 5. Complete Project Architecture

The architecture represents a complete end-to-end RAG system.

```text
  [ Chrome Extension (User Interface) ]
                |
                |  (HTTP POST /load-video)
                v
       [ FastAPI Backend ]
                |
                v
    [ Transcript Fetching ] -> Checks cache. If missing, calls YouTube API.
                |              Handles translation and exponential backoff.
                v
         [ Chunking ] -> LangChain RecursiveCharacterTextSplitter.
                |        Preserves timestamps in chunk metadata.
                v
        [ Embeddings ] -> Converts text chunks into MiniLM vectors.
                |
                v
       [ FAISS Vector DB ] -> Persists vectors locally under vector_db/<video_id>
                |
                = (User asks a question via POST /ask)
                |
                v
       [ Retriever ] -> MultiQueryRetriever queries FAISS for semantic matches.
                |
                v
     [ Prompt Construction ] -> Merges context chunks with the user query.
                |
                v
         [ Groq LLM ] -> Generates response based strictly on the context.
                |
                v
   [ Streaming Answer (SSE) ] -> Streams tokens back to the Chrome Extension.
                |
                v
     [ Timestamp Citations ] -> Attaches clickable YouTube timestamp links.
```

1. **Initialization:** The user loads a video. The backend checks for an existing FAISS index. If missing, it ingests the transcript, splits it, embeds it, and saves it to FAISS.
2. **Querying:** The user submits a question. The query is embedded, and FAISS returns the top nearest chunks.
3. **Generation:** LangChain bundles the chunks into a prompt. Groq streams the answer back to the extension alongside exact timestamp citations.

---

## 6. Folder Structure

```text
Youtube_RAG/
├── .env                    # Secret keys (Groq API key, etc.)
├── requirements.txt        # Python dependencies
├── app.py                  # Main FastAPI application and routing
├── main.py                 # (Optional/Legacy) Script entrypoint
├── test_ask.py             # Sandbox/tests for querying
├── temp.py                 # Scratchpad for testing
│
├── cache/                  # Auto-generated cache folder
│   └── transcripts/        # Raw .txt transcripts saved to prevent IP bans
│
├── data/                   # Fallback/sample data directory
│
├── extension/              # Chrome Extension UI
│   ├── manifest.json       # Chrome configuration
│   ├── popup.html          # Extension UI layout
│   └── popup.js            # Frontend logic and API communication
│
├── src/                    # Core RAG Business Logic
│   ├── embeddings.py       # Defines the HuggingFace embedding model
│   ├── ingestion.py        # YouTube transcript extraction & formatting
│   ├── llm.py              # Configures the Groq LLM connection
│   ├── prompt.py           # Defines the system prompt for the LLM
│   ├── rag.py              # Builds the LangChain LCEL answering chain
│   ├── retriever.py        # Configures the FAISS similarity searcher
│   ├── session.py          # Orchestrates per-video workflows & state
│   ├── splitter.py         # Handles text chunking and timestamp extraction
│   └── vectorstore.py      # Manages FAISS saving/loading operations
│
└── vector_db/              # Auto-generated FAISS indexes
    └── <video_id>/         # Directory for specific video's index files
```

---

## 7. Detailed File Explanation

### `app.py`
- **Responsibility:** The web server entry point.
- **Implementation:** Uses FastAPI. Includes a `lifespan` context manager to load the LLM and Embedding models once at startup.
- **Endpoints:**
  - `/load-video`: Manages session orchestration. Determines whether to load FAISS from disk or run ingestion from scratch.
  - `/ask`: Uses `AsyncGenerator` to yield Server-Sent Events from the LangChain stream, packaging final timestamps at the end.

### `src/session.py`
- **Responsibility:** Coordinator module.
- **Implementation:** Wires together `ingestion`, `splitter`, `vectorstore`, and `rag`. Provides `build_session()` for fresh videos and `load_session()` for previously cached videos.

### `src/ingestion.py`
- **Responsibility:** Fetches and normalizes YouTube transcripts.
- **Implementation:** Checks `cache/transcripts/`. If a miss, uses `youtube_transcript_api` to fetch captions. Applies 3 retries with exponential backoff. Prepends exact `[[start]]` markers to every chunk (e.g., `[[14.5]] Hello world`). Fails gracefully via a structured dict.

### `src/splitter.py`
- **Responsibility:** Chunks massive transcripts into bite-sized documents.
- **Implementation:** Uses `RecursiveCharacterTextSplitter` (size 500, overlap 50). Employs Regex to extract the `[[start]]` markers, dropping them from the raw text and injecting them cleanly into `doc.metadata["start"]`.

### `src/vectorstore.py`
- **Responsibility:** Disk persistence.
- **Implementation:** Simple wrapper around `FAISS.from_documents()`. Saves binary `.faiss` and `.pkl` index files directly to the `vector_db/` folder.

### `src/retriever.py`
- **Responsibility:** Semantic search configuration.
- **Implementation:** Defines a `MultiQueryRetriever` (or similar configured retriever) to query the FAISS database effectively.

### `src/embeddings.py` & `src/llm.py`
- **Responsibility:** Model instantiations.
- **Implementation:** `embeddings.py` initializes `HuggingFaceEmbeddings` (MiniLM). `llm.py` initializes `ChatGroq` (Llama 3) with `streaming=True`.

### `src/rag.py`
- **Responsibility:** The LangChain Expression Language (LCEL) chain.
- **Implementation:** Combines the retrieved source documents, parses them via `format_docs`, injects them into the custom `prompt`, and pipes the output to the LLM and `StrOutputParser`.

---

## 8. RAG Pipeline

The pipeline transforms raw video into a queryable database:
1. **Retrieval:** The transcript is downloaded.
2. **Preprocessing:** Time markers are injected directly into the raw strings.
3. **Chunking:** The script is cut into 500-character overlapping chunks to ensure context isn't lost mid-sentence.
4. **Metadata:** The `splitter.py` regex extracts the timestamps and embeds them as metadata. This keeps the vector text clean for the embedding model, while preserving the time code.
5. **Embeddings:** Each text chunk is converted into a high-dimensional vector.
6. **Vector Storage:** FAISS stores these vectors alongside their metadata on the local filesystem.

---

## 9. Retrieval Process

When a user asks: *"What is the main ingredient?"*
1. **Query:** The question is passed to the backend.
2. **Embeddings:** The question is converted into a MiniLM vector.
3. **Similarity Search:** FAISS calculates the Cosine Similarity between the question vector and all chunk vectors, returning the top matches.
4. **Prompt Creation:** The text from the matched chunks is injected into the LLM prompt.
5. **LLM Inference:** Llama-3 reads the prompt (containing the transcript segments) and answers the question.
6. **Streamed Response:** The answer streams back to the frontend immediately.

---

## 10. Timestamp Citation System

Without citations, a RAG system provides no proof. This project uses a highly effective timestamping system:
- **Preservation:** `ingestion.py` pairs every sentence with its start time `[[time]] sentence`.
- **Extraction:** `splitter.py` strips the `[[time]]` out of the text (so it doesn't confuse the LLM) but saves it into `doc.metadata["start"]`.
- **Generation:** Once the LLM finishes streaming its text answer, `app.py` intercepts the `source_documents` generated by LangChain.
- **Citations:** It extracts `metadata["start"]`, formats it to `HH:MM:SS`, and yields a final JSON array containing direct `https://youtu.be/{id}?t={time}s` URLs, allowing users to click and jump directly to the source.

---

## 11. Caching Mechanism

Because YouTube aggressively rate-limits IPs fetching transcripts, caching is critical.
- **Transcript Cache:** Stored in `cache/transcripts/`. Next time the same video is requested, ingestion hits the cache file, bypassing the network and saving ~1-2 seconds.
- **Vector Cache:** Stored in `vector_db/`. Embedding 10,000 words takes time and CPU. FAISS serializes the database to disk, allowing instant re-loads on server restart.

---

## 12. API Documentation

### `POST /load-video`
- **Purpose:** Initializes the RAG session for a given video.
- **Request Body:** `{"url": "https://www.youtube.com/watch?v=..."}`
- **Response:** 
  ```json
  {
    "status": "success",
    "video_id": "dQw4w9WgXcQ",
    "chunks": 45,
    "source": "ingested" // or "disk" / "memory"
  }
  ```

### `POST /ask`
- **Purpose:** Queries the loaded video using Server-Sent Events (SSE).
- **Request Body:** `{"video_id": "dQw4w9WgXcQ", "question": "What is this video about?"}`
- **Response:** `text/event-stream` stream yielding tokens and final sources.

### `GET /health`
- **Purpose:** Checks server uptime and lists currently loaded sessions in memory.

---

## 13. Error Handling

- **Transcript Unavailable:** Caught gracefully. If a video has disabled captions or is blocked, `get_transcript` returns a structured dictionary instead of throwing a stack trace. `app.py` intercepts this and alerts the user directly in the UI.
- **Retry Mechanism:** Exponential backoff (1s, 2s, 4s) absorbs temporary API connection drops.
- **Invalid URL:** RegEx safely validates and rejects non-YouTube URLs.
- **Missing FAISS:** The system checks `index_exists()`. If missing, it automatically falls back to full re-ingestion rather than crashing.

---

## 14. Installation Guide

**1. Clone the repository:**
```bash
git clone https://github.com/your-username/youtube-rag.git
cd youtube-rag
```

**2. Create a Virtual Environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**3. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**4. Configure Environment Variables:**
Create a `.env` file in the root directory.
```bash
GROQ_API_KEY=gsk_your_api_key_here
```

**5. Run the FastAPI Server:**
```bash
uvicorn app:app --reload --port 8000
```

**6. Load the Chrome Extension:**
- Open Chrome and navigate to `chrome://extensions/`
- Enable **"Developer mode"** in the top right.
- Click **"Load unpacked"** and select the `extension/` folder inside this repository.

---

## 15. Environment Variables

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Authenticates your application with Groq's servers to allow usage of the high-speed Llama-3 model. You can get a free API key at console.groq.com. |

---

## 16. How to Use

1. Start your `uvicorn` backend server.
2. Open any YouTube video in Google Chrome.
3. Click the YouTube RAG Extension icon in your browser toolbar.
4. The extension will automatically grab the current URL. Click **"Load Video"**.
5. Type a question like *"Summarize the main points of this lecture."* and click **Ask**.
6. Watch the answer stream in instantly.
7. Click the timestamped chips at the bottom of the answer to jump exactly to that point in the video!

---

## 17. Performance Optimizations

- **Groq LPU Processing:** Utilizing Groq instead of standard GPU providers allows token generation speeds exceeding 300+ tokens per second.
- **FAISS vs Heavy DBs:** By using local FAISS indexes instead of heavy network databases (like Pinecone or Qdrant), we eliminate network latency during the retrieval step.
- **Asynchronous Streaming (SSE):** The user receives the first word of the answer in milliseconds rather than waiting for the entire paragraph to generate.
- **Caching:** Multi-tier caching (Text cache + Vector cache) ensures returning users experience zero loading times.

---

## 18. Future Improvements

- **Hybrid Search:** Combine keyword search (BM25) with semantic vector search (FAISS) to improve accuracy on specific noun/name lookups.
- **Whisper Integration:** If a video lacks transcripts, automatically download the audio track and transcribe it locally using OpenAI's Whisper model.
- **Cross-Video Chat:** Allow users to chat across an entire YouTube Playlist or Channel rather than a single video.
- **Redis Caching:** Move the in-memory `video_sessions` dictionary to a Redis cluster to allow the FastAPI application to scale horizontally across multiple workers.

---

## 19. Resume Highlights

- **Designed and developed a Retrieval-Augmented Generation (RAG) system** capable of parsing, indexing, and semantically querying YouTube videos using LangChain and FastAPI.
- **Engineered a scalable ingestion pipeline** that extracts auto-generated captions, applies exponential backoff retries, and translates multiple languages to English using the YouTube Transcript API.
- **Implemented a highly optimized chunking and vector storage strategy** using FAISS and HuggingFace MiniLM, persisting indexes locally to achieve sub-second retrieval latency.
- **Integrated Server-Sent Events (SSE)** in FastAPI to stream LLM outputs directly to a custom Chrome Extension, ensuring real-time conversational UX.
- **Developed a proprietary timestamp citation system**, extracting timestamp metadata during document splitting to provide users with direct, clickable deep-links to specific moments in the video.
- **Reduced API dependency and improved stability** by creating a two-tier local caching mechanism for raw transcripts and serialized vector databases.
- **Leveraged Groq’s LPU infrastructure** with Llama-3.3-70B to achieve lightning-fast inference and context synthesis.

---

## 20. Key Learnings

- **RAG Architecture:** Mastered the complex interaction between retrievers, prompts, and Large Language Models to solve hallucinations.
- **LangChain (LCEL):** Deepened understanding of LangChain Expression Language for building robust, parallelized processing chains.
- **Vector Similarity:** Gained practical experience in high-dimensional semantic search and chunking strategies (handling overlap and metadata).
- **FastAPI & Async:** Learned how to utilize Python's async/await alongside HTTP Streaming architectures (SSE) to bypass traditional request-response bottlenecks.
- **Chrome Extensions:** Understood the mechanics of bridging web applications with browser extensions natively.
