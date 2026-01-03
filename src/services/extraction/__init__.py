"""Extraction services module."""

from src.services.extraction.extractor import (
    ExtractionService,
    FinancialExtraction,
    GenericExtraction,
    InvoiceExtraction,
    LegalExtraction,
    MedicalExtraction,
    OllamaClient,
    OpenAIClient,
    ReceiptExtraction,
    extract_document_fields,
)

__all__ = [
    "ExtractionService",
    "OpenAIClient",
    "OllamaClient",
    "InvoiceExtraction",
    "ReceiptExtraction",
    "MedicalExtraction",
    "LegalExtraction",
    "FinancialExtraction",
    "GenericExtraction",
    "extract_document_fields",
]
