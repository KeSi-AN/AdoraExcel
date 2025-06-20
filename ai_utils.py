from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import pandas as pd
import os
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the LLM
def get_llm():
    """Initialize and return the LLM with Groq."""
    return ChatGroq(
        temperature=0.1,
        model_name="llama3-70b-8192",  # Using LLaMA 3 70B through Groq
        api_key=os.getenv("GROQ_API_KEY"),
    )

def analyze_table(df: pd.DataFrame, question: str) -> str:
    """
    Analyze a table and answer questions about it using LLaMA 3.
    
    Args:
        df: DataFrame containing the table data
        question: User's question about the table
        
    Returns:
        str: Generated response
    """
    # Convert DataFrame to a readable string format
    df_str = df.head(10).to_markdown(index=False)  # Show first 10 rows for context
    
    # Create a prompt template with table context
    template = """You are a helpful data analyst assistant. Analyze the following table and answer the question.
    
Table (first 10 rows):
{table}

Question: {question}

Please provide a clear and concise answer based on the table data. If the question cannot be answered with the given data, say so.

Answer:"""

    prompt = PromptTemplate(
        input_variables=["table", "question"],
        template=template
    )
    
    # Initialize the LLM chain with streaming
    llm_chain = LLMChain(
        llm=get_llm(),
        prompt=prompt,
        verbose=True
    )
    
    try:
        # Get response from the model
        response = llm_chain.run({
            "table": df_str,
            "question": question
        })
        return response.strip()
    except Exception as e:
        return f"Error generating response: {str(e)}"

def generate_chat_response(chat_history: List[Dict[str, str]], current_question: str, table_context: pd.DataFrame = None) -> str:
    """
    Generate a response for the chat interface.
    
    Args:
        chat_history: List of previous messages in format [{"role": "user/assistant", "content": "message"}]
        current_question: The latest user question
        table_context: Optional DataFrame for table-specific questions
        
    Returns:
        str: Generated response
    """
    if table_context is not None and not table_context.empty:
        return analyze_table(table_context, current_question)
    
    # For general questions without table context
    template = """You are a helpful assistant. Continue the conversation naturally.
    
    Previous conversation:
    {history}
    
    User: {question}
    Assistant:"""
    
    # Format chat history
    history_str = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}" 
        for msg in chat_history[-5:]  # Use last 5 messages for context
    )
    
    prompt = PromptTemplate(
        input_variables=["history", "question"],
        template=template
    )
    
    llm_chain = LLMChain(
        llm=get_llm(),
        prompt=prompt,
        verbose=True
    )
    
    try:
        response = llm_chain.run({
            "history": history_str,
            "question": current_question
        })
        return response.strip()
    except Exception as e:
        return f"Error generating response: {str(e)}"
