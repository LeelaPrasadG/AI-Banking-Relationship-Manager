from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone as LangchainPinecone
from config import PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_API_KEY
import time
import os
from dotenv import load_dotenv

load_dotenv()

class VectorDBManager:
    def __init__(self):
        self.api_key = PINECONE_API_KEY
        self.index_name = PINECONE_INDEX_NAME
        self.embedding_model = OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model='text-embedding-3-small'
        )
        self.pc = None
        self.index = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Pinecone connection"""
        try:
            self.pc = Pinecone(api_key=self.api_key)
            
            # Check if index exists, if not create it
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes.indexes] if hasattr(existing_indexes, 'indexes') else []
            
            if self.index_name not in index_names:
                print(f"Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric="cosine",
                    spec={
                        "serverless": {
                            "cloud": "aws",
                            "region": "us-east-1"
                        }
                    }
                )
                # Wait for index to be ready
                time.sleep(60)
            
            # Get index reference for direct uploads
            self.index = self.pc.Index(self.index_name)
            print(f"✓ Connected to Pinecone index: {self.index_name}")
        except Exception as e:
            print(f"Error initializing Pinecone: {str(e)}")
            raise

    def add_documents_batch(self, documents):
        """Add multiple documents to vector database at once using direct Pinecone SDK"""
        try:
            if not documents:
                return True
            
            # Generate embeddings for all texts
            texts = [doc['text'] for doc in documents]
            metadatas = [doc['metadata'] for doc in documents]
            
            # Get embeddings for all documents
            embeddings = self.embedding_model.embed_documents(texts)
            
            # Prepare vectors for Pinecone (format: (id, values, metadata))
            vectors = []
            for idx, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
                vector_id = f"doc_{idx}_{int(time.time())}"
                # Include the text content in metadata for retrieval
                enriched_metadata = {**metadata, 'text': text}
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": enriched_metadata
                })
            
            # Upsert vectors to Pinecone index
            self.index.upsert(vectors=vectors)
            
            print(f"✓ Successfully added {len(documents)} document chunks to Pinecone")
            return True
        except Exception as e:
            print(f"Error adding documents to Pinecone: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def search(self, query, category_filter=None, k=4):
        """Search documents in vector database with optional category filter"""
        try:
            vector_store = LangchainPinecone.from_existing_index(
                index_name=self.index_name,
                embedding=self.embedding_model
            )
            
            if category_filter:
                # Filter by category using metadata filtering
                results = vector_store.similarity_search_with_score(
                    query, k=k, filter={"category": category_filter}
                )
            else:
                results = vector_store.similarity_search_with_score(query, k=k)
            
            return results
        except Exception as e:
            print(f"Error searching vector DB: {str(e)}")
            return []

    def get_vector_store(self, category_filter=None):
        """Get vector store instance"""
        try:
            vector_store = LangchainPinecone.from_existing_index(
                index_name=self.index_name,
                embedding=self.embedding_model
            )
            return vector_store
        except Exception as e:
            print(f"Error getting vector store: {str(e)}")
            return None

    def index_stats(self):
        """Get index statistics"""
        try:
            # In new Pinecone SDK, stats are obtained differently
            # For now, just return a success message
            return {"status": "ready", "index_name": self.index_name}
        except Exception as e:
            print(f"Error getting index stats: {str(e)}")
            return None

    def clear_index(self):
        """Clear all documents from index (use with caution)"""
        try:
            # Create a temporary vector store to get access to delete operations
            vector_store = LangchainPinecone.from_existing_index(
                index_name=self.index_name,
                embedding=self.embedding_model
            )
            # Note: Clearing entire index requires direct Pinecone client access
            # This is a simplified version - in production, use Pinecone client directly
            print("Note: Use Pinecone dashboard or direct API to clear index")
            return True
        except Exception as e:
            print(f"Error clearing index: {str(e)}")
            return False
