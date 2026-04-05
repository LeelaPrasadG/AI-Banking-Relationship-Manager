# Bank RAG System - Windows PowerShell Startup Script

Write-Host ""
Write-Host "========================================"
Write-Host "  Bank RAG System - Startup"
Write-Host "========================================"
Write-Host ""

# Check if Python is installed
try {
    python --version | Out-Null
    Write-Host "✓ Python detected"
} catch {
    Write-Host "Error: Python is not installed or not in PATH"
    Write-Host "Please install Python 3.8+ from https://www.python.org"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
    Write-Host "✓ Virtual environment created"
    Write-Host ""
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated"
Write-Host ""

# Check if requirements are installed
try {
    pip show flask | Out-Null
    Write-Host "✓ Dependencies already installed"
} catch {
    Write-Host "Installing dependencies..."
    pip install -r requirements.txt
    Write-Host "✓ Dependencies installed"
}

Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env file not found!"
    Write-Host "Please copy .env.example to .env and add your API keys:"
    Write-Host "  OPENAI_API_KEY=your-key-here"
    Write-Host "  PINECONE_API_KEY=your-key-here"
    Write-Host ""
    Write-Host "After adding your keys, run this script again."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ .env file found"
Write-Host ""

# Check if RAGDocs folder exists
if (-not (Test-Path "RAGDocs")) {
    Write-Host "Error: RAGDocs folder not found"
    Write-Host "Please create the RAGDocs folder and add PDF documents"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ RAGDocs folder found"
Write-Host ""

# Start the Flask application
Write-Host "Starting Bank RAG System..."
Write-Host ""
python app.py

Read-Host "Press Enter to exit"
