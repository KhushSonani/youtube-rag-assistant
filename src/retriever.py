from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
import logging

logger = logging.getLogger(__name__)

MULTI_QUERY_PROMPT = PromptTemplate(
    input_variables=["question"],
    template="""You are an AI language model assistant. Your task is to generate 3 
different versions of the given user question to retrieve relevant documents from a vector 
database. By generating multiple perspectives on the user question, your goal is to help
the user overcome some of the limitations of the distance-based similarity search. 
Provide these alternative questions separated by newlines.
IMPORTANT: Ensure each question is a complete, meaningful sentence. DO NOT output blank lines, empty strings, or just spaces.

Original question: {question}"""
)


def get_retriever(vector_store, llm):

    base_retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,
            "fetch_k": 20,
            "lambda_mult": 0.5,
        },
    )

    mq_retriever = MultiQueryRetriever.from_llm(
        llm=llm,
        retriever=base_retriever,
        prompt=MULTI_QUERY_PROMPT
    )

    def robust_retrieve(query: str):
        query = query.strip()
        if not query:
            return []
            
        docs = []
        try:
            docs = mq_retriever.invoke(query)
        except Exception as e:
            logger.error(f"MultiQueryRetriever failed: {e}")
            
        if len(docs) == 0:
            logger.warning(f"MultiQueryRetriever returned 0 docs. Falling back to base retriever.")
            docs = base_retriever.invoke(query)
            
        logger.info(f"Retrieved {len(docs)} documents for query.")
        return docs

    return RunnableLambda(robust_retrieve)