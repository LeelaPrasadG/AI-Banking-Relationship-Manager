# Setup Instructions - Complete Step-by-Step Guide

## 🎯 Final Setup Requirements

Before running the application, you need to complete these setup steps:

### Step 1: Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in with your OpenAI account
3. Click "Create new secret key"
4. Copy the key (⚠️ **Save it immediately** - it only shows once)
5. Keep it safe - this is your API credential

**Cost**: Pay-as-you-go billing. GPT-4 is more expensive than GPT-3.5

### Step 2: Get Pinecone API Key

1. Go to https://www.pinecone.io
2. Create a free account
3. Create a new organization/project
4. Go to "API Keys" section in the sidebar
5. Copy your API Key
6. Note your environment (default is often `us-east-1`)

**Cost**: Free tier available, pay-as-you-grow

### Step 3: Create .env File

1. Open `.env.example` (in project root)
2. Copy all the content
3. Create a new file called `.env` in the same directory
4. Paste the content
5. Replace the placeholder values:
   ```
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
   PINECONE_API_KEY=pcak_xxxxxxxxxxxxxxxxxxxxx
   PINECONE_ENVIRONMENT=us-east-1
   ```
6. Save the `.env` file

⚠️ **IMPORTANT**: Never commit `.env` to git. It's already in .gitignore

### Step 4: Install Python Dependencies

**Option A: Using Command Prompt/PowerShell**
```bash
# Navigate to project
cd d:\AI\Git\RAG_RBAC_LangChain

# Install packages
pip install -r requirements.txt
```

**Option B: Using Virtual Environment (Recommended)**
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### Step 5: Run the Application

**Option A: Direct Python**
```bash
python app.py
```

**Option B: Windows Batch Script**
```bash
run.bat
```

**Option C: PowerShell Script**
```powershell
run.ps1
```

The application will:
1. Initialize user accounts
2. Create Pinecone index (takes ~60 seconds first time)
3. Load all PDF documents from RAGDocs/
4. Start Flask server on http://localhost:5000

### Step 6: Open in Browser

```
http://localhost:5000
```

## 🧪 Test the System

### Login Test
1. Username: `loanagent`
2. Password: `pwd123`

### Ask a Question
Try: "What are the terms and conditions for auto loans?"

Should return an answer based on the PDF content.

## ✅ Verification Checklist

- [ ] Python 3.8+ installed (`python --version`)
- [ ] Project folder at `d:\AI\Git\RAG_RBAC_LangChain`
- [ ] `.env` file created with API keys
- [ ] All PDFs in `RAGDocs/` folder (6 files total)
- [ ] Dependencies installed (`pip list` shows langchain, pinecone, flask, etc.)
- [ ] No errors in app startup (check console output)
- [ ] Can login with test credentials
- [ ] Can ask a question and get an answer
- [ ] Documents appear in "Documents" section

## 🆘 Troubleshooting

### "No module named 'flask'" or similar
```bash
pip install -r requirements.txt
```

### "OPENAI_API_KEY not set"
- Check `.env` file exists (not `.env.example`)
- Check OPENAI_API_KEY value is correct
- Restart the application

### "Cannot connect to Pinecone"
- Verify PINECONE_API_KEY is correct
- Check PINECONE_ENVIRONMENT is correct
- Ensure you're connected to internet
- Check Pinecone dashboard shows your API key

### Application crashes on startup
- Check Python version (need 3.8+)
- Run `pip install -r requirements.txt` again
- Delete `.env` and recreate it carefully
- Check RAGDocs folder exists with PDFs

### Login fails
- Verify username is exactly `loanagent` (case-sensitive)
- Verify password is exactly `pwd123`
- Check no spaces in credentials

### No answers returned from queries
- Check PDFs are loading (look at console output)
- Check `loaded_documents.json` exists and has entries
- Try simpler, more specific questions
- Check user has correct role for that document category

## 📱 Access the Application

### Local Access
```
http://localhost:5000
```

### From Another Computer (Same Network)
```
http://<your-computer-ip>:5000
```

To find your IP:
```
ipconfig
# Look for IPv4 Address (e.g., 192.168.x.x)
```

## 🔐 Important Security Notes

### Before Production Deployment:
- [ ] Change `SECRET_KEY` in `config.py`
- [ ] Change all user passwords
- [ ] Use HTTPS/SSL
- [ ] Move API keys to secure vault
- [ ] Enable rate limiting
- [ ] Setup proper logging

### For Development:
If you're just testing, the current setup is fine.

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Complete feature documentation |
| `QUICKSTART.md` | 10-minute setup guide |
| `PROJECT_SUMMARY.md` | Project overview and structure |
| `DEPLOYMENT.md` | Production deployment guide |
| `TESTING.md` | Testing and QA guide |
| `SETUP.md` | This file - step-by-step setup |

## 🎓 Next Steps After Setup

1. **Explore the Interface**: Try asking different questions
2. **Customize Users**: Edit `users.json` to add your own users
3. **Add Documents**: Put new PDFs in `RAGDocs/` folder
4. **Modify Prompts**: Edit `rag_pipeline.py` to change response style
5. **Deploy**: Follow `DEPLOYMENT.md` for production

## 📞 Getting Help

1. Check `QUICKSTART.md` for common issues
2. Review console output for error messages
3. Verify all API keys are correct
4. Check internet connection
5. Try restarting the application
6. Review the error details in browser console (F12 in browser)

## ✨ Success Indicators

You'll know it's working when:
- ✅ Application starts without errors
- ✅ Can see login page at http://localhost:5000
- ✅ Can login with test credentials
- ✅ Can see dashboard with user info
- ✅ Can ask a question and get an answer
- ✅ Can see "Documents" section with loaded files
- ✅ Console shows "Loaded Documents Summary"

---

**You're all set! Time to explore and build! 🚀**
