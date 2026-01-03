"""Document status enumeration."""

from enum import Enum


class DocumentStatus(str, Enum):
    """Status of document processing."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class DocumentType(str, Enum):
    """Types of documents that can be classified."""
    
    INVOICE = "invoice"
    RECEIPT = "receipt"
    MEDICAL = "medical"
    LEGAL = "legal"
    FINANCIAL = "financial"
    IDENTITY = "identity"
    CORRESPONDENCE = "correspondence"
    UNKNOWN = "unknown"
