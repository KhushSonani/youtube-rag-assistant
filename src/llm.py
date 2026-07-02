from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_llm():

    return ChatGroq(
        model="llama-3.3-70b-versatile",
        streaming=True,
        temperature=0.2,
    )

    