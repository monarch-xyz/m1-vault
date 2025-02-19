from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from config import Config
from langchain_core.documents import Document
import os
import chromadb

# same instance as the one in main.py
from utils.logger import logger

# Initialize Chroma client
chroma_client = chromadb.HttpClient(
    host=os.getenv("VECTOR_DB_URL"),
    port=os.getenv("VECTOR_DB_PORT")
)
chroma_client.get_or_create_collection("long_term_memory")

# Initialize vector store
long_term_memory = Chroma(
    client=chroma_client,
    collection_name="long_term_memory",
    embedding_function=OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY),
)

@tool
async def add_long_term_memory(summary: str, metadata: dict):
    """
    Add a summary to the long term memory, the summary should be new perspective, insights, and not include temporary data like util rate or market rate.

    Args:
        summary: The message to add to the long term memory

        metadata: {
          "timestamp": int,
          "user_id": str,
          "type": str ("user", "information", "admin")
        }
    """
    long_term_memory.add_documents([Document(
      page_content=summary,
      metadata=metadata,
      )])

    await logger.memory("Memory", {
        "summary": summary,
        "type": metadata["type"]
    })

@tool
async def get_long_term_memory(query: str, filter: dict):
    """
    Get the long term memory

    Args:
        query: The query to search the long term memory
        filter: The filter by metadata, example: {"type": "user", "timestamp": 1723081200}
    """
    docs = long_term_memory.similarity_search(query, k=5, filter=filter)

    formatted_memory = ""
    for doc in docs:
        formatted_memory += f"[{doc.metadata['type']}] {doc.page_content}\n"

    return formatted_memory
