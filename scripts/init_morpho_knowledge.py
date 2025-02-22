from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from supabase.client import Client, create_client
from dotenv import load_dotenv
import os
import asyncio
import sys

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
file_path = "scripts/morpho-docs-dump.pdf"

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize vector store
knowledge_store = SupabaseVectorStore(
    client=supabase,
    embedding=OpenAIEmbeddings(openai_api_key=openai_api_key),
    table_name="documents",
    query_name="match_documents"
)

async def main():
    # Add context
    loader = PyPDFLoader(file_path)
    pages = []
    async for page in loader.alazy_load():
        pages.append(page)

    try:
        knowledge_store.add_documents(pages)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())