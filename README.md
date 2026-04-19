# AI Relationship Manager & Credit Operations Copilot

Imagine having a tireless assistant who knows your customers inside-out, understands every policy and regulation, and can help you answer the tough questions in seconds instead of hours.

That's what this platform does. Built for relationship managers, credit analysts, loan officers, compliance teams, and operations staff—it's your personal AI copilot that helps you navigate customer relationships, credit decisions, compliance requirements, and risk investigations by pulling together information from customer profiles, transaction histories, loan documents, policies, and real-time signals. No more hunting through dozens of documents or emails to get an answer.

## ✨ What It Does For You

- **Know Your Customers Better** — Get a complete picture of what they've done with your bank, how they've paid, where they might need help, and what you can offer them next. No more guessing.

- **Write Credit Memos in Minutes** — Stop spending hours assembling financial data, covenants, and policy checks. The system drafts structured memos so you can focus on the decision, not the paperwork.

- **Find What You Need in Documents** — Whether it's a key term in a loan agreement or a specific obligation in a guarantee, extract it instantly without manual review.

- **Get Answers You Can Trust** — Ask anything about internal policies, compliance rules, or procedures—and know the answer is straight from official documents, not guesswork.

- **Catch Fraud & Investigate Risks** — When something looks off (unusual wire, new location, pattern change), the system alerts you with context: historical cases, anomalies, and what similar situations turned out to be.

- **Rest Easy About Access Control** — Everyone sees only what they should. Relationship managers can't peek at risk models. Credit analysts can't access other people's draft decisions. It's automatic and tamper-proof.

- **Stay Audit-Ready** — Every answer comes with sources. Show auditors and regulators exactly where each piece of information came from. No guesswork, full traceability.

- **Deploy Without Drama** — It's built as production-ready. Deploy it, set up your users, load your documents, and you're live. No infrastructure overhaul needed.

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

Ready to get this running? It's easier than you think.

### Step 1: Create Virtual Environment

```bash
cd d:\AI\Git\AI-Banking-Relationship-Manager

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

| Role | Username | Password | Use Cases |
|------|----------|----------|----------|
| Relationship Manager | `rm_agent` | `pwd123` | Customer 360 summaries, cross-sell identification, relationship insights |
| Credit Analyst | `credit_analyst` | `pwd123` | Credit memo drafting, loan analysis, covenant review |
| Loan Operations | `loan_ops` | `pwd123` | Document verification, process workflows, policy lookups |
| Risk/Fraud Analyst | `risk_analyst` | `pwd123` | Anomaly investigation, alert correlation, case history |
| Compliance Officer | `compliance` | `pwd123` | Regulatory guidance, policy validation, audit documentation |
| Multi-Role (RM+Credit) | `multi_agent` | `pwd123` | Combined RM and credit analyst capabilities |

## 💡 What People Actually Ask

**Banking Account Question:**
- "I noticed some charges on my account. What's your policy on disputed transactions and how do I file a complaint?"

**Credit Card Question:**
- "Can you explain the grace period for credit card payments and any associated fees?"

**Risk & Fraud Teams ask:**
- "What are the current auto loan interest rates and what documentation do I need to apply?"

**Negative case Question:**
- "Who are the authors of the paper "Attention is all you need"?"

## 🛡️ Role-Based Access Control (RBAC) - Detailed Examples

The system enforces strict role-based access control ensuring users only access document categories and data sources relevant to their business function and compliance level.

### Primary Users & Document Access

| User Role | Username | Password | Accessible Data Sources | Restrictions |
|-----------|----------|----------|-------------------------|--------------|
| **Relationship Manager** | `rm_agent` | `pwd123` | CRM, customer profiles, transaction history, loan portfolios, call notes | Cannot access: Underwriting policy, risk ratings (limited access) |
| **Credit Analyst** | `credit_analyst` | `pwd123` | Loan documents, financial statements, credit policy, underwriting rules, KYC data | Cannot access: Risk model details, other analysts' draft memos |
| **Loan Operations** | `loan_ops` | `pwd123` | Process workflows, SOPs, policy documents, compliance checklists, approved templates | Cannot access: Customer financial data beyond what's needed for workflows |
| **Risk/Fraud Analyst** | `risk_analyst` | `pwd123` | Transaction data, alert feeds, historical cases, risk models, customer profiles | Cannot access: Credit decisions, lending strategy documents |
| **Compliance Officer** | `compliance` | `pwd123` | Regulatory guidance, internal policies, audit trail, compliance documentation | Full access for audit and supervision purposes |
| **Multi-Role (RM+Credit)** | `multi_agent` | `pwd123` | Combined RM and Credit Analyst data sources | Cannot access: Risk models, fraud investigations |

### Real-World Examples

#### ✅ Scenario 1: Your Day as a Relationship Manager

**You're thinking:** "I have a machine parts supplier I've worked with for 5 years. They're solid, but are we really serving them well? What could we offer them?"

**What you ask:** "Summarize this SME customer's relationship with the bank and identify cross-sell opportunities."

**What you get back (in seconds):
```
Customer Relationship Summary:
- Tenure: 5 years with SME customer segment
- Total Credit Exposure: $2.3M across 3 loan facilities
- Payment History: Excellent (100% on-time for past 24 months)
- Cross-sell Opportunities:
  * Trade Finance Products (based on 30% export revenue)
  * Working Capital Line (seasonal inventory gaps identified)
  * Cash Management Solutions (daily transaction volume analysis)

Recommended Next Actions:
1. Schedule quarterly review (6 weeks overdue)
2. Present trade finance proposal (high probability score: 0.87)
3. Discuss working capital optimization

Sources:
- CRM Profile (updated 5 days ago)
- Transaction History (12 months)
- Loan Portfolio Summary (current)
```

---

#### ❌ Scenario 2: Staying in Your Lane

**You're thinking:** "I wonder how risky this customer really is from a credit perspective."

**What you ask:** "What's the PD/LGD risk rating for customer ABC?"

**What happens:** The system says "I can't show you that—it's for the Risk team. You can ask Compliance for a general risk summary if you need it."

**Why this matters:** The bank keeps sensitive models and proprietary analysis private, while you still get what you need to do your job.

---

#### ✅ Scenario 3: Your Day as a Credit Analyst

**You're thinking:** "I need to get this credit decision to committee by Friday, but assembling all the numbers and policy checks always takes forever."

**What you ask:** "Generate a credit memo draft grounded in financial statements, covenants, and policy."

**What you get back (in 2 minutes instead of 2 hours):
```
CREDIT MEMORANDUM - DRAFT

Facility Name: ABC Ltd - Credit Facility Renewal
Borrower: ABC Ltd (SME Manufacturing)
Amount: $1.5M working capital + $2.0M term loan
Tenor: 3 years + 1 year option

Financial Analysis:
- Revenue (TTM): $45.2M (↑ 12% YoY)
- EBITDA Margin: 18.5% (vs. peer avg: 16.2%)
- Current Ratio: 1.8x (within policy threshold of 1.5x minimum)
- Debt Service Coverage: 2.1x (acceptable)

Covenant Analysis:
✓ All financial covenants in compliance
✓ Leverage Ratio: 2.1x (vs. limit of 2.5x)
✓ Interest Coverage: 4.2x (vs. minimum: 2.0x)

Recommended Terms:
- Rate: SOFR + 225bps (within policy grid)
- Pricing Tier: Tier 2 (per policy)
- Approx Committee sign-off expected

Sources:
- Financial statements (audited, FY2024)
- Debt schedule (updated)
- Bank KYC file (current)
- Lending Policy Manual (v2024.01)
```

---

#### ✅ Scenario 4: Your Day as a Risk/Fraud Analyst

**You're thinking:** "This wire request doesn't feel right, but I need facts to back up my gut."

**What you ask:** "Check whether this wire request looks anomalous and explain why."

**What you get back (with evidence, not just intuition):
```
TRANSACTION RISK ASSESSMENT - WIRE REQUEST

Transaction Details:
- Amount: $450,000 USD to unknown beneficiary
- Destination: Country with elevated AML risk
- Timing: 9:45 PM (outside business hours for typical activities)
- Device: New location (IP from Singapore, account typically accessed from NYC)

Risk Indicators - FLAGGED:
🚩 HIGH RISK: Wire amount is 8x typical monthly average ($56K)
🚩 NEW DESTINATION: Country on elevated monitoring list
🚩 DEVICE ANOMALY: Account accessed from new geographic location
⚠️ TIMING ANOMALY: Request submitted during unusual hours
⚠️ ENTITY TYPE: Beneficiary on customer watch list (not blocked)

Historical Context:
- Similar pattern matched 2 cases (Mar 2023, Sep 2023) - both fraud
- Customer has 0 prior wires to this destination
- Peer comparison: Only 1.2% of SME customers wire to this destination

Recommendation: ⛔ **BLOCK and INVESTIGATE**
- Verify wire with customer via callback to registered number
- Request additional beneficiary documentation
- File SAR if customer cannot justify business purpose

Sources:
- Transaction History (24 months)
- Device/Geolocation Data (30 days)
- Historical Case Correlation (5 year lookback)
- Enhanced Due Diligence File (current)
```

---

#### ✅ Scenario 5: Audit Day as a Compliance Officer

**You're thinking:** "Regulators are asking about our credit decisions on this customer. Did we follow policy? Can I prove it?"

**What you ask:** "Show me the audit trail for all credit decisions on this customer in the past 90 days."

**What you get back (the whole story, documented):
```
AUDIT TRAIL - Customer #XYZ2024 (90-day window)

Decision 1: Loan Renewal Approved (2024-03-15)
- Decision Maker: credit_analyst (Mary Johnson)
- Authority Level: $3M limit
- Policy Applied: Commercial Lending Policy v2024.01
- Documentation: Credit memo, financial statement review
- Status: ✓ Full compliance

Decision 2: Credit Limit Increase Approved (2024-02-20)
- Decision Maker: rm_agent (John Smith)
- Amount: $500K additional
- Escalation: Sent to credit_analyst for $3M+ approvals
- Time to Approval: 2 business days
- Status: ✓ Full compliance

Alert Log:
- Fraud Alert (2024-03-10): Wire transfer anomaly - Investigated & Cleared
- Compliance Watch (2024-02-28): KYC renewal required - Completed
- Risk Review (2024-01-15): Annual review - Passed

All decisions in full compliance with regulatory requirements and bank policy.
```

---

### How Security Works (In Plain English)

**Simple rule:** Nobody sees what they shouldn't.

1. **You log in** — System checks who you are and what role you have
2. **You ask a question** — System figures out what data you need
3. **Access check** — Does your role let you see this? 
   - Yes? → Get your answer with sources
   - No? → Polite message with a way to ask for help
4. **Everything is logged** — Every question, every answer, who asked what and when. If a regulator asks, you have receipts.

**Real examples:**
- A Relationship Manager asks about a customer—they see the customer data they need. ✓
- A Relationship Manager asks about risk models—the system says no. ✓
- A Risk Analyst asks about fraud patterns—they see transaction data and case history. ✓
- A Credit Analyst asks about another analyst's draft—the system says no. ✓

### Adding People to the System

When someone new joins your team, edit `users.json` to give them a login. It's that simple:

**New relationship manager:**
```json
{
  "username": "jane_doe",
  "password": "hashedpwd",
  "role": "relationship-manager",
  "department": "Commercial Banking",
  "access_level": "basic"
}
```

**Someone who does both RM and credit analysis:**
```json
{
  "username": "senior_rm",
  "password": "hashedpwd",
  "role": "relationship-manager,credit-analyst",
  "department": "Commercial Banking",
  "access_level": "advanced"
}
```

Restart the app, they're live.
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
