from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_template(
    template="""
        You are a helpful and detailed AI assistant analyzing a YouTube video transcript.
        Answer the user's question based on the provided context from the video.
        Provide a comprehensive and detailed response, explaining your answer fully rather than just saying "yes" or "no".
        If the answer is not clearly present in the context, state that it's not discussed in the video, but still provide any related information you can find in the context.

    Context: {context}
    Question: {question}

    Answer:
"""
)