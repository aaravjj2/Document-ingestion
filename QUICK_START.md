# Quick Start Guide - Document Ingestion Service

## ⚡ Fast Track Setup

### Option 1: Docker (Recommended)
```bash
# 1. Make script executable
chmod +x start.sh

# 2. Start everything with Docker
./start.sh --docker

# 3. Access services
# API:       http://localhost:8000/docs
# Dashboard: http://localhost:8501
# Flower:    http://localhost:5555
```

### Option 2: Local Development
```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Start PostgreSQL and Redis
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=document_ingestion postgres:14-alpine
docker run -d -p 6379:6379 redis:7-alpine

# 3. Run migrations
alembic upgrade head

# 4. Start services (in separate terminals)
make run-api        # Terminal 1
make run-worker     # Terminal 2  
make run-dashboard  # Terminal 3
```

## 🧪 Running Tests

### Quick E2E Test
```bash
python3 test_e2e.py
```

### Unit Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific tests
pytest tests/test_preprocessing.py -v
pytest tests/test_classification.py -v
```

### Stress Tests
```bash
pytest tests/stress/test_augraphy.py -v
pytest tests/stress/test_accuracy.py -v
```

## 📤 Upload a Document

### Using cURL
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@/path/to/document.pdf"
```

### Using Python
```python
import requests

with open('document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/api/v1/documents/upload', files=files)
    print(response.json())
```

### Using the Dashboard
1. Open http://localhost:8501
2. Go to "Upload Document" page
3. Drag & drop or browse for file
4. Click upload

## 🔍 Search Documents

### API
```bash
# Text search
curl "http://localhost:8000/api/v1/search?q=invoice"

# Filter by date range
curl "http://localhost:8000/api/v1/search?q=invoice&start_date=2024-01-01&end_date=2024-12-31"

# Filter by document type
curl "http://localhost:8000/api/v1/search?document_type=invoice"
```

### Dashboard
1. Go to "Search Documents" page
2. Enter search query
3. Apply filters as needed
4. View results

## 📊 Check Status

### Health Check
```bash
curl http://localhost:8000/api/v1/dashboard/health
```

### Metrics
```bash
curl http://localhost:8000/api/v1/dashboard/metrics
```

### Processing Queue
```bash
curl http://localhost:8000/api/v1/dashboard/queue
```

## 🔧 Common Tasks

### Reprocess a Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents/{document_id}/reprocess"
```

### Get Document Details
```bash
curl "http://localhost:8000/api/v1/documents/{document_id}"
```

### Update Review Status
```bash
curl -X PUT "http://localhost:8000/api/v1/documents/{document_id}/review" \
  -H "Content-Type: application/json" \
  -d '{"validated": true, "validated_by": "admin"}'
```

## 🐛 Troubleshooting

### Check Logs
```bash
# Docker
docker-compose logs -f api
docker-compose logs -f worker

# Local
# Check terminal outputs
```

### Reset Database
```bash
# Docker
docker-compose down -v
docker-compose up -d

# Local
alembic downgrade base
alembic upgrade head
```

### Clear Redis Cache
```bash
docker exec -it doc_ingestion_redis redis-cli FLUSHALL
```

### Test Individual Components
```bash
# Test preprocessing
python3 -c "from src.services.preprocessing.image_processor import ImagePreprocessor; print('✓ OK')"

# Test OCR
python3 -c "from src.services.ocr.ocr_service import OCRService; print('✓ OK')"

# Test classification
python3 -c "from src.services.classification.classifier import DocumentClassifier; print('✓ OK')"
```

## 📝 Environment Variables

Key variables to configure in `.env`:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/document_ingestion

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=50

# OCR
OCR_CONFIDENCE_THRESHOLD=0.6
OCR_LANGUAGE=en

# LLM (for extraction)
OPENAI_API_KEY=your-key-here
LLM_MODEL=gpt-4o-mini

# Or use local LLM
USE_LOCAL_LLM=true
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3
```

## 📚 API Documentation

Once the API is running, visit:
- **Interactive Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🎯 Next Steps

1. **Configure Environment:** Update `.env` with production values
2. **Set API Keys:** Add your OpenAI API key for LLM extraction
3. **Scale Workers:** Increase Celery worker concurrency for production
4. **Add Monitoring:** Integrate with your monitoring stack
5. **Tune OCR:** Adjust confidence thresholds based on your documents
6. **Customize Classification:** Add document types specific to your use case

## 💡 Tips

- **Batch Processing:** Use the Celery worker to process multiple documents in parallel
- **Queue Priority:** Higher priority documents are processed first
- **Confidence Threshold:** Documents below confidence threshold are flagged for review
- **File Types:** Supports PDF, PNG, JPG, TIFF formats
- **Max File Size:** Configurable, default 50MB

## 🆘 Need Help?

- Check [TEST_RESULTS.md](TEST_RESULTS.md) for detailed test results
- See [README.md](README.md) for architecture overview
- Review API docs at `/docs` endpoint
- Check logs for error messages
