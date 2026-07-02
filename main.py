import os
from src.ingestion import get_transcript
from src.splitter import split_text
from src.embeddings import get_embedding_model
from src.vectorstore import create_vectorstore, load_vectorstore
from src.retriever import get_retriever
from src.rag import get_rag_chain
from src.llm import get_llm

import os
import logging

# logging.basicConfig(level=logging.INFO)
# logging.getLogger(
#     "langchain.retrievers.multi_query"
# ).setLevel(logging.INFO)


video_id = "Gfr50f6ZBvo"

embedding_model = get_embedding_model()
llm = get_llm()

# Build FAISS only once
if not os.path.exists("vector_db/index.faiss"):

    print("Creating Vector Database...")
    transcript = get_transcript(video_id)
    chunks = split_text(transcript)
    vector_store = create_vectorstore(chunks,embedding_model,)
else:
    vector_store = load_vectorstore(embedding_model,)


# Retrieval

retriever = get_retriever(vector_store,llm)
question = "Is the topic of mind discussed in this video? If yes, what was discussed?"

rag_chain = get_rag_chain(retriever)

sources = None
print("Answer:\n")

for chunk in rag_chain.stream(question):
    if "answer" in chunk:
        print(chunk["answer"], end="", flush=True)
    if "source_documents" in chunk:
        sources = chunk["source_documents"]
        
print("\n\nSources:\n")
for i, doc in enumerate(sources):
    start = doc.metadata.get("start")
    if start is not None:
        start_int = int(start)
        hours = start_int // 3600
        minutes = (start_int % 3600) // 60
        seconds = start_int % 60
        formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        url = f"https://youtu.be/{video_id}?t={start_int}s"
        print(f"{formatted_time} - {url}")