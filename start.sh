#!/bin/bash

# Startup script for the Document Ingestion Service

set -e

echo "🚀 Starting Intelligent Document Ingestion Service..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please configure .env with your settings before running in production"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads/originals uploads/processed logs

# Check if running with Docker
if [ "$1" == "--docker" ] || [ "$1" == "-d" ]; then
    echo "🐳 Starting with Docker Compose..."
    docker-compose up -d --build
    
    echo ""
    echo "✅ Services started!"
    echo ""
    echo "📍 Access points:"
    echo "   - API:       http://localhost:8000"
    echo "   - Dashboard: http://localhost:8501"
    echo "   - Flower:    http://localhost:5555"
    echo "   - API Docs:  http://localhost:8000/docs"
    echo ""
    echo "📋 View logs: docker-compose logs -f"
    echo "🛑 Stop:      docker-compose down"
    exit 0
fi

# Local development mode
echo "💻 Starting in local development mode..."
echo ""
echo "Prerequisites:"
echo "  - PostgreSQL running on localhost:5432"
echo "  - Redis running on localhost:6379"
echo ""

# Check for PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL client not found. Please ensure PostgreSQL is running."
fi

# Check for Redis
if ! command -v redis-cli &> /dev/null; then
    echo "⚠️  Redis client not found. Please ensure Redis is running."
fi

# Install dependencies if needed
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
else
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        source venv/bin/activate
    fi
fi

# Run migrations
echo "🗄️  Running database migrations..."
alembic upgrade head

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the services, run in separate terminals:"
echo ""
echo "  Terminal 1 (API):       make run-api"
echo "  Terminal 2 (Worker):    make run-worker"
echo "  Terminal 3 (Dashboard): make run-dashboard"
echo ""
echo "Or use Docker: ./start.sh --docker"
