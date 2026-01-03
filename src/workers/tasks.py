"""Celery tasks for document processing."""

import logging
import traceback
from pathlib import Path
from uuid import UUID

from celery import Task

from src.core.config import settings
from src.core.database import get_sync_session
from src.models.enums import DocumentStatus, DocumentType
from src.services.classification import classify_document, DocumentClassifier
from src.services.extraction import ExtractionService
from src.services.ocr import process_document_ocr
from src.services.storage import DocumentRepository
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class DocumentProcessingTask(Task):
    """Base task class with error handling and retry logic."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True
    max_retries = 3

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")
        
        # Update document status to FAILED
        if args:
            document_id = args[0]
            session = get_sync_session()
            try:
                repo = DocumentRepository(session)
                repo.update_document_status_sync(
                    UUID(document_id),
                    DocumentStatus.FAILED,
                    error_log=str(exc),
                )
                session.commit()
            except Exception as e:
                logger.error(f"Failed to update document status: {e}")
            finally:
                session.close()


@celery_app.task(bind=True, base=DocumentProcessingTask)
def process_document(self, document_id: str, file_path: str) -> dict:
    """
    Main document processing task.
    
    Orchestrates the full processing pipeline:
    1. OCR extraction
    2. Document classification
    3. Field extraction via LLM
    4. Storage of results
    
    Args:
        document_id: UUID of the document
        file_path: Path to the document file
        
    Returns:
        Processing result summary
    """
    logger.info(f"Starting processing for document: {document_id}")
    
    session = get_sync_session()
    doc_uuid = UUID(document_id)
    
    try:
        repo = DocumentRepository(session)
        
        # Update status to PROCESSING
        repo.update_document_status_sync(doc_uuid, DocumentStatus.PROCESSING)
        session.commit()
        
        # Step 1: OCR Processing
        logger.info(f"[{document_id}] Starting OCR...")
        ocr_result = process_document_ocr(
            file_path,
            language=settings.ocr_language,
            confidence_threshold=settings.ocr_confidence_threshold,
        )
        
        raw_text = ocr_result["raw_text"]
        ocr_confidence = ocr_result["average_confidence"]
        page_count = ocr_result["page_count"]
        needs_review = ocr_result["needs_review"]
        
        logger.info(f"[{document_id}] OCR completed. Confidence: {ocr_confidence:.2%}")
        
        # Update document with OCR results
        repo.update_document_ocr_sync(
            doc_uuid,
            raw_text=raw_text,
            ocr_confidence=ocr_confidence,
            page_count=page_count,
        )

        # Step 1.5: Check for empty text
        if not raw_text or not raw_text.strip():
            logger.warning(f"[{document_id}] OCR failed to detect text.")
            repo.update_document_status_sync(
                doc_uuid,
                DocumentStatus.FAILED,
                error_log="OCR failed to detect any text. The document may be blank, too blurry, or contain unsupported content.",
            )
            session.commit()
            return {
                "document_id": document_id,
                "status": "failed",
                "ocr_confidence": 0.0,
                "document_type": "unknown",
                "extraction_confidence": 0.0,
                "page_count": page_count,
            }
        
        # Store detailed OCR results
        ocr_detections = []
        for detection in ocr_result["detections"]:
            ocr_detections.append({
                "page_number": detection.get("page", 1),
                "text": detection["text"],
                "confidence": detection["confidence"],
                "bounding_box": detection["bounding_box"],
                "sequence_order": detection.get("sequence_order"),
            })
        
        if ocr_detections:
            repo.create_ocr_results_sync(doc_uuid, ocr_detections)
        
        session.commit()
        
        # Step 2: Classification
        logger.info(f"[{document_id}] Classifying document...")
        classification = classify_document(raw_text)
        
        # LLM Fallback for Unknown Documents
        if classification.document_type == DocumentType.UNKNOWN:
            logger.info(f"[{document_id}] Keyword classification uncertain. Attempting LLM fallback...")
            try:
                extraction_service = ExtractionService(use_local_llm=settings.use_local_llm)
                llm_classifier = DocumentClassifier()
                llm_result = llm_classifier.classify_with_llm(raw_text, extraction_service.llm_client)
                
                if llm_result.document_type != DocumentType.UNKNOWN:
                    classification = llm_result
                    logger.info(f"[{document_id}] LLM Classified as: {classification.document_type} ({classification.confidence:.2%})")
            except Exception as e:
                logger.warning(f"[{document_id}] LLM classification fallback failed: {e}")

        document_type = classification.document_type
        classification_confidence = classification.confidence
        
        logger.info(f"[{document_id}] Final Classification: {document_type} ({classification_confidence:.2%})")
        
        repo.update_document_classification_sync(
            doc_uuid,
            document_type=document_type,
            classification_confidence=classification_confidence,
        )
        session.commit()
        
        # Step 3: Field Extraction
        logger.info(f"[{document_id}] Extracting fields...")
        
        try:
            extraction_service = ExtractionService(use_local_llm=settings.use_local_llm)
            extracted_data, extraction_confidence = extraction_service.extract_with_confidence(
                raw_text,
                document_type,
            )
            
            logger.info(f"[{document_id}] Extraction completed. Fields: {len(extracted_data)}")
            
            # Store extracted metadata
            repo.create_extracted_metadata_sync(
                document_id=doc_uuid,
                document_type=document_type.value,
                data=extracted_data,
                extraction_model=extraction_service.model_name,
                extraction_confidence=extraction_confidence,
            )
            session.commit()
        except Exception as e:
            logger.error(f"[{document_id}] Extraction failed: {e}")
            # Don't fail the whole process, just skip extraction
            needs_review = True
            # Optionally log the error in the document error log, but append it
            # repo.update_document_status_sync(doc_uuid, DocumentStatus.PROCESSING, error_log=f"Extraction failed: {e}")
            # session.commit()
        
        # Step 4: Determine final status
        if needs_review or ocr_confidence < settings.ocr_confidence_threshold:
            final_status = DocumentStatus.NEEDS_REVIEW
            logger.info(f"[{document_id}] Flagged for review (low confidence)")
        else:
            final_status = DocumentStatus.COMPLETED
        
        repo.update_document_status_sync(doc_uuid, final_status)
        session.commit()
        
        logger.info(f"[{document_id}] Processing completed. Status: {final_status}")
        
        return {
            "document_id": document_id,
            "status": final_status.value,
            "ocr_confidence": ocr_confidence,
            "document_type": document_type.value,
            "extraction_confidence": extraction_confidence,
            "page_count": page_count,
        }
        
    except Exception as e:
        logger.error(f"[{document_id}] Processing failed: {e}")
        logger.error(traceback.format_exc())
        
        # Update status to FAILED
        try:
            repo = DocumentRepository(session)
            repo.update_document_status_sync(
                doc_uuid,
                DocumentStatus.FAILED,
                error_log=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
            )
            session.commit()
        except Exception:
            pass
        
        raise
        
    finally:
        session.close()


@celery_app.task(bind=True)
def reprocess_document(self, document_id: str) -> dict:
    """
    Reprocess a failed or review-flagged document.
    
    Args:
        document_id: UUID of the document
        
    Returns:
        Processing result
    """
    session = get_sync_session()
    doc_uuid = UUID(document_id)
    
    try:
        repo = DocumentRepository(session)
        document = repo.get_document_sync(doc_uuid)
        
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        
        # Reset status
        document.status = DocumentStatus.PENDING
        document.error_log = None
        document.retry_count = (document.retry_count or 0) + 1
        session.commit()
        
        # Reprocess
        return process_document(document_id, document.file_path)
        
    finally:
        session.close()


@celery_app.task
def cleanup_old_files(days: int = 30) -> dict:
    """
    Cleanup old temporary files.
    
    Args:
        days: Delete files older than this many days
        
    Returns:
        Cleanup summary
    """
    import os
    import time
    
    upload_dir = Path(settings.upload_dir)
    cutoff_time = time.time() - (days * 86400)
    
    deleted_count = 0
    deleted_size = 0
    
    for file_path in upload_dir.rglob("*"):
        if file_path.is_file():
            if file_path.stat().st_mtime < cutoff_time:
                size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                deleted_size += size
    
    logger.info(f"Cleaned up {deleted_count} files ({deleted_size / 1024 / 1024:.2f} MB)")
    
    return {
        "deleted_files": deleted_count,
        "deleted_size_mb": deleted_size / 1024 / 1024,
    }


@celery_app.task
def health_check() -> dict:
    """Health check task to verify worker is running."""
    return {
        "status": "healthy",
        "worker": "document_processing",
    }
