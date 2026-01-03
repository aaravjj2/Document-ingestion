# Makefile for common development tasks

.PHONY: help install dev test lint format clean docker-up docker-down migrate run-api run-worker run-dashboard

help:
	@echo "Available commands:"
	@echo "  install       - Install production dependencies"
	@echo "  dev           - Install development dependencies"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linting"
	@echo "  format        - Format code"
	@echo "  clean         - Clean build artifacts"
	@echo "  docker-up     - Start all services with Docker"
	@echo "  docker-down   - Stop all Docker services"
	@echo "  migrate       - Run database migrations"
	@echo "  run-api       - Run the API server locally"
	@echo "  run-worker    - Run Celery worker locally"
	@echo "  run-dashboard - Run Streamlit dashboard locally"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=src --cov-report=html

test-unit:
	pytest tests/ -v --ignore=tests/stress --ignore=tests/load

test-stress:
	pytest tests/stress/ -v

test-load:
	cd tests/load && locust -f locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:8000

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

# Docker commands
docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down -v

docker-logs:
	docker-compose logs -f

docker-rebuild:
	docker-compose down -v
	docker-compose build --no-cache
	docker-compose up -d

# Database commands
migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(MSG)"

migrate-down:
	alembic downgrade -1

# Local development commands
run-api:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

run-worker:
	celery -A src.workers.celery_app worker --loglevel=info --concurrency=2 -Q document_processing,default

run-beat:
	celery -A src.workers.celery_app beat --loglevel=info -Q document_processing,default

run-flower:
	celery -A src.workers.celery_app flower --port=5555

run-dashboard:
	streamlit run dashboard/app.py --server.port 8501

# Combined local development
run-dev:
	@echo "Starting development environment..."
	@echo "Run these commands in separate terminals:"
	@echo "  make run-api"
	@echo "  make run-worker"
	@echo "  make run-dashboard"

# Create necessary directories
setup-dirs:
	mkdir -p uploads/originals uploads/processed logs

# Initialize database (first time setup)
init-db:
	alembic upgrade head

# Full setup for development
setup: dev setup-dirs init-db
	@echo "Development environment setup complete!"
	@echo "Copy .env.example to .env and configure your settings"
