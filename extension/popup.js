/**
 * popup.js — YouTube RAG Assistant Extension
 * -------------------------------------------
 * Flow:
 *   1. On open: ping /health → detect YouTube tab → extract video_id → POST /load-video
 *   2. On send: POST /ask → read SSE stream → render tokens → render source chips
 */

const API_BASE = "http://localhost:8000";

// ── State ──────────────────────────────────────────────────────────────────
let currentVideoId = null;
let isStreaming    = false;
let isVideoReady   = false;

// ── DOM refs ───────────────────────────────────────────────────────────────
const serverDot    = document.getElementById("server-dot");
const serverText   = document.getElementById("server-text");
const videoBanner  = document.getElementById("video-banner");
const bannerMsg    = document.getElementById("banner-msg");
const bannerVid    = document.getElementById("banner-vid");
const videoBadge   = document.getElementById("video-badge");
const chatArea     = document.getElementById("chat-area");
const emptyState   = document.getElementById("empty-state");
const sourcesSection = document.getElementById("sources-section");
const sourcesList  = document.getElementById("sources-list");
const questionInput = document.getElementById("question-input");
const sendBtn      = document.getElementById("send-btn");
const sendIcon     = document.getElementById("send-icon");

// ── Helpers ────────────────────────────────────────────────────────────────

function extractVideoId(url) {
  const patterns = [
    /[?&]v=([A-Za-z0-9_-]{11})/,
    /youtu\.be\/([A-Za-z0-9_-]{11})/,
    /\/embed\/([A-Za-z0-9_-]{11})/,
    /\/shorts\/([A-Za-z0-9_-]{11})/,
  ];
  for (const p of patterns) {
    const m = url.match(p);
    if (m) return m[1];
  }
  return null;
}

function setServerStatus(connected) {
  serverDot.className  = "dot " + (connected ? "connected" : "error");
  serverText.textContent = connected ? "Connected" : "Offline";
}

function setBannerState(state, videoId) {
  // state: "detecting" | "loading" | "ready" | "error" | "not-youtube"
  videoBadge.className = "badge";
  if (state === "detecting") {
    bannerMsg.textContent = "Detecting video…";
    bannerVid.textContent = "";
    videoBadge.classList.add("loading");
    videoBadge.textContent = "Detecting";
  } else if (state === "loading") {
    bannerMsg.textContent = "Loading video index…";
    bannerVid.textContent = videoId || "";
    videoBadge.classList.add("loading");
    videoBadge.textContent = "Loading";
  } else if (state === "ready") {
    bannerMsg.textContent = "Video ready";
    bannerVid.textContent = videoId || "";
    videoBadge.classList.add("ready");
    videoBadge.textContent = "Ready";
  } else if (state === "error") {
    bannerMsg.textContent = "Failed to load video";
    bannerVid.textContent = videoId || "";
    videoBadge.classList.add("error");
    videoBadge.textContent = "Error";
  } else if (state === "not-youtube") {
    bannerMsg.textContent = "Open a YouTube video to begin";
    bannerVid.textContent = "";
    videoBadge.textContent = "Inactive";
    videoBadge.style.background = "rgba(255,255,255,0.05)";
    videoBadge.style.color = "#6b6b8a";
  }
}

function enableInput(enabled) {
  questionInput.disabled = !enabled;
  sendBtn.disabled       = !enabled;
}

function setLoading(loading) {
  isStreaming = loading;
  sendBtn.disabled = loading;
  if (loading) {
    sendIcon.innerHTML = '<div class="spinner"></div>';
  } else {
    sendIcon.textContent = "➤";
    sendBtn.disabled = !isVideoReady;
  }
}

// ── Chat rendering ─────────────────────────────────────────────────────────

function appendUserMessage(text) {
  emptyState.style.display = "none";
  const wrap = document.createElement("div");
  wrap.className = "message";
  wrap.innerHTML = `
    <div class="msg-label user">You</div>
    <div class="bubble user">${escapeHtml(text)}</div>
  `;
  chatArea.appendChild(wrap);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function createAiBubble() {
  emptyState.style.display = "none";
  const wrap = document.createElement("div");
  wrap.className = "message";
  const bubble = document.createElement("div");
  bubble.className = "bubble ai";
  const cursor = document.createElement("span");
  cursor.className = "cursor";
  bubble.appendChild(cursor);
  wrap.innerHTML = `<div class="msg-label">AI Assistant</div>`;
  wrap.appendChild(bubble);
  chatArea.appendChild(wrap);
  chatArea.scrollTop = chatArea.scrollHeight;
  return { bubble, cursor };
}

function appendToken(bubble, cursor, token) {
  // Insert text node before the cursor
  const textNode = document.createTextNode(token);
  bubble.insertBefore(textNode, cursor);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function finaliseBubble(cursor) {
  cursor.remove();
}

function renderSources(sources) {
  if (!sources || sources.length === 0) {
    sourcesSection.style.display = "none";
    return;
  }
  sourcesList.innerHTML = "";
  sources.forEach(src => {
    const chip = document.createElement("a");
    chip.className = "source-chip";
    chip.href = src.url;
    chip.target = "_blank";
    chip.rel = "noopener noreferrer";
    chip.title = src.snippet || src.formatted;
    chip.innerHTML = `<span class="chip-icon">⏱</span>${src.formatted}`;
    sourcesList.appendChild(chip);
  });
  sourcesSection.style.display = "block";
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ── API calls ──────────────────────────────────────────────────────────────

async function pingServer() {
  try {
    const r = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    setServerStatus(r.ok);
    return r.ok;
  } catch {
    setServerStatus(false);
    return false;
  }
}

async function loadVideo(videoId) {
  setBannerState("loading", videoId);
  try {
    const r = await fetch(`${API_BASE}/load-video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: `https://www.youtube.com/watch?v=${videoId}` }),
    });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.detail || "Unknown error");
    }
    const data = await r.json();
    setBannerState("ready", videoId);
    isVideoReady = true;
    enableInput(true);
    return data;
  } catch (err) {
    setBannerState("error", videoId);
    console.error("load-video error:", err);
    return null;
  }
}

async function askQuestion(question) {
  if (!currentVideoId || !question.trim()) return;

  appendUserMessage(question);

  // Clear old sources
  sourcesSection.style.display = "none";
  sourcesList.innerHTML = "";

  const { bubble, cursor } = createAiBubble();
  setLoading(true);

  try {
    const response = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question.trim(), video_id: currentVideoId }),
    });

    if (!response.ok) {
      const err = await response.json();
      appendToken(bubble, cursor, "Error: " + (err.detail || "Request failed"));
      finaliseBubble(cursor);
      return;
    }

    // Read SSE stream
    const reader  = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by double newlines
      const events = buffer.split("\n\n");
      buffer = events.pop(); // keep incomplete trailing chunk

      for (const event of events) {
        const line = event.trim();
        if (!line.startsWith("data: ")) continue;
        try {
          const payload = JSON.parse(line.slice(6));
          if (payload.type === "token") {
            appendToken(bubble, cursor, payload.content);
          } else if (payload.type === "sources") {
            renderSources(payload.sources);
          } else if (payload.type === "error") {
            appendToken(bubble, cursor, "\n⚠ " + payload.message);
          }
          // type === "done" — nothing to do
        } catch {
          // ignore malformed event
        }
      }
    }

    finaliseBubble(cursor);

  } catch (err) {
    appendToken(bubble, cursor, "Connection error: " + err.message);
    finaliseBubble(cursor);
  } finally {
    setLoading(false);
  }
}

// ── Entry point ────────────────────────────────────────────────────────────

async function init() {
  // 1. Check server health
  const serverOk = await pingServer();
  if (!serverOk) {
    setBannerState("error", null);
    bannerMsg.textContent = "Cannot reach server. Run: uvicorn app:app --port 8000";
    return;
  }

  // 2. Get active tab URL
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url) {
    setBannerState("not-youtube", null);
    return;
  }

  const videoId = extractVideoId(tab.url);
  if (!videoId) {
    setBannerState("not-youtube", null);
    return;
  }

  currentVideoId = videoId;

  // 3. Load the video's index
  await loadVideo(videoId);
}

// ── Event listeners ────────────────────────────────────────────────────────

sendBtn.addEventListener("click", async () => {
  if (isStreaming) return;
  const q = questionInput.value.trim();
  if (!q) return;
  questionInput.value = "";
  questionInput.style.height = "auto";
  await askQuestion(q);
});

questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendBtn.click();
  }
});

// Auto-resize textarea
questionInput.addEventListener("input", () => {
  questionInput.style.height = "auto";
  questionInput.style.height = Math.min(questionInput.scrollHeight, 100) + "px";
});

// ── Boot ───────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", init);
