# Quick Start Guide - Bank RAG System

Follow these steps to get the Bank RAG System running in 10 minutes.

## ⚡ Quick Setup

### Step 1: Navigate to Project Directory
```bash
cd d:\AI\Git\RAG_RBAC_LangChain
```

### Step 2: Create Virtual Environment (Optional)
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Get Your API Keys

#### Get OpenAI API Key:
1. Visit https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (it only shows once)

#### Get Pinecone API Key:
1. Visit https://www.pinecone.io
2. Sign up for free
3. Create a new project
4. Go to API Keys section
5. Copy your API key
6. Note your environment (usually `us-east-1`)

### Step 5: Configure Environment
1. Open `.env.example`
2. Replace with your actual API keys:
   ```
   OPENAI_API_KEY=sk-xxxxxxxxxxxxx
   PINECONE_API_KEY=pcak_xxxxxxxxxxxxx
   ```
3. Save as `.env`

### Step 6: Run the Application
```bash
python app.py
```

### Step 7: Open in Browser
```
http://localhost:5000
```

## 🧪 Test the System

### Login with Test User
- **Username**: `loanagent`
- **Password**: `pwd123`

### Ask a Question
Try asking about auto loans:
- "What are the terms and conditions for auto loans?"
- "What is the interest rate?"
- "What documents do I need for an auto loan?"

### Try Other Users
1. **cardagent** / pwd123 - Credit card questions
2. **bankagent** / pwd123 - Banking questions
3. **cardbankagent** / pwd123 - Both credit card and banking

### Test Role-Based Access
Login as `loanagent` and ask about "credit card" - it should say:
> "Role not supported for Credit Card Information"

## 📊 What's Happening Behind the Scenes

### Document Loading
When you start the app:
```
✓ Found 6 documents
✓ Converting PDFs to text
✓ Splitting into 1000-char chunks
✓ Creating embeddings with OpenAI
✓ Storing in Pinecone vector database
✓ Saving manifest to loaded_documents.json
```

### First Query Processing
1. User asks a question
2. System converts question to embedding
3. Searches Pinecone for similar text chunks
4. Retrieves relevant document sections
5. Sends to GPT-4 with context and role constraints
6. Returns answer with source documents

## 🐛 Quick Troubleshooting

### Error: "Module not found"
```bash
# Install missing packages
pip install -r requirements.txt
```

### Error: "OPENAI_API_KEY not set"
- Check `.env` file exists and has correct key
- Make sure you didn't use quotes around the key

### Error: "Cannot connect to Pinecone"
- Verify API key is correct
- Check environment is set to `us-east-1`
- Ensure you're connected to internet

### Slow First Startup
- Normal! It's loading and embedding all documents
- Pinecone index creation takes ~60 seconds
- This is one-time setup

### No Results from Query
- Check user has access to that document category
- Try asking simpler, more specific questions
- Check `loaded_documents.json` to see what's loaded

## 📝 Project Files Overview

| File | Purpose |
|------|---------|
| `app.py` | Main Flask application |
| `rag_pipeline.py` | Question answering logic |
| `vector_db.py` | Pinecone integration |
| `auth.py` | User authentication |
| `document_processor.py` | PDF handling |
| `config.py` | Configuration settings |
| `templates/login.html` | Login page |
| `templates/dashboard.html` | Main interface |
| `static/style.css` | Styling |
| `static/script.js` | Frontend logic |

## 🎯 Next Steps

1. **Customize Users**: Edit `auth.py` to add your own users
2. **Add Documents**: Drop PDFs in `RAGDocs/` and restart
3. **Modify Prompts**: Edit `rag_pipeline.py` to change response style
4. **Deploy**: Follow deployment guide for production setup
5. **Monitor**: Check logs for any issues

## 🚀 Going to Production

Before deploying:
- [ ] Change `SECRET_KEY` in `config.py`
- [ ] Set `DEBUG = False` in `config.py`
- [ ] Use production database for sessions (Redis)
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Set up logging
- [ ] Configure backups for `loaded_documents.json`
- [ ] Use environment variables for all secrets

## 📚 Learn More

- **LangChain**: https://docs.langchain.com/
- **Pinecone**: https://docs.pinecone.io/
- **OpenAI API**: https://platform.openai.com/docs/
- **Flask**: https://flask.palletsprojects.com/

## 💡 Tips & Tricks

### Faster Document Loading (Development)
Comment out document loading in first app startup for quicker testing:
```python
# In app.py, before init_vector_db():
# Skip loading, just connect to existing index
```

### Test New Documents
1. Add PDF to `RAGDocs/`
2. Delete `loaded_documents.json`
3. Restart app
4. New doc will be loaded automatically

### Clear All Data
```bash
# Delete these files to reset:
rm loaded_documents.json
rm users.json
# Then restart and everything reinitializes
```

### Debug Mode
Enable detailed logging:
```python
# In config.py
DEBUG = True
```

## ❓ FAQ

**Q: Can I use different LLM models?**  
A: Yes, edit `config.py` and change `OPENAI_MODEL` to any available OpenAI model.

**Q: How many documents can I add?**  
A: Depends on your Pinecone plan, but typically thousands. Check Pinecone pricing.

**Q: Can I run this without internet?**  
A: No, you need OpenAI and Pinecone APIs which require internet connection.

**Q: How do I update user passwords?**  
A: Edit `users.json` directly or use the `auth.py` functions to update hashes.

**Q: What if I go over API limits?**  
A: Set up rate limiting or implement caching in `rag_pipeline.py`.

---

**Ready to go!** 🎉 Start the app and begin asking questions!
