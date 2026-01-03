"""Services module initialization."""

from src.services.classification import (
    ClassificationResult,
    DocumentClassifier,
    classify_document,
)
from src.services.extraction import (
    ExtractionService,
    extract_document_fields,
)
from src.services.ocr import (
    OCRDetection,
    OCRPageResult,
    OCRService,
    process_document_ocr,
)
from src.services.preprocessing import (
    ImagePreprocessor,
    PDFConverter,
    convert_pdf_to_images,
    preprocess_image,
)
from src.services.storage import DocumentRepository, SearchService

__all__ = [
    # Preprocessing
    "ImagePreprocessor",
    "preprocess_image",
    "PDFConverter",
    "convert_pdf_to_images",
    # OCR
    "OCRService",
    "OCRDetection",
    "OCRPageResult",
    "process_document_ocr",
    # Classification
    "DocumentClassifier",
    "ClassificationResult",
    "classify_document",
    # Extraction
    "ExtractionService",
    "extract_document_fields",
    # Storage
    "DocumentRepository",
    "SearchService",
]
