# 🏦 Bank RAG System - Getting Started Guide

Welcome to the Bank RAG (Retrieval-Augmented Generation) System! This is a complete, production-ready enterprise AI application with role-based access control.

## 📖 Start Here

This project is comprehensive but well-organized. Choose your path:

### 🚀 **I Want to Run It NOW** (10 minutes)
→ Go to [`QUICKSTART.md`](QUICKSTART.md)

### 📚 **I Want to Understand Everything**
→ Read [`README.md`](README.md) (comprehensive documentation)

### 🔧 **Show Me Step-By-Step Setup**
→ Follow [`SETUP.md`](SETUP.md) (detailed instructions)

### 📋 **Project Overview**
→ Check [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) (structure & components)

### 🚀 **Deploy to Production**
→ See [`DEPLOYMENT.md`](DEPLOYMENT.md) (production guide)

### 🧪 **Testing Instructions**
→ Review [`TESTING.md`](TESTING.md) (QA & testing)

---

## 💡 What This Project Does

```
┌─────────────────────────────────────────┐
│  Users Login with Credentials           │
│  ↓                                       │
│  Get Access to Specific Document Types  │
│  ↓                                       │
│  Ask Questions About Those Documents    │
│  ↓                                       │
│  Get Intelligent Answers via AI         │
└─────────────────────────────────────────┘
```

### Features Available:
- ✅ User authentication with role-based access
- ✅ Three document categories (Auto Loan, Credit Card, Banking)
- ✅ 4 pre-configured test users
- ✅ Automatic document loading and categorization
- ✅ AI-powered Q&A using GPT-4
- ✅ Vector search with Pinecone
- ✅ Beautiful web interface
- ✅ Production-ready architecture

---

## 👥 Default Users (Test Account)

| Username | Password | Access |
|----------|----------|--------|
| `loanagent` | `pwd123` | Auto Loan Documents |
| `cardagent` | `pwd123` | Credit Card Documents |
| `bankagent` | `pwd123` | Banking Documents |
| `cardbankagent` | `pwd123` | Credit Card + Banking |

---

## 📂 What's Included

### Code Files (7 core modules)
- `app.py` - Main Flask application
- `config.py` - Configuration
- `auth.py` - User authentication & RBAC
- `document_processor.py` - PDF handling
- `vector_db.py` - Pinecone integration
- `rag_pipeline.py` - AI question answering
- Templates & CSS - Web interface

### Documentation (6 guides)
- `README.md` - Full documentation
- `QUICKSTART.md` - 10-minute setup
- `SETUP.md` - Detailed instructions
- `PROJECT_SUMMARY.md` - Architecture overview
- `DEPLOYMENT.md` - Production guide
- `TESTING.md` - QA strategies

### Configuration
- `requirements.txt` - All dependencies
- `.env.example` - Environment template
- `run.bat` & `run.ps1` - Startup scripts

### Documents
- `RAGDocs/` folder with 6 sample PDFs
- Auto-categorized by filename
- Automatically loaded anytime

---

## ⚡ Quick Start (Choose Your Speed)

### **5 SECOND OVERVIEW**
This is an AI chatbot for banks with user roles. Ask it questions about documents you have access to.

### **5 MINUTE SETUP**
1. Get API keys (OpenAI, Pinecone)
2. Create `.env` file with keys
3. Run `python app.py`
4. Open http://localhost:5000
5. Login with `loanagent` / `pwd123`

### **5 HOUR DEEP DIVE**
- Read all documentation
- Understand the architecture
- Customize for your needs
- Deploy to production

---

## 🎯 Your First Steps

### Step 1: Get API Keys (5 minutes)
- OpenAI: https://platform.openai.com/api-keys
- Pinecone: https://www.pinecone.io

### Step 2: Setup Environment (2 minutes)
```bash
# Copy example
cp .env.example .env

# Edit .env with your API keys
# OPENAI_API_KEY=your-key
# PINECONE_API_KEY=your-key
```

### Step 3: Install & Run (3 minutes)
```bash
pip install -r requirements.txt
python app.py
```

### Step 4: Test (2 minutes)
- Open http://localhost:5000
- Login: `loanagent` / `pwd123`
- Ask: "What are the auto loan terms?"

---

## 🏗️ Architecture (High Level)

```
┌──────────────────────────────────────────────┐
│             Flask Web App                    │
│  (Login, Dashboard, Query Interface)         │
└────────┬──────────────────────────┬──────────┘
         │                          │
    ┌────▼────┐        ┌────────────▼────┐
    │ Auth    │        │  RAG Pipeline   │
    │ System  │        │  (LangChain)    │
    └────────┬┘        └────────┬────────┘
             │                   │
             │         ┌─────────▼─────────┐
             │         │  Pinecone Vector  │
             │         │  Database         │
             │         └─────────┬─────────┘
             │                   │
             │         OpenAI Embeddings
             │         OpenAI GPT-4
             │
    ┌────────▼──────────┐
    │ PDF Documents     │
    │ (in RAGDocs/)     │
    └───────────────────┘
```

---

## 📊 Use Cases

### For IT Teams
- Monitor which users access what
- Control document access via roles
- Deploy to company servers
- Integrate with authentication systems

### For Business Users
- Ask questions about policies
- Get quick answers from company docs
- No need to read policy manually
- Role-based information access

### For Developers
- Learn RAG architecture
- Understand Langchain
- Study Pinecone integration
- See enterprise patterns

---

## ❓ FAQ

**Q: Do I need a computer science degree?**  
A: No! Just follow the QUICKSTART.md

**Q: How much does this cost?**  
A: Free to develop. OpenAI and Pinecone have free tiers.

**Q: Can I customize the documents?**  
A: Yes! Just add PDFs to RAGDocs/ folder

**Q: Can I add more users?**  
A: Yes! Edit auth.py or users.json

**Q: Is it secure?**  
A: Development: ✓ Production: Follow DEPLOYMENT.md

**Q: How do I deploy it?**  
A: See DEPLOYMENT.md for Docker, cloud options

**Q: What if I want to change the AI model?**  
A: Edit config.py and change OPENAI_MODEL

---

## 📞 Help & Support

| Need | File |
|------|------|
| Quick setup | QUICKSTART.md |
| Full documentation | README.md |
| Step-by-step | SETUP.md |
| Project structure | PROJECT_SUMMARY.md |
| Deploy to production | DEPLOYMENT.md |
| Testing | TESTING.md |

---

## 🎉 What Happens Next?

1. **Setup** (10 min) - Get it running locally
2. **Explore** (15 min) - Try different users & questions
3. **Customize** (1 hour) - Add your own documents & users
4. **Deploy** (varies) - Put on your company server
5. **Monitor** (ongoing) - Watch usage and performance

---

## 🚀 Key Takeaways

- ✅ Complete AI system ready to use
- ✅ Role-based security built-in
- ✅ Professional web interface
- ✅ Automatic document handling
- ✅ Production-ready code
- ✅ Comprehensive documentation
- ✅ Easy to customize and extend

---

## 🎓 Learning Value

This project teaches you:

1. **RAG Systems** - How AI learns from documents
2. **Vector Databases** - Pinecone for similar document search
3. **Large Language Models** - Using GPT-4 API
4. **Web Development** - Flask applications
5. **Security** - User authentication and authorization
6. **System Architecture** - Production system design
7. **Document Processing** - PDFs to AI-ready data
8. **Deployment** - Taking systems live

---

## 💪 Ready?

### QUICK PATH (Recommended for first-timers)
[→ Go to QUICKSTART.md](QUICKSTART.md)

### DETAILED PATH (For thorough understanding)
[→ Go to README.md](README.md)

### SETUP PATH (Step-by-step walkthrough)
[→ Go to SETUP.md](SETUP.md)

---

**Time to build something amazing! Let's go! 🚀**

---

*Last Updated: April 2026 | Version: 1.0.0*
