from langchain_community.vectorstores import FAISS
import os


DB_PATH = "vector_db"


def create_vectorstore(chunks, embedding_model):

    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embedding_model,
    )
    vector_store.save_local(DB_PATH)
    print("Vector Store Saved Successfully")
    return vector_store


def load_vectorstore(embedding_model):

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            "Vector database not found. Run indexing first."
        )

    vector_store = FAISS.load_local(
        DB_PATH,
        embedding_model,
        allow_dangerous_deserialization=True,
    )

    print("Vector Store Loaded")

    return vector_store