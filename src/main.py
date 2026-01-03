"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api import api_router
from src.api.routes.dashboard import router as dashboard_router
from src.core.config import settings
from src.core.database import close_db, init_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Document Ingestion Service...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Document Ingestion Service...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Intelligent Document Ingestion Service",
    description="""
    A production-ready document processing pipeline featuring:
    
    - **OCR**: Extract text from scanned documents using PaddleOCR
    - **Classification**: Auto-detect document types (Invoice, Medical, etc.)
    - **Extraction**: Extract structured fields using LLM
    - **Search**: Full-text search across all documents
    
    ## Features
    
    - Multi-format support: PDF, PNG, JPG, TIFF
    - Async processing with Celery workers
    - Confidence scoring and review flagging
    - RESTful API with comprehensive documentation
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Include routers
app.include_router(dashboard_router)  # Dashboard routes (no prefix, serves HTML)
app.include_router(api_router, prefix=settings.api_prefix)  # API routes





# Run with: uvicorn src.main:app --reload
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
