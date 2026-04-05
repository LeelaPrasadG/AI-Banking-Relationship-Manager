import os
import json
from pathlib import Path
from PyPDF2 import PdfReader
from config import RAG_DOCS_PATH, DOCUMENT_CATEGORIES, LOADED_DOCUMENTS_FILE

def get_document_category(filename):
    """Determine document category based on filename"""
    filename_lower = filename.lower()
    
    for category, keywords in DOCUMENT_CATEGORIES.items():
        for keyword in keywords:
            if keyword in filename_lower:
                return category
    
    return None

def load_documents_metadata():
    """Load metadata of already processed documents"""
    if os.path.exists(LOADED_DOCUMENTS_FILE):
        with open(LOADED_DOCUMENTS_FILE, 'r') as f:
            return json.load(f)
    return {'documents': []}

def save_documents_metadata(metadata):
    """Save metadata of processed documents"""
    with open(LOADED_DOCUMENTS_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def is_document_loaded(filename):
    """Check if a document has already been loaded"""
    metadata = load_documents_metadata()
    for doc in metadata['documents']:
        if doc['filename'] == filename:
            return True
    return False

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from {file_path}: {str(e)}")
        return None

def get_unloaded_documents():
    """Get list of documents that haven't been loaded to vector DB yet"""
    unloaded_docs = []
    
    if not os.path.exists(RAG_DOCS_PATH):
        print(f"RAGDocs path not found: {RAG_DOCS_PATH}")
        return unloaded_docs
    
    for filename in os.listdir(RAG_DOCS_PATH):
        if filename.endswith('.pdf'):
            if not is_document_loaded(filename):
                category = get_document_category(filename)
                if category:
                    file_path = os.path.join(RAG_DOCS_PATH, filename)
                    unloaded_docs.append({
                        'filename': filename,
                        'path': file_path,
                        'category': category
                    })
    
    return unloaded_docs

def add_document_to_metadata(filename, category, content_hash):
    """Add a document to the loaded documents metadata"""
    metadata = load_documents_metadata()
    
    doc_entry = {
        'filename': filename,
        'category': category,
        'loaded_at': json.dumps(__import__('datetime').datetime.now().isoformat()),
        'hash': content_hash
    }
    
    metadata['documents'].append(doc_entry)
    save_documents_metadata(metadata)

def get_all_documents():
    """Get all documents organized by category"""
    metadata = load_documents_metadata()
    documents_by_category = {
        'auto-loan': [],
        'credit-card': [],
        'banking': []
    }
    
    for doc in metadata['documents']:
        category = doc.get('category')
        if category in documents_by_category:
            documents_by_category[category].append(doc['filename'])
    
    return documents_by_category

def get_category_for_document(filename):
    """Get the category of a loaded document"""
    metadata = load_documents_metadata()
    for doc in metadata['documents']:
        if doc['filename'] == filename:
            return doc.get('category')
    return None
