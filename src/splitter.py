import re 
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging

logger = logging.getLogger(__name__)


def split_text(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    
    docs = splitter.create_documents([text])
    marker_pattern = re.compile(r"\[\[(\d+\.?\d*)\]\]")
    for doc in docs:
        matches = marker_pattern.findall(doc.page_content)
        if matches:
            start_time = float(matches[0])
            end_time = float(matches[-1])
            doc.metadata["start"] = start_time
            doc.metadata["end"] = end_time
        doc.page_content = marker_pattern.sub("", doc.page_content).strip()
        
    logger.info(f"Created {len(docs)} chunks from transcript.")
    return docs