"""Classification services module."""

from src.services.classification.classifier import (
    ClassificationResult,
    DocumentClassifier,
    classify_document,
)

__all__ = [
    "DocumentClassifier",
    "ClassificationResult",
    "classify_document",
]
