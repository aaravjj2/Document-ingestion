"""SQLAlchemy models for the document ingestion service."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import relationship

from src.core.database import Base
from src.models.enums import DocumentStatus, DocumentType


class Document(Base):
    """Main document model for tracking uploaded files and their processing status."""

    __tablename__ = "documents"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Float, nullable=True)  # Size in bytes
    mime_type = Column(String(100), nullable=True)
    page_count = Column(Float, nullable=True)

    # Processing status
    status = Column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )

    # Classification
    document_type = Column(
        String(50),
        default="unknown",
        nullable=True,
    )
    classification_confidence = Column(Float, nullable=True)

    # OCR results
    ocr_confidence = Column(Float, nullable=True)
    raw_text = Column(Text, nullable=True)
    
    # Full-text search vector
    text_search_vector = Column(TSVECTOR, nullable=True)

    # Timestamps
    upload_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Alias for upload_timestamp
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)

    # Error handling
    error_log = Column(Text, nullable=True)
    retry_count = Column(Float, default=0, nullable=False)

    # Relationships
    extracted_metadata = relationship(
        "ExtractedMetadata",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )
    ocr_results = relationship(
        "OCRResult",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_documents_status", "status"),
        Index("idx_documents_type", "document_type"),
        Index("idx_documents_upload_timestamp", "upload_timestamp"),
        Index(
            "idx_documents_text_search",
            "text_search_vector",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"


class ExtractedMetadata(Base):
    """Extracted structured data from documents."""

    __tablename__ = "extracted_metadata"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to document
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Document type (denormalized for query performance)
    document_type = Column(String(50), nullable=True)

    # Flexible JSONB storage for extracted fields
    data = Column(JSONB, nullable=False, default=dict)

    # Extraction metadata
    extraction_model = Column(String(100), nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    extraction_timestamp = Column(DateTime, default=datetime.utcnow)

    # Validation status
    is_validated = Column(Float, default=0)  # 0=False, 1=True
    validated_by = Column(String(100), nullable=True)
    validated_at = Column(DateTime, nullable=True)

    # Relationship
    document = relationship("Document", back_populates="extracted_metadata")

    # Indexes for JSONB queries
    __table_args__ = (
        Index("idx_metadata_document_type", "document_type"),
        Index("idx_metadata_data", "data", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<ExtractedMetadata(document_id={self.document_id}, type={self.document_type})>"


class OCRResult(Base):
    """Individual OCR detection results with bounding boxes."""

    __tablename__ = "ocr_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Page information (for multi-page documents)
    page_number = Column(Float, default=1, nullable=False)

    # OCR detection data
    text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Bounding box coordinates (stored as JSON)
    # Format: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    bounding_box = Column(JSONB, nullable=False)

    # Text block ordering
    sequence_order = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    document = relationship("Document", back_populates="ocr_results")

    # Indexes
    __table_args__ = (
        Index("idx_ocr_document_page", "document_id", "page_number"),
    )

    def __repr__(self) -> str:
        return f"<OCRResult(document_id={self.document_id}, text={self.text[:30]}...)>"


class ProcessingQueue(Base):
    """Queue tracking for document processing."""

    __tablename__ = "processing_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    celery_task_id = Column(String(255), nullable=True)
    priority = Column(Float, default=5, nullable=False)  # 1=highest, 10=lowest
    
    queued_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_queue_priority", "priority", "queued_at"),
    )
