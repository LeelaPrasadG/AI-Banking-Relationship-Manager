# Testing Guide - Bank RAG System

## 🧪 Unit Tests

Create `tests/` directory with test files.

### Test Structure
```
tests/
├── __init__.py
├── test_auth.py
├── test_document_processor.py
├── test_rag_pipeline.py
├── test_vector_db.py
└── test_routes.py
```

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-cov pytest-flask

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test
pytest tests/test_auth.py::test_authenticate_user -v
```

## 📋 Manual Testing Checklist

### Authentication Tests
- [ ] Login with valid credentials (loanagent/pwd123)
- [ ] Login with invalid username
- [ ] Login with invalid password
- [ ] Logout and verify session cleared
- [ ] Access dashboard without login redirects to login
- [ ] Session persists across page reloads

### Document Loading Tests
- [ ] All documents loaded on first run
- [ ] Documents not reloaded on subsequent starts
- [ ] New documents auto-detected and loaded
- [ ] Document metadata saved correctly
- [ ] Loaded documents list displays correctly

### Query Tests
- [ ] Ask question as loanagent returns auto loan answers
- [ ] Ask question as cardagent returns credit card answers
- [ ] Ask question as bankagent returns banking answers
- [ ] cardbankagent gets both categories
- [ ] Cross-category question denied appropriately
- [ ] Empty question shows error
- [ ] Long question processes correctly

### Role-Based Access Tests
- [ ] loanagent cannot access banking documents
- [ ] cardagent cannot access auto loan documents
- [ ] bankagent cannot access credit card documents
- [ ] cardbankagent can access both credit card AND banking
- [ ] cardbankagent cannot access auto loan
- [ ] Appropriate error messages shown

### UI/UX Tests
- [ ] Login page displays correctly
- [ ] Dashboard loads with user info
- [ ] Ask section functional
- [ ] Documents section shows correct categories
- [ ] Responsive on mobile devices
- [ ] Navigation between sections works
- [ ] Loading spinner displays during queries
- [ ] Error messages clear and helpful

### Performance Tests
- [ ] Response time < 5 seconds for typical query
- [ ] Document loading completes in reasonable time
- [ ] No memory leaks in long sessions
- [ ] Handles concurrent users
- [ ] Proper error handling under load

## 🔍 Integration Tests

### API Endpoint Tests
```bash
# Test login
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"loanagent","password":"pwd123"}'

# Test ask question (requires valid session)
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the auto loan terms?"}' \
  --cookie "session=..."

# Test documents endpoint
curl http://localhost:5000/api/documents \
  --cookie "session=..."

# Test stats endpoint
curl http://localhost:5000/api/stats \
  --cookie "session=..."
```

## 🔐 Security Testing

### Injection Tests
- [ ] Test SQL injection in login (if using database)
- [ ] Test prompt injection in questions
- [ ] Test XSS in form inputs
- [ ] Test CSRF protection

### Authentication Tests
- [ ] Test session fixation
- [ ] Test session hijacking resistance
- [ ] Test token expiration
- [ ] Test privilege escalation

### Data Privacy Tests
- [ ] Verify API keys not exposed in errors
- [ ] Check no sensitive data logged
- [ ] Verify HTTPS in production
- [ ] Test secure cookie attributes

## 📊 Load Testing

### Using Apache Bench
```bash
# Install Apache Bench (on Windows, via Apache or alternatives)
# Simulate 100 concurrent users with 1000 requests
ab -c 100 -n 1000 http://localhost:5000/

# Test API endpoint
ab -c 50 -n 500 -p data.json -T application/json http://localhost:5000/api/ask
```

### Using wrk
```bash
# Install wrk: https://github.com/wg/wrk

# Simple load test
wrk -t4 -c100 -d30s http://localhost:5000/

# With script for POST requests
wrk -t4 -c100 -d30s -s script.lua http://localhost:5000/api/ask
```

### Using Locust
```bash
# Install
pip install locust

# Create locustfile.py
# Run test
locust -f locustfile.py --host=http://localhost:5000
```

## 🧩 Sample Test Cases

### test_auth.py
```python
import pytest
from auth import authenticate_user, get_user_roles

def test_authenticate_valid_user():
    user, message = authenticate_user('loanagent', 'pwd123')
    assert user is not None
    assert user['username'] == 'loanagent'
    assert 'auto-loan' in user['roles']

def test_authenticate_invalid_password():
    user, message = authenticate_user('loanagent', 'wrong')
    assert user is None
    assert 'Invalid password' in message

def test_get_user_roles():
    roles = get_user_roles('cardagent')
    assert 'credit-card' in roles
    assert len(roles) == 1
```

### test_document_processor.py
```python
import os
from document_processor import (
    get_document_category,
    is_document_loaded,
    extract_text_from_pdf
)

def test_document_categorization():
    assert get_document_category('auto-loan-terms.pdf') == 'auto-loan'
    assert get_document_category('credit-card-terms.pdf') == 'credit-card'
    assert get_document_category('banking-terms.pdf') == 'banking'

def test_extract_text_from_pdf():
    pdf_path = 'RAGDocs/auto-loan-terms-and-conditions.pdf'
    text = extract_text_from_pdf(pdf_path)
    assert text is not None
    assert len(text) > 0
```

## 🔄 Continuous Testing

### Pre-commit Hook
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
echo "Running tests before commit..."
pytest --cov=. || exit 1
echo "Tests passed! Proceeding with commit."
```

### Pre-push Hook
Create `.git/hooks/pre-push`:
```bash
#!/bin/bash
echo "Running all tests before push..."
pytest --cov=. -q || exit 1
```

## 📈 Test Coverage

### Generate Report
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Coverage Goals
- Aim for >80% code coverage
- Focus on critical paths
- Test error scenarios
- Test edge cases

## 🐛 Debugging Failed Tests

### Enable Debug Output
```bash
# Verbose output
pytest -v

# Show print statements
pytest -s

# Drop to debugger on failure
pytest --pdb

# Exit on first failure
pytest -x
```

### Debug in Code
```python
import pdb; pdb.set_trace()  # Add this line and use "c" to continue

# Or use breakpoint() in Python 3.7+
breakpoint()
```

## 📝 Test Documentation

### Document Your Tests
```python
def test_loanagent_cannot_access_banking():
    """
    Test that loanagent user cannot access banking documents.
    This ensures RBAC is properly enforced at the query level.
    
    Given: User with 'auto-loan' role
    When: User asks a banking-related question
    Then: System returns "Role not supported" message
    """
    # Test code here
    pass
```

## 🎯 Testing Strategies

### Boundary Testing
- Empty strings
- Very long inputs
- Special characters
- Null values

### Scenario Testing
- Happy path
- Error conditions
- Edge cases
- User workflows

### Performance Testing
- Response time
- Memory usage
- Database query efficiency
- Concurrent user handling

---

**Testing is not optional - it's essential for reliability!**
