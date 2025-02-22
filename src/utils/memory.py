from supabase.client import Client, create_client
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from config import Config
from langchain_core.documents import Document
import os
import chromadb
import logging

# Get the standard Python logger
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize vector store
long_term_memory = SupabaseVectorStore(
    client=supabase,
    embedding=OpenAIEmbeddings(openai_api_key=Config.OPENAI_API_KEY),
    table_name="documents",
    query_name="match_documents"
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
          "type": str: "information","documentation","news"
        }
    """
    long_term_memory.add_documents([Document(
        page_content=summary,
        metadata=metadata,
    )])

    logger.info(f"Added {metadata['type']} to long term memory: {summary}")

@tool
async def get_long_term_memory(query: str, filter: dict):
    """
    Get the long term memory

    Args:
        query: The query to search the long term memory
        filter: The filter by metadata, example: {"type": "user", "timestamp": 1723081200}
    """
    docs = long_term_memory.similarity_search(
        query,
        k=5,
        filter=filter
    )

    formatted_memory = ""
    for doc in docs:
        formatted_memory += f"[{doc.metadata['type']}] {doc.page_content}\n"

    return formatted_memory
