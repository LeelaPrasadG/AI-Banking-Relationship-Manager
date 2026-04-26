from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import json
import logging
from datetime import datetime
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config import SECRET_KEY, FLASK_ENV, OPENAI_API_KEY, LOG_LEVEL

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)
from auth import authenticate_user, get_user_roles, init_users
from auth import user_has_role
from document_processor import (
    get_unloaded_documents, 
    add_document_to_metadata, 
    get_all_documents,
    extract_text_from_pdf,
    load_documents_metadata,
    get_document_category
)
from vector_db import VectorDBManager
from rag_pipeline import RAGPipeline, DocumentProcessor

# Initialize Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app)

# Global instances
vector_db = None
rag_pipeline = None

def init_vector_db():
    """Initialize vector database and load documents"""
    global vector_db, rag_pipeline
    
    logger.info("[INIT] starting vector database initialisation")
    print("\n" + "="*60)
    print("Initializing Vector Database")
    print("="*60)
    
    try:
        vector_db = VectorDBManager()
        rag_pipeline = RAGPipeline()
        logger.info("[INIT] VectorDBManager and RAGPipeline created")
        
        # Load unloaded documents
        unloaded_docs = get_unloaded_documents()
        
        if unloaded_docs:
            print(f"\nFound {len(unloaded_docs)} new documents to load:")
            all_chunks = []
            doc_metadata_map = {}
            
            # Extract all chunks from all documents
            for doc in unloaded_docs:
                print(f"\n  Processing: {doc['filename']} ({doc['category']})")
                try:
                    text = extract_text_from_pdf(doc['path'])
                    if text:
                        # Split text into chunks
                        chunks = DocumentProcessor.split_into_chunks(text)
                        print(f"    - Extracted text: {len(text)} characters, {len(chunks)} chunks")
                        logger.info(
                            "[INIT] '%s' category='%s' chars=%d chunks=%d",
                            doc['filename'], doc['category'], len(text), len(chunks)
                        )
                        
                        # Prepare chunks for batch upload
                        for idx, chunk in enumerate(chunks):
                            metadata = DocumentProcessor.create_metadata(
                                doc['filename'],
                                doc['category'],
                                idx,
                                len(chunks)
                            )
                            all_chunks.append({
                                'text': chunk,
                                'metadata': metadata
                            })
                        
                        # Store metadata for later
                        content_hash = hashlib.md5(text.encode()).hexdigest()
                        doc_metadata_map[doc['filename']] = {
                            'category': doc['category'],
                            'hash': content_hash
                        }
                except Exception as e:
                    print(f"    ✗ Error extracting text: {str(e)}")
                    logger.error("[INIT] error extracting '%s': %s", doc['filename'], e)
            
            # Batch add all chunks to Pinecone
            if all_chunks:
                success = vector_db.add_documents_batch(all_chunks)
                if success:
                    # Only mark documents as loaded if upload succeeded
                    for filename, info in doc_metadata_map.items():
                        add_document_to_metadata(filename, info['category'], info['hash'])
                    print(f"\n✓ All {len(all_chunks)} chunks successfully added to vector database")
                    logger.info("[INIT] %d chunks uploaded to Pinecone", len(all_chunks))
                else:
                    print(f"\n✗ Failed to add document chunks to Pinecone")
                    logger.error("[INIT] batch upload to Pinecone failed")
            else:
                print("\nNo chunks extracted from documents.")
        else:
            print("\nNo new documents to load.")
        
        # Display loaded documents
        print("\n" + "-"*60)
        print("Loaded Documents Summary:")
        print("-"*60)
        loaded_docs = get_all_documents()
        for category, docs in loaded_docs.items():
            if docs:
                print(f"\n{category.upper().replace('-', ' ')}:")
                for doc in docs:
                    print(f"  - {doc}")
        
        print("\n" + "="*60 + "\n")
        logger.info("[INIT] vector database initialisation complete")
        return True
    except Exception as e:
        print(f"Error initializing vector database: {str(e)}")
        logger.error("[INIT] vector database initialisation failed: %s", e, exc_info=True)
        return False

def login_required(f):
    """Decorator to check if user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# Routes
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Home page - redirect to dashboard if logged in"""
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
        
        user, message = authenticate_user(username, password)
        
        if user:
            session['user'] = user
            session['username'] = username
            logger.info("[LOGIN] SUCCESS user='%s'", username)
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'redirect': url_for('dashboard')
            })
        else:
            logger.warning("[LOGIN] FAILED user='%s' reason='%s'", username, message)
            return jsonify({
                'success': False,
                'message': message
            }), 401
    
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Dashboard page - user can ask questions"""
    username = session.get('username')
    user = session.get('user', {})
    roles = user.get('roles', [])
    
    # Convert role codes to readable names
    role_names = {
        'auto-loan': 'Auto Loan',
        'credit-card': 'Credit Card',
        'banking': 'Banking'
    }
    
    display_roles = [role_names.get(r, r) for r in roles]
    
    return render_template('dashboard.html', 
                         username=username,
                         roles=display_roles,
                         role_codes=roles)

@app.route('/api/ask', methods=['POST'])
@login_required
def ask_question():
    """API endpoint to process questions"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'success': False,
                'message': 'Question cannot be empty'
            }), 400
        
        username = session.get('username')
        user = session.get('user', {})
        user_roles = user.get('roles', [])
        logger.info(
            "[API:ASK] user='%s' roles=%s question='%.80s%s'",
            username, user_roles, question, '...' if len(question) > 80 else ''
        )
        
        if not user_roles:
            logger.warning("[API:ASK] user='%s' has no assigned roles", username)
            return jsonify({
                'success': False,
                'message': 'User has no assigned roles'
            }), 403
        
        # Query the RAG pipeline
        result = rag_pipeline.query(question, username, user_roles)
        
        logger.info(
            "[API:ASK] response for user='%s' success=%s guardrail_blocked=%s",
            username, result.get('success'), result.get('guardrail_blocked', False)
        )
        return jsonify(result)
    
    except Exception as e:
        logger.error("[API:ASK] unhandled error for user='%s': %s", session.get('username'), e, exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error processing question: {str(e)}'
        }), 500

@app.route('/api/documents', methods=['GET'])
@login_required
def get_documents():
    """API endpoint to get loaded documents"""
    try:
        documents = get_all_documents()
        metadata = load_documents_metadata()
        
        return jsonify({
            'success': True,
            'documents': documents,
            'total_documents': len(metadata.get('documents', [])),
            'last_updated': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """API endpoint to get vector database statistics"""
    try:
        if vector_db:
            stats = vector_db.index_stats()
            return jsonify({
                'success': True,
                'stats': stats
            })
        return jsonify({
            'success': False,
            'message': 'Vector DB not initialized'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """User logout"""
    username = session.get('username')
    session.clear()
    logger.info("[LOGOUT] user='%s'", username)
    return redirect(url_for('login'))

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'success': False, 'message': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

# ============================================================================
# Initialization
# ============================================================================

@app.before_request
def before_request():
    """Run before each request"""
    session.permanent = True

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Bank RAG System - Initialization")
    print("="*60 + "\n")
    
    # Verify API keys are loaded
    if not OPENAI_API_KEY:
        print("❌ ERROR: OPENAI_API_KEY not found in .env file!")
        print("Please add your OpenAI API key to the .env file")
        exit(1)
    
    print("✓ OpenAI API Key loaded from .env")
    print(f"✓ Using Model: gpt-5.4")
    print(f"✓ API Key: {OPENAI_API_KEY[:20]}...{OPENAI_API_KEY[-10:]}\n")
    
    # Initialize users
    init_users()
    print("✓ Users initialized\n")
    
    # Initialize vector database
    if init_vector_db():
        print("✓ Vector database initialized\n")
        
        # Start Flask app
        print("Starting Flask application...")
        print("Open http://localhost:5000 in your browser")
        print("\nTest credentials:")
        print("  loanagent / pwd123 (Auto Loan)")
        print("  cardagent / pwd123 (Credit Card)")
        print("  bankagent / pwd123 (Banking)")
        print("  cardbankagent / pwd123 (Credit Card + Banking)")
        print("\n" + "="*60 + "\n")
        
        app.run(debug=True, port=5000)
    else:
        print("✗ Failed to initialize vector database")
