"""
Web dashboard routes for the document ingestion service.
Provides HTML UI for document management and monitoring.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_async_session
from src.services.storage.repository import DocumentRepository

router = APIRouter(tags=["dashboard"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="src/templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_home(request: Request):
    """Main dashboard page with overview stats."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/documents", response_class=HTMLResponse, include_in_schema=False)
async def documents_page(request: Request):
    """Documents list page."""
    return templates.TemplateResponse("documents.html", {"request": request})


@router.get("/upload", response_class=HTMLResponse, include_in_schema=False)
async def upload_page(request: Request):
    """Document upload page."""
    return templates.TemplateResponse("upload.html", {"request": request})


@router.get("/health", response_class=HTMLResponse, include_in_schema=False)
async def health_page(request: Request):
    """System health monitoring page."""
    return templates.TemplateResponse("health.html", {"request": request})


@router.get("/documents/{document_id}", response_class=HTMLResponse, include_in_schema=False)
async def document_detail_page(
    request: Request,
    document_id: str,
    db: AsyncSession = Depends(get_async_session)
):
    """Document detail page."""
    repo = DocumentRepository(db)
    document = await repo.get_document(document_id)
    
    if not document:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_code": 404,
                "error_message": "Document not found"
            },
            status_code=404
        )
    
    return templates.TemplateResponse(
        "document_detail.html",
        {"request": request, "document": document}
    )
