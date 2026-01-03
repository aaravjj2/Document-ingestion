# Intelligent Document Ingestion Service

A production-ready document processing pipeline featuring OCR, intelligent classification, and structured data extraction.

## 🚀 Features

- **Multi-format Support**: PDF, PNG, JPG, TIFF
- **Advanced OCR**: PaddleOCR with handwriting support
- **Intelligent Classification**: Auto-detect document types (Invoice, Medical, etc.)
- **LLM Extraction**: Extract structured fields using GPT-4 or local Llama
- **Full-Text Search**: PostgreSQL-powered text search
- **Real-time Dashboard**: Monitor processing status and review flagged documents
- **Async Processing**: Celery + Redis for scalable background tasks

## 📁 Project Structure

```
document-ingestion/
├── src/
│   ├── api/                 # FastAPI endpoints
│   ├── core/                # Configuration and dependencies
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   │   ├── preprocessing/   # Image cleaning pipeline
│   │   ├── ocr/             # OCR integration
│   │   ├── classification/  # Document classification
│   │   └── extraction/      # LLM-based field extraction
│   ├── workers/             # Celery tasks
│   └── utils/               # Helper utilities
├── dashboard/               # Streamlit frontend
├── tests/                   # Test suite
├── alembic/                 # Database migrations
└── docker/                  # Docker configurations
```

## 🛠️ Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Docker (optional)

### Quick Start

1. **Clone and setup environment**:
```bash
cd "Document ingestion"
python -m venv venv
source venv/bin/activate
pip install -e .
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Start services**:
```bash
# Start Redis
docker run -d -p 6379:6379 --name redis redis:7-alpine

# Start PostgreSQL
docker run -d -p 5432:5432 --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=document_ingestion \
  postgres:14-alpine

# Run database migrations
alembic upgrade head
```

4. **Start the application**:
```bash
# Terminal 1: API Server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Celery Worker
celery -A src.workers.celery_app worker --loglevel=info

# Terminal 3: Dashboard
streamlit run dashboard/app.py
```

## 🔧 Usage

### Upload a Document

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### Check Status

```bash
curl "http://localhost:8000/api/v1/documents/{job_id}"
```

### Search Documents

```bash
curl "http://localhost:8000/api/v1/search?q=invoice+2024"
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run stress tests with Augraphy
pytest tests/stress/ -v

# Run load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## 📊 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Dashboard**: http://localhost:8501

## 📈 Metrics

- **CER Target**: < 5% for printed text, < 15% for handwriting
- **Processing Speed**: ~2-5 seconds per page
- **Concurrent Load**: Supports 50+ simultaneous uploads

## 📝 License

MIT License
