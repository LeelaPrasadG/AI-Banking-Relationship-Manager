@echo off
REM Bank RAG System - Windows Startup Script

echo.
echo ========================================
echo   Bank RAG System - Startup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

echo ✓ Python detected
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo ✓ Virtual environment created
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo ✓ Virtual environment activated
echo.

REM Check if requirements are installed
pip show flask >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo ✓ Dependencies installed
    echo.
) else (
    echo ✓ Dependencies already installed
    echo.
)

REM Check if .env file exists
if not exist ".env" (
    echo Warning: .env file not found!
    echo Please copy .env.example to .env and add your API keys:
    echo   OPENAI_API_KEY=your-key-here
    echo   PINECONE_API_KEY=your-key-here
    echo.
    echo After adding your keys, run this script again.
    pause
    exit /b 1
)

echo ✓ .env file found
echo.

REM Check if RAGDocs folder exists
if not exist "RAGDocs" (
    echo Error: RAGDocs folder not found
    echo Please create the RAGDocs folder and add PDF documents
    pause
    exit /b 1
)

echo ✓ RAGDocs folder found
echo.

REM Start the Flask application
echo Starting Bank RAG System...
echo.
python app.py

pause
