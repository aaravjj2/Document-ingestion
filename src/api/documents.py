"""Document upload and management API endpoints."""

import logging
import mimetypes
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_async_session
from src.models import Document, DocumentStatus, DocumentType
from src.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
    OCRResponse,
    ReviewResponse,
    ReviewUpdate,
)
from src.services.storage import DocumentRepository
from src.workers.tasks import process_document, reprocess_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


# ============== Upload Endpoint ==============

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document for processing",
    description="Upload a document (PDF, PNG, JPG, TIFF) for OCR and extraction",
)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
) -> DocumentUploadResponse:
    """
    Upload a document for processing.
    
    The document is queued for async processing via Celery.
    Returns immediately with a job_id to track status.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    
    suffix = Path(file.filename).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Supported: {', '.join(settings.allowed_extensions)}",
        )
    
    # Check file size
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{suffix}"
    
    # Create upload directory structure (by date)
    date_dir = datetime.utcnow().strftime("%Y/%m/%d")
    upload_path = settings.upload_dir / date_dir
    upload_path.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_path / safe_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    logger.info(f"Saved uploaded file: {file_path}")
    
    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(file.filename)
    
    # Create database record
    repo = DocumentRepository(session)
    document = await repo.create_document(
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        mime_type=mime_type,
    )
    await session.commit()
    
    # Queue for processing
    task = process_document.delay(str(document.id), str(file_path))
    logger.info(f"Queued document {document.id} for processing. Task: {task.id}")
    
    return DocumentUploadResponse(
        job_id=document.id,
        filename=file.filename,
        status="queued",
        message="Document queued for processing",
    )


# ============== Status & Retrieval Endpoints ==============

@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details",
)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> DocumentDetailResponse:
    """Get detailed information about a document."""
    repo = DocumentRepository(session)
    document, metadata = await repo.get_document_with_metadata(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )
    
    return DocumentDetailResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        file_size=document.file_size,
        page_count=int(document.page_count) if document.page_count else None,
        status=document.status,
        document_type=document.document_type,
        classification_confidence=document.classification_confidence,
        ocr_confidence=document.ocr_confidence,
        raw_text=document.raw_text,
        extracted_data=metadata.data if metadata else None,
        upload_timestamp=document.upload_timestamp,
        processing_started_at=document.processing_started_at,
        processing_completed_at=document.processing_completed_at,
    )


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get document processing status",
)
async def get_document_status(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> DocumentStatusResponse:
    """Get the current processing status of a document."""
    repo = DocumentRepository(session)
    document = await repo.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )
    
    return DocumentStatusResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        document_type=document.document_type,
        ocr_confidence=document.ocr_confidence,
        upload_timestamp=document.upload_timestamp,
        processing_started_at=document.processing_started_at,
        processing_completed_at=document.processing_completed_at,
        error_log=document.error_log,
    )


@router.get(
    "/{document_id}/ocr",
    response_model=OCRResponse,
    summary="Get detailed OCR results",
)
async def get_document_ocr(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> OCRResponse:
    """Get the full OCR details including bounding boxes."""
    repo = DocumentRepository(session)
    document = await repo.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )
    
    # Map OCR Result (ORM) to OCRResultSchema
    results = []
    if document.ocr_results:
        for ocr_res in document.ocr_results:
            results.append({
                "text": ocr_res.text,
                "confidence": ocr_res.confidence,
                "bounding_box": ocr_res.bounding_box,
                "page_number": int(ocr_res.page_number or 1),
                "sequence_order": int(ocr_res.sequence_order) if ocr_res.sequence_order is not None else None
            })

    return OCRResponse(
        document_id=document.id,
        results=results,
        average_confidence=document.ocr_confidence or 0.0,
        total_text=document.raw_text or "",
        page_count=int(document.page_count or 1),
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
)
async def list_documents(
    status_filter: DocumentStatus | None = Query(None, alias="status"),
    type_filter: DocumentType | None = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
) -> DocumentListResponse:
    """List documents with filtering and pagination."""
    repo = DocumentRepository(session)
    documents, total = await repo.list_documents(
        status=status_filter,
        document_type=type_filter,
        page=page,
        page_size=page_size,
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return DocumentListResponse(
        documents=[
            DocumentStatusResponse(
                id=doc.id,
                filename=doc.filename,
                status=doc.status,
                document_type=doc.document_type,
                ocr_confidence=doc.ocr_confidence,
                upload_timestamp=doc.upload_timestamp,
                processing_started_at=doc.processing_started_at,
                processing_completed_at=doc.processing_completed_at,
                error_log=doc.error_log,
            )
            for doc in documents
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ============== Reprocess & Review Endpoints ==============

@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentStatusResponse,
    summary="Reprocess a document",
)
async def reprocess_document_endpoint(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> DocumentStatusResponse:
    """Reprocess a failed or flagged document."""
    repo = DocumentRepository(session)
    document = await repo.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )
    
    # Queue for reprocessing
    task = reprocess_document.delay(str(document_id))
    logger.info(f"Queued document {document_id} for reprocessing. Task: {task.id}")
    
    # Update status
    document = await repo.update_document_status(document_id, DocumentStatus.PENDING)
    await session.commit()
    
    return DocumentStatusResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
        document_type=document.document_type,
        ocr_confidence=document.ocr_confidence,
        upload_timestamp=document.upload_timestamp,
        processing_started_at=document.processing_started_at,
        processing_completed_at=document.processing_completed_at,
        error_log=None,
    )


@router.put(
    "/{document_id}/review",
    response_model=ReviewResponse,
    summary="Update document after review",
)
async def update_document_review(
    document_id: uuid.UUID,
    review: ReviewUpdate,
    session: AsyncSession = Depends(get_async_session),
) -> ReviewResponse:
    """Update extracted data after human review."""
    repo = DocumentRepository(session)
    document = await repo.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )
    
    # Update extracted metadata
    metadata = await repo.update_extracted_metadata(
        document_id,
        data=review.extracted_data,
        validated_by="reviewer",  # Could be passed from auth context
    )
    
    # Update document type if provided
    if review.document_type:
        await repo.update_document_classification(
            document_id,
            document_type=review.document_type,
            classification_confidence=1.0,  # Human-verified
        )
    
    # Mark as completed
    await repo.update_document_status(document_id, DocumentStatus.COMPLETED)
    await session.commit()
    
    return ReviewResponse(
        document_id=document_id,
        status=DocumentStatus.COMPLETED,
        message="Document updated and marked as completed",
    )


# ============== Delete Endpoint ==============

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a document and its associated files."""
    repo = DocumentRepository(session)
    document = await repo.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )
    
    # Delete file from disk
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()
        logger.info(f"Deleted file: {file_path}")
    
    # Delete from database
    await repo.delete_document(document_id)
    await session.commit()
    
    logger.info(f"Deleted document: {document_id}")

# ============== Download Endpoint ==============

@router.get(
    "/{document_id}/download",
    summary="Download document file",
)
async def download_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """Download the original document file."""
    repo = DocumentRepository(session)
    document = await repo.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )
    
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server",
        )
        
    return FileResponse(
        path=file_path,
        filename=document.original_filename,
        media_type=document.mime_type
    )
