import os
from dotenv import load_dotenv

load_dotenv()

# Flask Configuration
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DEBUG = os.getenv('DEBUG', True)
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# OpenAI Configuration (used for embeddings only)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError('OPENAI_API_KEY environment variable is required!')

# Groq Cloud Configuration (used for LLM inference)
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    raise ValueError('GROQ_API_KEY environment variable is required!')
XAI_BASE_URL = 'https://api.groq.com/openai/v1'
OPENAI_MODEL = 'openai/gpt-oss-120b'  # Groq model

# Cohere Configuration (used for re-ranking retrieved chunks)
COHERE_API_KEY = os.getenv('COHERE_API_KEY')
COHERE_RERANK_MODEL = 'rerank-v3.5'

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

# Guardrail Configuration
# Set to True to enable LLM-based scope classification for ambiguous questions.
# Disabling falls back to keyword-only checks (faster, no extra LLM call).
GUARDRAIL_LLM_SCOPE_CHECK_ENABLED = True
# Logging level for guardrail events: 'WARNING' to log only violations, 'INFO' for all events.
GUARDRAIL_LOG_LEVEL = 'WARNING'

# Application Logging
# Controls overall flow-trace logging level. Set to 'DEBUG' for maximum verbosity,
# 'INFO' to trace the request/response flow, 'WARNING' for errors only.
# Can be overridden via the LOG_LEVEL environment variable.
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ---------------------------------------------------------------------------
# Cost Monitoring Configuration
# ---------------------------------------------------------------------------
COST_MONITORING_ENABLED = True
COST_LOG_FILE = 'cost_log.json'

# Token pricing in USD per 1,000 tokens.
# Update these to match your OpenAI billing tier.
# Current public rates (April 2026) — verify at https://openai.com/pricing
COST_PER_1K_TOKENS: dict = {
    # xAI Grok models — verify current rates at https://x.ai/api#pricing
    'openai/gpt-oss-120b':        {'input': 0.005,   'output': 0.015},
    'grok-3':                     {'input': 0.003,   'output': 0.015},
    'grok-3-mini':                {'input': 0.0003,  'output': 0.0005},
    'grok-2':                     {'input': 0.002,   'output': 0.010},
    # OpenAI models (embeddings)
    'text-embedding-3-small':     {'input': 0.00002, 'output': 0.0},
    'text-embedding-3-large':     {'input': 0.00013, 'output': 0.0},
    # Fallback for unknown models
    'default':                    {'input': 0.005,   'output': 0.015},
}

# Alert thresholds (USD).  Set to 0 to disable a specific alert.
COST_ALERT_PER_REQUEST_USD  = 0.10   # alert if a single request costs more than this
COST_ALERT_PER_USER_DAY_USD = 1.00   # alert if one user's daily spend exceeds this
COST_ALERT_TOTAL_DAY_USD    = 10.00  # alert if aggregate daily spend exceeds this
