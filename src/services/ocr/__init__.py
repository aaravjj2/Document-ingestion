"""OCR services module."""

from src.services.ocr.ocr_service import (
    OCRDetection,
    OCRPageResult,
    OCRService,
    process_document_ocr,
)

__all__ = [
    "OCRService",
    "OCRDetection",
    "OCRPageResult",
    "process_document_ocr",
]
