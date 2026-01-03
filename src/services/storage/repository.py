"""Document storage and database operations service."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from src.models import (
    Document,
    DocumentStatus,
    DocumentType,
    ExtractedMetadata,
    OCRResult,
    ProcessingQueue,
)

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository for document database operations."""

    def __init__(self, session: AsyncSession | Session):
        """Initialize repository with database session."""
        self.session = session
        self._is_async = isinstance(session, AsyncSession)

    # ============== Create Operations ==============

    async def create_document(
        self,
        filename: str,
        original_filename: str,
        file_path: str,
        file_size: float | None = None,
        mime_type: str | None = None,
    ) -> Document:
        """Create a new document record."""
        document = Document(
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            status=DocumentStatus.PENDING.value,  # Use .value for enum
        )
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        logger.info(f"Created document: {document.id}")
        return document

    def create_document_sync(
        self,
        filename: str,
        original_filename: str,
        file_path: str,
        file_size: float | None = None,
        mime_type: str | None = None,
    ) -> Document:
        """Create document (sync version for Celery workers)."""
        document = Document(
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            status=DocumentStatus.PENDING.value,  # Use .value for enum
        )
        self.session.add(document)
        self.session.flush()
        self.session.refresh(document)
        return document

    async def create_extracted_metadata(
        self,
        document_id: UUID,
        document_type: str,
        data: dict[str, Any],
        extraction_model: str | None = None,
        extraction_confidence: float | None = None,
    ) -> ExtractedMetadata:
        """Create extracted metadata for a document."""
        metadata = ExtractedMetadata(
            document_id=document_id,
            document_type=document_type,
            data=data,
            extraction_model=extraction_model,
            extraction_confidence=extraction_confidence,
        )
        self.session.add(metadata)
        await self.session.flush()
        return metadata

    def create_extracted_metadata_sync(
        self,
        document_id: UUID,
        document_type: str,
        data: dict[str, Any],
        extraction_model: str | None = None,
        extraction_confidence: float | None = None,
    ) -> ExtractedMetadata:
        """Create extracted metadata (sync version)."""
        # Check if exists
        existing = self.session.query(ExtractedMetadata).filter_by(document_id=document_id).first()
        if existing:
            existing.document_type = document_type
            existing.data = data
            existing.extraction_model = extraction_model
            existing.extraction_confidence = extraction_confidence
            existing.extraction_timestamp = datetime.utcnow()
            self.session.flush()
            return existing

        metadata = ExtractedMetadata(
            document_id=document_id,
            document_type=document_type,
            data=data,
            extraction_model=extraction_model,
            extraction_confidence=extraction_confidence,
        )
        self.session.add(metadata)
        self.session.flush()
        return metadata

    async def create_ocr_results(
        self,
        document_id: UUID,
        results: list[dict[str, Any]],
    ) -> list[OCRResult]:
        """Bulk create OCR results for a document."""
        ocr_results = []
        for result in results:
            ocr_result = OCRResult(
                document_id=document_id,
                page_number=result.get("page_number", 1),
                text=result["text"],
                confidence=result["confidence"],
                bounding_box=result["bounding_box"],
                sequence_order=result.get("sequence_order"),
            )
            ocr_results.append(ocr_result)
        
        self.session.add_all(ocr_results)
        await self.session.flush()
        return ocr_results

    def create_ocr_results_sync(
        self,
        document_id: UUID,
        results: list[dict[str, Any]],
    ) -> list[OCRResult]:
        """Bulk create OCR results (sync version)."""
        ocr_results = []
        for result in results:
            ocr_result = OCRResult(
                document_id=document_id,
                page_number=result.get("page_number", 1),
                text=result["text"],
                confidence=result["confidence"],
                bounding_box=result["bounding_box"],
                sequence_order=result.get("sequence_order"),
            )
            ocr_results.append(ocr_result)
        
        self.session.add_all(ocr_results)
        self.session.flush()
        return ocr_results

    # ============== Read Operations ==============

    async def get_document(self, document_id: UUID) -> Document | None:
        """Get document by ID with relationships loaded."""
        result = await self.session.execute(
            select(Document)
            .options(
                selectinload(Document.extracted_metadata),
                selectinload(Document.ocr_results)
            )
            .where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    def get_document_sync(self, document_id: UUID) -> Document | None:
        """Get document by ID (sync version)."""
        return self.session.query(Document).filter(Document.id == document_id).first()

    async def get_document_with_metadata(
        self,
        document_id: UUID,
    ) -> tuple[Document | None, ExtractedMetadata | None]:
        """Get document with its extracted metadata."""
        doc_result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = doc_result.scalar_one_or_none()
        
        if not document:
            return None, None
        
        meta_result = await self.session.execute(
            select(ExtractedMetadata).where(ExtractedMetadata.document_id == document_id)
        )
        metadata = meta_result.scalar_one_or_none()
        
        return document, metadata

    async def list_documents(
        self,
        status: DocumentStatus | None = None,
        document_type: DocumentType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        """List documents with filtering and pagination."""
        query = select(Document)
        count_query = select(func.count(Document.id))
        
        if status:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)
        
        if document_type:
            query = query.where(Document.document_type == document_type)
            count_query = count_query.where(Document.document_type == document_type)
        
        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()
        
        # Apply pagination
        query = query.order_by(Document.upload_timestamp.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        documents = list(result.scalars().all())
        
        return documents, total

    async def get_documents_needing_review(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Document], int]:
        """Get documents flagged for review."""
        return await self.list_documents(
            status=DocumentStatus.NEEDS_REVIEW,
            page=page,
            page_size=page_size,
        )

    async def get_ocr_results(
        self,
        document_id: UUID,
    ) -> list[OCRResult]:
        """Get OCR results for a document."""
        result = await self.session.execute(
            select(OCRResult)
            .where(OCRResult.document_id == document_id)
            .order_by(OCRResult.page_number, OCRResult.sequence_order)
        )
        return list(result.scalars().all())

    # ============== Update Operations ==============

    async def update_document_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_log: str | None = None,
    ) -> Document | None:
        """Update document status."""
        updates: dict[str, Any] = {"status": status}
        
        if status == DocumentStatus.PROCESSING:
            updates["processing_started_at"] = datetime.utcnow()
        elif status in (DocumentStatus.COMPLETED, DocumentStatus.FAILED):
            updates["processing_completed_at"] = datetime.utcnow()
        
        if error_log:
            updates["error_log"] = error_log
        
        await self.session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(**updates)
        )
        await self.session.flush()
        
        return await self.get_document(document_id)

    def update_document_status_sync(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_log: str | None = None,
    ) -> Document | None:
        """Update document status (sync version)."""
        document = self.get_document_sync(document_id)
        if not document:
            return None
        
        document.status = status
        
        if status == DocumentStatus.PROCESSING:
            document.processing_started_at = datetime.utcnow()
        elif status in (DocumentStatus.COMPLETED, DocumentStatus.FAILED):
            document.processing_completed_at = datetime.utcnow()
        
        if error_log:
            document.error_log = error_log
        
        self.session.flush()
        return document

    async def update_document_ocr(
        self,
        document_id: UUID,
        raw_text: str,
        ocr_confidence: float,
        page_count: int | None = None,
    ) -> Document | None:
        """Update document with OCR results."""
        updates = {
            "raw_text": raw_text,
            "ocr_confidence": ocr_confidence,
        }
        
        if page_count:
            updates["page_count"] = page_count
        
        # Update text search vector
        await self.session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(**updates)
        )
        
        # Update text search vector separately (requires raw SQL for tsvector)
        await self.session.execute(
            text("""
                UPDATE documents 
                SET text_search_vector = to_tsvector('english', :text)
                WHERE id = :doc_id
            """),
            {"text": raw_text, "doc_id": str(document_id)},
        )
        
        await self.session.flush()
        return await self.get_document(document_id)

    def update_document_ocr_sync(
        self,
        document_id: UUID,
        raw_text: str,
        ocr_confidence: float,
        page_count: int | None = None,
    ) -> Document | None:
        """Update document with OCR results (sync version)."""
        document = self.get_document_sync(document_id)
        if not document:
            return None
        
        document.raw_text = raw_text
        document.ocr_confidence = ocr_confidence
        
        if page_count:
            document.page_count = page_count
        
        self.session.flush()
        
        # Update text search vector
        self.session.execute(
            text("""
                UPDATE documents 
                SET text_search_vector = to_tsvector('english', :text)
                WHERE id = :doc_id
            """),
            {"text": raw_text, "doc_id": str(document_id)},
        )
        
        self.session.flush()
        return document

    async def update_document_classification(
        self,
        document_id: UUID,
        document_type: DocumentType,
        classification_confidence: float,
    ) -> Document | None:
        """Update document classification."""
        await self.session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                document_type=document_type,
                classification_confidence=classification_confidence,
            )
        )
        await self.session.flush()
        return await self.get_document(document_id)

    def update_document_classification_sync(
        self,
        document_id: UUID,
        document_type: DocumentType,
        classification_confidence: float,
    ) -> Document | None:
        """Update document classification (sync version)."""
        document = self.get_document_sync(document_id)
        if not document:
            return None
        
        document.document_type = document_type
        document.classification_confidence = classification_confidence
        self.session.flush()
        return document

    async def update_extracted_metadata(
        self,
        document_id: UUID,
        data: dict[str, Any],
        validated_by: str | None = None,
    ) -> ExtractedMetadata | None:
        """Update extracted metadata (for review corrections)."""
        result = await self.session.execute(
            select(ExtractedMetadata).where(ExtractedMetadata.document_id == document_id)
        )
        metadata = result.scalar_one_or_none()
        
        if not metadata:
            return None
        
        metadata.data = data
        if validated_by:
            metadata.is_validated = 1
            metadata.validated_by = validated_by
            metadata.validated_at = datetime.utcnow()
        
        await self.session.flush()
        return metadata

    # ============== Delete Operations ==============

    async def delete_document(self, document_id: UUID) -> bool:
        """Delete a document and all related records."""
        document = await self.get_document(document_id)
        if not document:
            return False
        
        await self.session.delete(document)
        await self.session.flush()
        logger.info(f"Deleted document: {document_id}")
        return True

    # ============== Statistics ==============

    async def get_statistics(self) -> dict[str, Any]:
        """Get document processing statistics."""
        # Total documents
        total_result = await self.session.execute(
            select(func.count(Document.id))
        )
        total = total_result.scalar_one()
        
        # Status counts
        status_result = await self.session.execute(
            select(Document.status, func.count(Document.id))
            .group_by(Document.status)
        )
        status_counts = {str(row[0]) if isinstance(row[0], str) else row[0].value: row[1] for row in status_result.all()}
        
        # Average confidence
        confidence_result = await self.session.execute(
            select(func.avg(Document.ocr_confidence))
            .where(Document.ocr_confidence.isnot(None))
        )
        avg_confidence = confidence_result.scalar_one() or 0.0
        
        # Average processing time
        time_result = await self.session.execute(
            select(
                func.avg(
                    func.extract('epoch', Document.processing_completed_at) -
                    func.extract('epoch', Document.processing_started_at)
                )
            )
            .where(Document.processing_completed_at.isnot(None))
            .where(Document.processing_started_at.isnot(None))
        )
        avg_processing_time = time_result.scalar_one()
        
        # Documents today
        today_result = await self.session.execute(
            select(func.count(Document.id))
            .where(func.date(Document.upload_timestamp) == func.current_date())
        )
        documents_today = today_result.scalar_one()
        
        return {
            "total_documents": total,
            "documents_processed": status_counts.get("completed", 0),
            "documents_pending": status_counts.get("pending", 0),
            "documents_failed": status_counts.get("failed", 0),
            "documents_needs_review": status_counts.get("needs_review", 0),
            "average_confidence": float(avg_confidence),
            "average_processing_time": float(avg_processing_time) if avg_processing_time else None,
            "documents_today": documents_today,
        }
