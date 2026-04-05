// ============================================
// Dashboard Interactivity
// ============================================

let currentSection = 'ask-section';

// Navigation
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function(e) {
        // Skip for logout link
        if (this.href && this.href.includes('logout')) {
            return;
        }
        
        e.preventDefault();
        
        // Get target section
        const href = this.getAttribute('href');
        if (!href || !href.startsWith('#')) {
            return;
        }
        
        const targetSection = href.substring(1);
        switchSection(targetSection);
    });
});

function switchSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Remove active class from all nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Show selected section
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
        currentSection = sectionId;
        
        // Set active nav link
        document.querySelector(`[href="#${sectionId}"]`).classList.add('active');
        
        // Load documents if documents section
        if (sectionId === 'documents-section') {
            loadDocuments();
        }
    }
}

// ============================================
// Ask Question Functionality
// ============================================

let isAsking = false;

document.getElementById('askBtn').addEventListener('click', askQuestion);

document.getElementById('questionInput').addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') {
        askQuestion();
    }
});

async function askQuestion() {
    if (isAsking) return;
    
    const question = document.getElementById('questionInput').value.trim();
    
    if (!question) {
        showError('Please enter a question');
        return;
    }
    
    isAsking = true;
    document.getElementById('askBtn').disabled = true;
    document.getElementById('loadingSpinner').style.display = 'flex';
    document.getElementById('answerContainer').style.display = 'none';
    document.getElementById('errorContainer').style.display = 'none';
    
    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayAnswer(data);
        } else {
            showError(data.message || 'Failed to process question');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred. Please try again.');
    } finally {
        isAsking = false;
        document.getElementById('askBtn').disabled = false;
        document.getElementById('loadingSpinner').style.display = 'none';
    }
}

function displayAnswer(data) {
    const container = document.getElementById('answerContainer');
    const errorContainer = document.getElementById('errorContainer');
    
    // Hide error if shown
    errorContainer.style.display = 'none';
    
    // Display answer
    if (data.primary_answer) {
        // Single role answer
        document.getElementById('answerText').textContent = data.primary_answer;
        
        const sourcesContainer = document.getElementById('sourcesContainer');
        if (data.sources && data.sources.length > 0) {
            displaySources(data.sources);
            sourcesContainer.style.display = 'block';
        } else {
            sourcesContainer.style.display = 'none';
        }
        
        document.getElementById('multiCategoryContainer').style.display = 'none';
    } else if (data.answers_by_category) {
        // Multiple role answers
        document.getElementById('answerText').textContent = 'Multiple categories provided answers below.';
        
        const categoryAnswersDiv = document.getElementById('categoryAnswers');
        categoryAnswersDiv.innerHTML = '';
        
        for (const [category, categoryData] of Object.entries(data.answers_by_category)) {
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'category-answer';
            
            const titleDiv = document.createElement('h5');
            titleDiv.textContent = category;
            categoryDiv.appendChild(titleDiv);
            
            const answerDiv = document.createElement('div');
            answerDiv.className = 'category-answer-text';
            answerDiv.textContent = categoryData.answer;
            categoryDiv.appendChild(answerDiv);
            
            if (categoryData.sources && categoryData.sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.style.marginTop = '8px';
                sourcesDiv.innerHTML = '<small style="color: var(--text-secondary)">Sources: ';
                categoryData.sources.forEach((source, idx) => {
                    if (idx > 0) sourcesDiv.innerHTML += ', ';
                    sourcesDiv.innerHTML += source.filename;
                });
                sourcesDiv.innerHTML += '</small>';
                categoryDiv.appendChild(sourcesDiv);
            }
            
            categoryAnswersDiv.appendChild(categoryDiv);
        }
        
        document.getElementById('multiCategoryContainer').style.display = 'block';
        document.getElementById('sourcesContainer').style.display = 'none';
    }
    
    container.style.display = 'block';
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displaySources(sources) {
    const sourcesList = document.getElementById('sourcesList');
    sourcesList.innerHTML = '';
    
    sources.forEach(source => {
        const sourceItem = document.createElement('div');
        sourceItem.className = 'source-item';
        sourceItem.innerHTML = `
            <div class="source-filename">📄 ${source.filename}</div>
            <div class="source-category">${source.category || 'Unknown Category'}</div>
        `;
        sourcesList.appendChild(sourceItem);
    });
}

function showError(message) {
    const errorContainer = document.getElementById('errorContainer');
    const errorText = document.getElementById('errorText');
    
    errorText.textContent = message;
    errorContainer.style.display = 'block';
}

// ============================================
// Load Documents
// ============================================

async function loadDocuments() {
    try {
        const response = await fetch('/api/documents');
        const data = await response.json();
        
        if (data.success) {
            displayDocuments(data.documents);
        } else {
            displayDocumentsError(data.message);
        }
    } catch (error) {
        console.error('Error loading documents:', error);
        displayDocumentsError('Failed to load documents');
    }
}

function displayDocuments(documents) {
    const container = document.getElementById('documentsContainer');
    container.innerHTML = '';
    
    const categoryNames = {
        'auto-loan': '🚗 Auto Loan',
        'credit-card': '💳 Credit Card',
        'banking': '🏦 Banking'
    };
    
    let hasDocuments = false;
    
    for (const [category, docs] of Object.entries(documents)) {
        if (docs && docs.length > 0) {
            hasDocuments = true;
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'document-category';
            
            const titleDiv = document.createElement('h3');
            titleDiv.textContent = categoryNames[category] || category;
            categoryDiv.appendChild(titleDiv);
            
            const listDiv = document.createElement('ul');
            listDiv.className = 'document-list';
            
            docs.forEach(doc => {
                const itemDiv = document.createElement('li');
                itemDiv.className = 'document-item';
                itemDiv.innerHTML = `
                    <span class="document-item-icon">📎</span>
                    <span class="document-item-name">${doc}</span>
                `;
                listDiv.appendChild(itemDiv);
            });
            
            categoryDiv.appendChild(listDiv);
            container.appendChild(categoryDiv);
        }
    }
    
    if (!hasDocuments) {
        container.innerHTML = '<div class="no-documents">No documents loaded yet.</div>';
    }
}

function displayDocumentsError(message) {
    const container = document.getElementById('documentsContainer');
    container.innerHTML = `<div class="error-container"><p id="errorText">${message}</p></div>`;
}

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized');
    console.log('User roles:', userRoles);
});
