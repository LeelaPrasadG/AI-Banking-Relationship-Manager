# Production Deployment Guide - Bank RAG System

## 🚀 Deployment Checklist

Before deploying to production, ensure the following:

### Security
- [ ] Change `SECRET_KEY` in `config.py` to a secure random string
- [ ] Set `DEBUG = False` in `config.py`
- [ ] Store all API keys in environment variables, not in code
- [ ] Enable HTTPS/SSL certificates
- [ ] Implement CSRF protection
- [ ] Add rate limiting to prevent abuse
- [ ] Implement request validation and sanitization
- [ ] Hash user passwords with bcrypt (not werkzeug only)
- [ ] Use secure session cookies (HttpOnly, SecureOnly, SameSite)

### Database & Storage
- [ ] Use production-grade database for user data (PostgreSQL, MySQL)
- [ ] Use Redis or similar for session management
- [ ] Implement database backups
- [ ] Store `loaded_documents.json` in persistent storage
- [ ] Setup database connection pooling
- [ ] Encrypt sensitive data at rest

### Monitoring & Logging
- [ ] Setup centralized logging (ELK, Splunk, CloudWatch)
- [ ] Enable error tracking (Sentry, New Relic)
- [ ] Setup health check endpoints
- [ ] Monitor API usage and costs
- [ ] Setup alerts for errors and performance issues
- [ ] Log all authentication attempts

### Performance
- [ ] Enable caching (Redis, Memcached)
- [ ] Use CDN for static files
- [ ] Implement query caching
- [ ] Setup load balancing
- [ ] Optimize PDF text extraction
- [ ] Use async workers (Celery, APScheduler)
- [ ] Monitor and optimize API response times

### API Management
- [ ] Setup rate limiting per user
- [ ] Implement API key management
- [ ] Version your API endpoints
- [ ] Setup API documentation
- [ ] Monitor OpenAI and Pinecone usage
- [ ] Setup usage quotas
- [ ] Implement graceful degradation

### Infrastructure
- [ ] Use containerized deployment (Docker)
- [ ] Setup CI/CD pipeline
- [ ] Test on production-like environment
- [ ] Implement automated backups
- [ ] Setup disaster recovery plan
- [ ] Use infrastructure as code (Terraform, CloudFormation)
- [ ] Setup VPC and network security

### Compliance
- [ ] Ensure GDPR compliance if EU users
- [ ] Implement data retention policies
- [ ] Setup audit logging
- [ ] Privacy policy and terms of service
- [ ] Compliance with financial regulations
- [ ] Data encryption in transit and at rest

## 🐳 Docker Deployment

### Dockerfile Example
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000')"

# Start application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "app:app"]
```

### Build and Run
```bash
# Build image
docker build -t bank-rag:latest .

# Run container
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e PINECONE_API_KEY=$PINECONE_API_KEY \
  -v loaded_documents.json:/app/loaded_documents.json \
  bank-rag:latest
```

## 🔧 Production Configuration

### config.py Modifications
```python
import os

# Environment
FLASK_ENV = os.getenv('FLASK_ENV', 'production')
DEBUG = False
SECRET_KEY = os.getenv('SECRET_KEY')  # Must be set!

# Security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Database
DATABASE_URL = os.getenv('DATABASE_URL')

# Caching
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = os.getenv('REDIS_URL')

# Rate limiting
RATELIMIT_ENABLED = True
RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL')

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = '/var/log/bank-rag/app.log'
```

## 📦 Systemd Service (Linux)

### /etc/systemd/system/bank-rag.service
```ini
[Unit]
Description=Bank RAG System
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/bank-rag
Environment="PATH=/opt/bank-rag/venv/bin"
ExecStart=/opt/bank-rag/venv/bin/gunicorn \
  --bind 127.0.0.1:5000 \
  --workers 4 \
  --worker-class sync \
  --timeout 120 \
  app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start
```bash
sudo systemctl enable bank-rag
sudo systemctl start bank-rag
sudo systemctl status bank-rag
```

## ☁️ Cloud Deployment Options

### AWS Elastic Beanstalk
```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.9 bank-rag

# Create environment
eb create production

# Deploy
eb deploy
```

### Heroku
```bash
# Login
heroku login

# Create app
heroku create bank-rag

# Set environment variables
heroku config:set OPENAI_API_KEY=$OPENAI_API_KEY
heroku config:set PINECONE_API_KEY=$PINECONE_API_KEY

# Deploy
git push heroku main
```

### Google Cloud Run
```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT-ID/bank-rag

# Deploy
gcloud run deploy bank-rag \
  --image gcr.io/PROJECT-ID/bank-rag \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY,PINECONE_API_KEY=$PINECONE_API_KEY
```

## 🔄 CI/CD Pipeline Example (GitHub Actions)

### .github/workflows/deploy.yml
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ --cov=.

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to production
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
          DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}
        run: |
          mkdir ~/.ssh
          echo "$DEPLOY_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh -i ~/.ssh/deploy_key $DEPLOY_HOST 'cd /opt/bank-rag && git pull && ./deploy.sh'
```

## 📊 Monitoring & Metrics

### Key Metrics to Track
- API response time
- Error rate and error types
- Vector database query time
- OpenAI API usage and costs
- User authentication success/failure rate
- Document loading time
- Cache hit rate

### Recommended Tools
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or Splunk
- **Error Tracking**: Sentry
- **APM**: New Relic or DataDog
- **Uptime**: Uptime Robot

## 🔒 Security Hardening

### WAF Rules
- Enable AWS WAF or similar
- Block SQL injection attempts
- Rate limit per IP
- CORS policy restrictions

### DDoS Protection
- Use Cloudflare or similar
- Enable rate limiting
- Implement request throttling

### API Security
- Implement API keys
- Use OAuth for sensitive operations
- Validate all inputs
- Implement output encoding

## 📈 Scaling Strategy

### Horizontal Scaling
1. Load balancer (AWS ELB, nginx)
2. Multiple Flask instances
3. Shared Redis for sessions
4. Database replication

### Vertical Scaling
1. Increase worker processes
2. Use async workers (gevent)
3. Optimize database queries
4. Implement caching layers

## 🆘 Rollback Procedure

```bash
# Check deployment history
git log --oneline

# Rollback to previous version
git revert HEAD

# Or reset to specific commit
git reset --hard commit-hash

# Redeploy
./deploy.sh
```

## 📞 Support & Maintenance

### Regular Maintenance Tasks
- Update dependencies monthly
- Review and rotate API keys quarterly
- Audit access logs
- Test backup restoration
- Security patching
- Performance optimization

### Incident Response Plan
1. Detect issue via monitoring
2. Alert on-call engineer
3. Isolate affected systems
4. Implement fix or rollback
5. Test and verify
6. Document and post-mortem

---

**Remember**: Security and reliability should be your top priorities in production!
