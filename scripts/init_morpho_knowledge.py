from langchain_community.document_loaders import PyPDFLoader
import os
import asyncio
import sys
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import chromadb

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

storeage_path = "data/morpho_knowledge"

file_path = "scripts/morpho-docs-dump.pdf"

# Initialize Chroma client
chroma_client = chromadb.HttpClient(
    host=os.getenv("VECTOR_DB_URL"),
    port=os.getenv("VECTOR_DB_PORT")
)
chroma_client.get_or_create_collection("morpho_knowledge")

# Initialize vector store
knowledge_store = Chroma(
    client=chroma_client,
    collection_name="morpho_knowledge",
    embedding_function=OpenAIEmbeddings(openai_api_key=openai_api_key),
)

async def main():
    # Add context
    loader = PyPDFLoader(file_path)
    pages = []
    async for page in loader.alazy_load():
        pages.append(page)

    knowledge_store.add_documents(pages)

if __name__ == "__main__":
    asyncio.run(main())