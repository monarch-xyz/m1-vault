from langchain_community.document_loaders import PyPDFLoader
import os
import asyncio
import sys

# Add src directory to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from utils import VectorStoreManager


file_path = "scripts/morpho-docs-dump.pdf"

# Initialize vector store
vector_store = VectorStoreManager("data/morpho_knowledge")

async def main():
    # Add context
    loader = PyPDFLoader(file_path)
    pages = []
    async for page in loader.alazy_load():
        pages.append(page)

    vector_store.add_documents(pages)

if __name__ == "__main__":
    asyncio.run(main())