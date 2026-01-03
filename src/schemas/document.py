"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import DocumentStatus, DocumentType


# ============== Base Schemas ==============

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


# ============== Document Schemas ==============

class DocumentUploadResponse(BaseSchema):
    """Response after uploading a document."""
    
    status: str = "queued"
    job_id: UUID
    filename: str
    message: str = "Document queued for processing"


class DocumentStatusResponse(BaseSchema):
    """Response for document status query."""
    
    id: UUID
    filename: str
    status: DocumentStatus
    document_type: DocumentType | None = None
    ocr_confidence: float | None = None
    upload_timestamp: datetime
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    error_log: str | None = None


class DocumentDetailResponse(BaseSchema):
    """Detailed document response including extracted data."""
    
    id: UUID
    filename: str
    original_filename: str
    file_size: float | None = None
    page_count: int | None = None
    status: DocumentStatus
    document_type: DocumentType | None = None
    classification_confidence: float | None = None
    ocr_confidence: float | None = None
    raw_text: str | None = None
    extracted_data: dict[str, Any] | None = None
    upload_timestamp: datetime
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    error_log: str | None = None


class DocumentListResponse(BaseSchema):
    """Response for listing documents."""
    
    documents: list[DocumentStatusResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============== OCR Schemas ==============

class BoundingBox(BaseSchema):
    """Bounding box coordinates for OCR results."""
    
    coordinates: list[list[float]]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]


class OCRResultSchema(BaseSchema):
    """Individual OCR detection result."""
    
    text: str
    confidence: float
    bounding_box: list[list[float]]
    page_number: int = 1
    sequence_order: int | None = None


class OCRResponse(BaseSchema):
    """Full OCR response for a document."""
    
    document_id: UUID
    results: list[OCRResultSchema]
    average_confidence: float
    total_text: str
    page_count: int


# ============== Extraction Schemas ==============

class ExtractedField(BaseSchema):
    """A single extracted field with confidence."""
    
    field_name: str
    value: Any
    confidence: float | None = None


class ExtractionResponse(BaseSchema):
    """Response from field extraction."""
    
    document_id: UUID
    document_type: DocumentType
    extracted_fields: dict[str, Any]
    extraction_confidence: float
    model_used: str


# ============== Invoice-specific Schema ==============

class InvoiceData(BaseSchema):
    """Extracted invoice data."""
    
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    vendor_name: str | None = None
    vendor_address: str | None = None
    customer_name: str | None = None
    customer_address: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    total_amount: float | None = None
    currency: str | None = None
    line_items: list[dict[str, Any]] | None = None


# ============== Medical-specific Schema ==============

class MedicalDocumentData(BaseSchema):
    """Extracted medical document data."""
    
    patient_name: str | None = None
    patient_dob: str | None = None
    provider_name: str | None = None
    facility_name: str | None = None
    document_date: str | None = None
    diagnosis: list[str] | None = None
    medications: list[dict[str, Any]] | None = None
    procedures: list[str] | None = None


# ============== Search Schemas ==============

class SearchQuery(BaseSchema):
    """Search query parameters."""
    
    q: str = Field(..., min_length=1, description="Search query")
    document_type: DocumentType | None = None
    status: DocumentStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseSchema):
    """Individual search result."""
    
    document_id: UUID
    filename: str
    document_type: DocumentType | None
    snippet: str
    relevance_score: float
    upload_timestamp: datetime


class SearchResponse(BaseSchema):
    """Search response with results."""
    
    query: str
    results: list[SearchResult]
    total: int
    page: int
    page_size: int


# ============== Dashboard Schemas ==============

class DashboardMetrics(BaseSchema):
    """Dashboard statistics."""
    
    total_documents: int
    documents_processed: int
    documents_pending: int
    documents_failed: int
    documents_needs_review: int
    average_confidence: float
    average_processing_time: float | None = None  # in seconds
    documents_today: int
    documents_this_week: int


class QueueStatus(BaseSchema):
    """Processing queue status."""
    
    queue_depth: int
    active_workers: int
    average_wait_time: float | None = None


# ============== Review Schemas ==============

class ReviewUpdate(BaseSchema):
    """Update for document review."""
    
    extracted_data: dict[str, Any]
    document_type: DocumentType | None = None
    notes: str | None = None


class ReviewResponse(BaseSchema):
    """Response after review update."""
    
    document_id: UUID
    status: DocumentStatus
    message: str
