from langchain_core.runnables import RunnableSequence,RunnableParallel,RunnablePassthrough,RunnableLambda,RunnableMap,RunnableReduce
from langchain_core.output_parsers import StrOutputParser

def format_docs(retrieved_docs):
    context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)
    return context_text

parallel_chain = RunnableParallel({
    'context': retriever | RunnableLambda(format_docs),
    'question': RunnablePassthrough()  
})

parser = StrOutputParser()

main_chain = parallel_chain | prompt | llm | parser;


# possible enhancements
# UI base enhancements
# evaluation    -> *) ragas *) Langsmith
# indexing      -> *) Document ingestion *) text splitting *) vetore store
# Retrieval     -> *) pre-retrieval
                   #   -> Query rewriting using llm
                   #   -> multi_query generation
                   #   -> domain aware routing
                   #*)during retrieval
                   #   -> MMR
                   #   -> Hybrid Retrieval
                   #   -> Reranking
                   #*) post retrieval
                   #   -> Contextual compression
# Augmentation  -> *) Prompt Templating *) Answer grounding *) context window optimization
# Generation    -> *) answer with citations *) Guard railing
# System Design -> *) multiModel *) Agentic *) Memory Based