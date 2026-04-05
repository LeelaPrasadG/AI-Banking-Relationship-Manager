# Bank RAG System - Retrieval-Augmented Generation with Role-Based Access Control

A production-ready AI-powered RAG system for banks, built with **LangChain 0.1.20**, **Pinecone 8.1.1**, **OpenAI GPT-5.4**, and **Flask 2.3.3**. Provides intelligent document retrieval with role-based access control, automatic PDF processing, and AI-powered Q&A.

## ✨ Key Features

- **Retrieval-Augmented Generation (RAG)**: Direct Pinecone SDK integration for vector search + GPT-5.4 for answer generation
- **Role-Based Access Control**: Users access only documents matching their assigned roles (Auto Loan, Credit Card, Banking)
- **Automatic Document Processing**: Scans RAGDocs folder, extracts text, chunks documents, generates embeddings, stores in Pinecone
- **Real-Time Vector Search**: Cosine similarity search with metadata filtering on 330+ document chunks
- **Web Dashboard**: Login-protected Flask interface with question answering and document browsing
- **Source Attribution**: Every answer includes source documents and relevance scores
- **User Management**: Pre-configured test users with different role combinations
- **Production-Ready**: Error handling, logging, API versioning, and security best practices

## 🏗️ Technical Architecture

### Technology Stack
| Component | Technology | Version |
|-----------|-----------|---------|
| **Web Framework** | Flask | 2.3.3 |
| **RAG Framework** | LangChain | 0.1.20 |
| **Vector DB** | Pinecone | 8.1.1 |
| **LLM** | OpenAI | GPT-5.4 |
| **Embeddings** | OpenAI | text-embedding-3-small |
| **PDF Processing** | PyPDF2 | 3.0.1 |
| **Python** | Python | 3.10+ |

### Data Flow Pipeline

```
User Query
    ↓
[Authentication Check] → Role-based filtering
    ↓
[Embedding Generation] → Convert question to embeddings
    ↓
[Vector Search] → Query Pinecone index with metadata filter
    ↓
[Document Retrieval] → Get top 4 relevant chunks per role
    ↓
[Context Assembly] → Combine chunks into context window
    ↓
[Prompt Formatting] → Create role-specific prompt with context
    ↓
[LLM Invocation] → GPT-5.4 generates answer
    ↓
[Response Formatting] → Include sources and relevance scores
    ↓
User Response with Source Attribution
```

### Document Processing Pipeline

```
RAGDocs/
    ↓
[PDF Extraction] → Extract text from all PDFs
    ↓
[Categorization] → Match filename to category (auto-loan, credit-card, banking)
    ↓
[Text Chunking] → 1000 char chunks with 200 char overlap
    ↓
[Embedding Generation] → text-embedding-3-small (1536 dimensions)
    ↓
[Vector Storage] → Upsert to Pinecone with metadata
    ↓
[Manifest Update] → Store in loaded_documents.json to prevent reload
```

```
RAG_RBAC_LangChain/
├── app.py                          # Main Flask application
├── config.py                       # Configuration settings
├── auth.py                         # User authentication & RBAC
├── document_processor.py           # Document handling & categorization
├── vector_db.py                    # Pinecone vector database management
├── rag_pipeline.py                 # LangChain RAG pipeline
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── users.json                      # User credentials (auto-generated)
├── loaded_documents.json           # Loaded documents metadata (auto-generated)
├── RAGDocs/                        # Source documents
│   ├── auto-loan-terms-and-conditions.pdf
│   ├── auto-loan-terms-and-conditions2.pdf
│   ├── credit-card-terms-conditions.pdf
│   ├── visa-mastercard-classic-gold-platinum-en.pdf
│   ├── banking_terms-and-conditions.pdf
│   └── banking2.pdf
├── templates/                      # HTML templates
│   ├── login.html
│   └── dashboard.html
└── static/                         # Static files
    ├── style.css
    └── script.js
```

## 🚀 Quick Start (5 Minutes)

### Step 1: Create Virtual Environment

```bash
cd d:\AI\Git\RAG_RBAC_LangChain

# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Key Packages:**
- Flask 2.3.3 (Web framework)
- LangChain 0.1.20 (RAG orchestration)
- Pinecone 8.1.1 (Vector database)
- OpenAI 1.3.1 (GPT-5.4 LLM)
- PyPDF2 3.0.1 (PDF processing)

### Step 3: Configure API Keys

Edit `.env` file (or create from `.env.example`):

```env
OPENAI_API_KEY=sk-proj-xxxxx  # Get from https://platform.openai.com/api-keys
PINECONE_API_KEY=pcsk_xxxxx   # Get from https://www.pinecone.io
PINECONE_ENVIRONMENT=us-east-1
```

### Step 4: Launch Application

```bash
# Ensure venv is activated
venv\Scripts\python.exe app.py

# Or on macOS/Linux
python app.py
```

**Expected Output:**
```
============================================================
Bank RAG System - Initialization
============================================================

✓ OpenAI API Key loaded from .env
✓ Using Model: gpt-5.4

✓ Connected to Pinecone index: bank-rag-index

Found 6 new documents to load:
  Processing: auto-loan-terms-and-conditions.pdf (auto-loan)
    - Extracted text: 15792 characters, 20 chunks
  ✓ Successfully added 330 document chunks to Pinecone

Starting Flask application...
Open http://localhost:5000 in your browser
```

### Step 5: Access Application

Open **http://localhost:5000** in your browser and login with:

| Role | Username | Password | Access |
|------|----------|----------|--------|
| Auto Loan | `loanagent` | `pwd123` | Auto loan documents |
| Credit Card | `cardagent` | `pwd123` | Credit card documents |
| Banking | `bankagent` | `pwd123` | Banking documents |
| Multi-Role | `cardbankagent` | `pwd123` | Credit card + banking |

## 💡 Sample Questions (Try with `loanagent` user)

Once logged in as `loanagent`, try asking these questions to test the RAG system:

### Question 1: Enrollment Requirements
**"What are the specific requirements for an individual to enroll in and use Capital One's Online Auto Finance Services?"**
- Tests: Document retrieval, answer synthesis from multiple chunks, role-based filtering

### Question 2: Business Day Definition  
**"How does Capital One define a \"Business Day\" for its auto finance services?"**
- Tests: Exact definition matching, metadata-aware context retrieval

### Question 3: Service Comparison
**"What is the difference between the \"Direct Pay (DPAY)\" and \"CarPay\" services?"**
- Tests: Comparative analysis, feature extraction, source attribution

### Question 4: Technical Requirements
**"What are the minimum technical security requirements for an Internet browser to access Capital One's Online Services?"**
- Tests: Technical specification retrieval, detail-focused answers

### Question 5: Security Responsibilities
**"What are the specific responsibilities of a user regarding the security of \"Access Information\"?"**
- Tests: Obligation matching, multi-chunk context synthesis

## � Project Structure

```
RAG_RBAC_LangChain/
├── app.py                          # Flask app + routes + document loading
├── config.py                       # Model, API keys, chunk parameters
├── auth.py                         # User authentication & RBAC
├── document_processor.py           # PDF extraction & text chunking
├── vector_db.py                    # Pinecone SDK wrapper (direct upsert)
├── rag_pipeline.py                 # RAG pipeline (vector search + LLM)
├── requirements.txt                # Dependencies (LangChain, Pinecone, etc.)
├── .env                            # Your API keys here
├── users.json                      # 4 test users (auto-generated)
├── loaded_documents.json           # Document manifest (auto-generated)
├── RAGDocs/                        # 6 PDFs → 330 vectors in Pinecone
├── templates/login.html            # Login page
├── templates/dashboard.html        # Q&A interface
├── static/style.css                # Styling
└── static/script.js                # Frontend logic
```

## 🔑 Implementation Details

### RAG Pipeline (rag_pipeline.py)
- **Vector Query**: Direct Pinecone SDK `index.query()` with role-based metadata filtering
- **Embedding**: OpenAI text-embedding-3-small (1536 dimensions)
- **LLM**: GPT-5.4 via `ChatOpenAI.invoke()`
- **Retrieval**: Top 4 chunks per role with relevance scores
- **Context**: 1000-character chunks assembled into prompt

### Vector Storage (vector_db.py)
- **Batch Upload**: Upsert all documents at once to Pinecone
- **Embeddings**: Generated via `embedding_model.embed_documents()`
- **Metadata**: Includes text content for direct retrieval
- **Filtering**: `{"category": {"$eq": role}}` for access control

⚠️ **Important for Production:**
- Change the `SECRET_KEY` in config.py
- Use environment variables for all sensitive keys
- Implement proper password hashing with different security levels
- Enable HTTPS
- Add rate limiting
- Implement session timeouts
- Add CSRF protection

## 📚 Document Categories

Documents are automatically categorized based on filenames:

### Auto Loan
- `auto-loan-terms-and-conditions.pdf`
- `auto-loan-terms-and-conditions2.pdf`

### Credit Card
- `credit-card-terms-conditions.pdf`
- `visa-mastercard-classic-gold-platinum-en.pdf`

### Banking
- `banking_terms-and-conditions.pdf`
- `banking2.pdf`

**Adding New Documents:**
1. Place PDF files in the `RAGDocs` folder
2. Name them with category keywords: `auto-loan`, `credit-card`, or `banking`
3. Restart the application
4. New documents will be automatically detected and loaded

## 🔄 Document Management

### Automatic Loading
- On first launch, all documents are scanned and loaded
- A manifest is saved in `loaded_documents.json`
- New documents (not in manifest) are loaded on subsequent launches
- Already-loaded documents are skipped to avoid duplication

### Checking Loaded Documents
1. Login to the application
2. Navigate to the "Documents" section
3. View all loaded documents organized by category

### Manual Document Refresh
To force reload all documents:
1. Delete `loaded_documents.json`
2. Restart the application

## 🤖 RAG Pipeline

### How It Works

1. **User Query**: User submits a question through the web interface
2. **Authentication Check**: System verifies user roles
3. **Vector Search**: Query is converted to embeddings and searched in Pinecone
4. **Context Retrieval**: Relevant document chunks are retrieved
5. **LLM Processing**: GPT-4 generates an answer based on retrieved context
6. **Response Generation**: Answer is formatted and displayed to user

### Search Strategy
- **Similarity Metric**: Cosine similarity
- **Embedding Model**: OpenAI's text-embedding-3-small
- **Retrieval Count**: Top 4 most relevant chunks per category
- **Context Window**: 1000 characters per chunk with 200 character overlap

## 🌐 Web Interface

### Login Page
- Username and password authentication
- Demo credentials displayed
- Error messages for failed attempts

### Dashboard
- **Ask Question**: Main interface for querying documents
- **Documents**: View all loaded documents by category
- **User Info**: Displays current user and assigned roles

### Query Interface
- Text input for questions
- Real-time response streaming
- Source document attribution
- Multi-category answer support for users with multiple roles

## 🔧 Configuration

Edit `config.py` to customize:

```python
# OpenAI Model
OPENAI_MODEL = 'gpt-5.4'

# Pinecone Settings
PINECONE_INDEX_NAME = 'bank-rag-index'

# Document Processing
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
```

## 📊 API Endpoints

### Authentication
- `POST /login` - User login
- `GET /logout` - User logout

### Query
- `POST /api/ask` - Submit a question
  - Body: `{"question": "Your question here"}`
  - Response: Answer with sources

### Information
- `GET /api/documents` - Get loaded documents list
- `GET /api/stats` - Get vector DB statistics

### Pages
- `GET /` - Home (redirects to login/dashboard)
- `GET /login` - Login page
- `GET /dashboard` - Dashboard (requires login)

## 🚨 Troubleshooting

### "Failed to process question" Error
**Cause**: Document chunks not stored in Pinecone or vector search failing
**Solution**: 
1. Check that Pinecone index has vectors: `Record count > 0` in Pinecone dashboard
2. Verify documents loaded successfully in Flask output
3. Check that metadata includes "text" field in vectors
4. Restart Flask: Delete `loaded_documents.json` and relaunch

### Documents Not Loading to Pinecone
**Cause**: Vector embedding or Pinecone SDK compatibility issues
**Solution**:
1. Verify API keys are correct in `.env`
2. Check Pinecone index exists and is accessible
3. Ensure langchain-community is upgraded: `pip install --upgrade langchain-community`
4. Delete `loaded_documents.json` and restart

### "No Role Found" Error
**Cause**: User doesn't have required role or document category doesn't match
**Solution**: 
1. Verify user roles in `users.json`
2. Ensure PDFs are named with category keywords: `auto-loan`, `credit-card`, `banking`
3. Check document category matches user's assigned role

### Slow Response Times
**Cause**: Large embeddings, slow API calls, or slow network
**Solution**:
1. Reduce chunk size in `config.py` (default: 1000)
2. Check OpenAI API rate limits
3. Monitor Pinecone query latency
4. Use `top_k=4` in queries (don't increase without reason)

### "module 'pinecone' has no attribute 'Index'" Error
**Cause**: Incompatible langchain-community version with Pinecone 8.1.1
**Solution**: 
```bash
pip install --upgrade langchain-community
# Ensure version 0.4.1 or higher
```

## � System Status & Statistics

### Current Implementation
- **Vector Database**: 330 document chunks loaded in Pinecone
- **Embedding Dimension**: 1536 (OpenAI text-embedding-3-small)
- **Average Response Time**: <2 seconds (depends on OpenAI latency)
- **Uptime**: Running on Flask development server (use Gunicorn for production)
- **Concurrent Users**: Single venv instance (scale with multiple workers)

### Document Breakdown
| Category | Documents | Chunks |
|----------|-----------|--------|
| Auto Loan | 2 PDFs | 64 chunks |
| Credit Card | 2 PDFs | 100 chunks |
| Banking | 2 PDFs | 166 chunks |
| **Total** | **6 PDFs** | **330 chunks** |

## 📊 System Status & Statistics

### Current Implementation
- **Vector Database**: 330 document chunks loaded in Pinecone
- **Embedding Dimension**: 1536 (OpenAI text-embedding-3-small)
- **Average Response Time**: <2 seconds (depends on OpenAI latency)
- **Uptime**: Running on Flask development server (use Gunicorn for production)
- **Concurrent Users**: Single venv instance (scale with multiple workers)

### Document Breakdown
| Category | Documents | Chunks |
|----------|-----------|--------|
| Auto Loan | 2 PDFs | 64 chunks |
| Credit Card | 2 PDFs | 100 chunks |
| Banking | 2 PDFs | 166 chunks |
| **Total** | **6 PDFs** | **330 chunks** |

### API and Dependencies
```
python-dotenv==1.0.0          # Environment variables
Flask==2.3.3                  # Web framework
langchain==0.1.20             # RAG orchestration
langchain-openai==0.1.1       # OpenAI integration
langchain-community==0.4.1    # Vector store integrations
pinecone==8.1.1               # Vector database
openai==1.3.1                 # GPT-5.4 API
PyPDF2==3.0.1                 # PDF processing
Werkzeug==2.3.7               # WSGI utilities
```

## 🚀 Scaling & Deployment

### For Production
1. Replace Flask dev server with Gunicorn: `pip install gunicorn`
2. Run: `gunicorn -w 4 app:app --bind 0.0.0.0:5000`
3. Add Nginx reverse proxy for SSL/TLS
4. Use RDS/PostgreSQL for user database instead of JSON
5. Implement caching layer (Redis) for embeddings
6. Set up CI/CD with GitHub Actions

### For Enterprise
1. Implement SSO (LDAP/OAuth2) for user management
2. Add audit logging for compliance
3. Use Pinecone dedicated infrastructure
4. Implement request signing for API security
5. Add analytics dashboard for usage monitoring
6. Set up alerting for API failures

## 📚 Further Reading

- [LangChain Documentation](https://python.langchain.com/)
- [Pinecone Vector Database](https://www.pinecone.io/docs/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 📝 License & Attribution

This Bank RAG System demonstrates production patterns for:
- Vector-based semantic search (Pinecone)
- Large language model integration (OpenAI GPT-5.4)
- Role-based access control in Flask
- Automatic document processing pipelines

Developed as a complete example of modern AI-powered document Q&A systems.

### Query Optimization
- Use metadata filtering for role-based access
- Adjust k (number of retrieved docs) based on needs
- Implement query caching for frequent questions

## 🔐 Data Privacy

- User passwords are hashed (Werkzeug security)
- API keys stored in environment variables, not in code
- Document content only stored in Pinecone
- Session data kept in-memory (use Redis for production)

## 📝 Logging

The application logs:
- Document loading progress
- Vector DB operations
- Query processing
- Errors and exceptions

Check console output for detailed logging information.

## 🛠️ Advanced Usage

### Custom Document Categories
Edit `config.py` `DOCUMENT_CATEGORIES` dict:

```python
DOCUMENT_CATEGORIES = {
    'category-name': ['keyword1', 'keyword2'],
}
```

### Custom User Roles
Edit `auth.py` `init_users()` function:

```python
'newuser': {
    'password': generate_password_hash('pwd123'),
    'roles': ['category-name'],
    'created_at': datetime.now().isoformat()
}
```

### Custom Prompts
Edit `rag_pipeline.py` `_create_category_prompt()` method to customize response behavior.

## 📞 Support

For issues or questions:
1. Check troubleshooting section
2. Review API key setup
3. Check application logs for errors
4. Verify document format is PDF

## 📄 License

This project is provided as-is for educational and commercial use.

## 🙏 Acknowledgments

- Built with [LangChain](https://www.langchain.com/)
- Vector database: [Pinecone](https://www.pinecone.io/)
- LLM: [OpenAI GPT-4](https://openai.com/)
- Web framework: [Flask](https://flask.palletsprojects.com/)

---

**Last Updated**: April 2026  
**Version**: 1.0.0
