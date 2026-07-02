from langchain_core.runnables import (
    RunnableParallel,
    RunnablePassthrough,
    RunnableLambda,
)
from langchain_core.output_parsers import StrOutputParser
from src.prompt import prompt
from src.llm import get_llm

llm = get_llm()

def format_docs(retrieved_docs):
    return "\n\n".join( doc.page_content for doc in retrieved_docs )


def get_rag_chain(retriever):

    
    retrieve_chain = RunnableParallel({
        "source_documents": retriever,
        "question": RunnablePassthrough(),
    })  


    parser = StrOutputParser()
    answer_chain = (
        RunnablePassthrough.assign(context=lambda x: format_docs(x["source_documents"]))
        | prompt
        | llm
        | parser
    )
    
    rag_chain = retrieve_chain.assign(answer=answer_chain)

    return rag_chain