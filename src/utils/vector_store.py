"""Vector store """
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import asyncio

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class VectorStoreManager():
    """ Vector store manager: fetching relevant docs or storing new docs, in local directory """
    
    def __init__(
        self,
        index_path: str = "data/vector_index",
        embedding_model: str = "text-embedding-3-small"
    ):
        """Initialize vector store manager."""
        self.index_path = Path(index_path)
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        self.text_splitter = CharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.vectorstore = None
        self._initialize_store()
        logger.info(f"Vector store manager initialized with index_path: {self.index_path}")

    def _initialize_store(self):
        """Initialize or load existing vector store."""
        try:
            if self.index_path.exists():
                logger.info("Loading existing vector store...")
                self.vectorstore = FAISS.load_local(
                    self.index_path.as_posix(),
                    self.embeddings,
                    allow_dangerous_deserialization=True  # Safe as we're loading our own files
                )
                logger.info("Vector store loaded successfully")
            else:
                logger.info(f"Creating new vector store... at {self.index_path}")
                # Create an empty document with a placeholder
                empty_doc = Document(
                    page_content="Morpho is a DeFi lending protocol focsed on isolated lending, with fully immutable markets that enable single collateral to loan pair."
                )
                self.vectorstore = FAISS.from_documents(
                    [empty_doc],
                    self.embeddings,
                )
                self._save_store()
                logger.info("New vector store created")
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}", exc_info=True)
            raise

    def _save_store(self):
        """Save vector store to disk."""
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            self.vectorstore.save_local(self.index_path.as_posix())
            logger.info("Vector store saved successfully")
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}", exc_info=True)
            raise

    async def get_context(self, query: str = "", k: int = 4) -> str:
        """Get formatted context based on query."""
        try:
            docs = await self.get_raw_context(query, k)
            if not docs:
                return "No relevant context found."
                
            result = ["Relevant Context:"]
            for i, doc in enumerate(docs, 1):
                result.append(f"\n{i}. {doc.page_content}")
                if doc.metadata:
                    result.append(f"   Metadata: {doc.metadata}")
                    
            return "\n".join(result)
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}", exc_info=True)
            return f"Error retrieving context: {str(e)}"
            
    async def get_raw_context(self, query: str = "", k: int = 4) -> List[Document]:
        """Get raw context documents."""
        try:
            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": k}
            )
            return await retriever.ainvoke(query)
        except Exception as e:
            logger.error(f"Error retrieving raw context: {str(e)}", exc_info=True)
            return []

    def add_documents(self, documents: List[Document]):
        """Add new documents to the vector store."""
        try:
            self.vectorstore.add_documents(documents)
            self._save_store()
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}", exc_info=True)
            raise

    def add_context(self, texts: List[str], metadata: Optional[List[Dict[str, Any]]] = None):
        """Add new context to the vector store."""
        try:
            if metadata is None:
                metadata = [{} for _ in texts]
            
            documents = [
                Document(page_content=text, metadata=meta)
                for text, meta in zip(texts, metadata)
            ]
            
            # Split documents into chunks
            split_docs = self.text_splitter.split_documents(documents)
            
            # Add to vector store
            self.vectorstore.add_documents(split_docs)
            self._save_store()
            
            logger.info(f"Added {len(texts)} new context items to vector store")
            logger.info(f"text: {texts}")
        except Exception as e:
            logger.error(f"Error adding context: {str(e)}", exc_info=True)
            raise
            
    async def initialize(self):
        """Async initialization of vector store"""
        if not self.vectorstore:
            await self._initialize_vectorstore()

    async def _initialize_vectorstore(self):
        """Initialize vector store with async support"""
        try:
            # Create if not exists
            self.vectorstore = await asyncio.to_thread(
                FAISS, 
                persist_directory=str(self.index_path),
                embedding_function=self.embeddings
            )
            logger.info("Vector store initialized")
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise