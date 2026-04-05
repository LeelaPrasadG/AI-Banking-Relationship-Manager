import os
from dotenv import load_dotenv

load_dotenv()

# Flask Configuration
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = os.getenv('DEBUG', True)
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError('OPENAI_API_KEY environment variable is required!')
OPENAI_MODEL = 'gpt-5.4'  # Using GPT-5.4 model

# Pinecone Configuration
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY', '')
PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT', 'us-east-1')
PINECONE_INDEX_NAME = 'bank-rag-index'

# Document Configuration
RAG_DOCS_PATH = os.path.join(os.path.dirname(__file__), 'RAGDocs')
LOADED_DOCUMENTS_FILE = 'loaded_documents.json'

# Document Categories
DOCUMENT_CATEGORIES = {
    'auto-loan': ['auto-loan'],
    'credit-card': ['credit-card', 'visa-mastercard'],
    'banking': ['banking']
}

# Session Configuration
PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

# Embedding Configuration
EMBEDDING_MODEL = 'text-embedding-3-small'
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
