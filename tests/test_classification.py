"""Tests for document classification service."""

import pytest

from src.models.enums import DocumentType
from src.services.classification import DocumentClassifier, classify_document


class TestDocumentClassifier:
    """Tests for DocumentClassifier class."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return DocumentClassifier()

    def test_classify_invoice(self, classifier):
        """Test invoice classification."""
        text = """
        INVOICE
        Invoice Number: INV-2024-001
        Invoice Date: January 15, 2024
        
        Bill To:
        John Smith
        123 Main St
        
        Items:
        Widget A - Qty: 5 - Unit Price: $10.00 - Total: $50.00
        
        Subtotal: $50.00
        Tax (10%): $5.00
        Total Amount Due: $55.00
        """
        
        result = classifier.classify(text)
        
        assert result.document_type == DocumentType.INVOICE
        assert result.confidence > 0.5
        assert "invoice" in [k.lower() for k in result.matched_keywords]

    def test_classify_receipt(self, classifier):
        """Test receipt classification."""
        text = """
        STORE RECEIPT
        Thank you for shopping!
        
        Transaction ID: TXN-123456
        Date: 2024-01-15
        
        Items:
        Coffee - $4.50
        Sandwich - $8.00
        
        Subtotal: $12.50
        Tax: $1.00
        Total: $13.50
        
        Paid by Credit Card
        """
        
        result = classifier.classify(text)
        
        assert result.document_type == DocumentType.RECEIPT
        assert result.confidence > 0.3

    def test_classify_medical(self, classifier):
        """Test medical document classification."""
        text = """
        PATIENT: John Doe
        Date of Birth: 01/15/1980
        
        PRESCRIPTION
        Rx: Amoxicillin 500mg
        Dosage: Take 1 tablet 3 times daily
        
        Diagnosis: Bacterial Infection
        
        Dr. Jane Smith, MD
        City Hospital
        """
        
        result = classifier.classify(text)
        
        assert result.document_type == DocumentType.MEDICAL
        assert "prescription" in [k.lower() for k in result.matched_keywords] or \
               "rx" in [k.lower() for k in result.matched_keywords]

    def test_classify_legal(self, classifier):
        """Test legal document classification."""
        text = """
        SERVICE AGREEMENT
        
        This Agreement is entered into as of January 1, 2024
        
        WHEREAS, the parties wish to establish terms and conditions;
        
        NOW, THEREFORE, in consideration of the mutual covenants hereby
        agreed upon, the parties agree as follows:
        
        1. Services. The Contractor shall provide services...
        
        WITNESS the execution hereof as of the day and year first written above.
        """
        
        result = classifier.classify(text)
        
        assert result.document_type == DocumentType.LEGAL
        assert result.confidence > 0.3

    def test_classify_financial(self, classifier):
        """Test financial document classification."""
        text = """
        BANK STATEMENT
        Account Holder: John Smith
        Account Number: ****1234
        Statement Period: January 1-31, 2024
        
        Opening Balance: $5,000.00
        
        Transactions:
        01/05 Deposit $1,000.00
        01/10 Withdrawal -$200.00
        01/15 Interest $5.00
        
        Closing Balance: $5,805.00
        """
        
        result = classifier.classify(text)
        
        assert result.document_type == DocumentType.FINANCIAL

    def test_classify_empty_text(self, classifier):
        """Test classification with empty text."""
        result = classifier.classify("")
        
        assert result.document_type == DocumentType.UNKNOWN
        assert result.confidence == 0.0

    def test_classify_whitespace_only(self, classifier):
        """Test classification with whitespace only."""
        result = classifier.classify("   \n\t  ")
        
        assert result.document_type == DocumentType.UNKNOWN

    def test_classify_unknown_content(self, classifier):
        """Test classification with unclassifiable content."""
        text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
        
        result = classifier.classify(text)
        
        # Should return UNKNOWN or low confidence
        assert result.confidence < 0.5 or result.document_type == DocumentType.UNKNOWN

    def test_classify_returns_all_scores(self, classifier):
        """Test that classification returns scores for all types."""
        text = "Invoice number 123, total amount due $500"
        
        result = classifier.classify(text)
        
        assert result.all_scores is not None
        assert len(result.all_scores) > 0

    def test_convenience_function(self):
        """Test classify_document convenience function."""
        result = classify_document("Invoice #123 Total: $500")
        
        assert result is not None
        assert hasattr(result, "document_type")
        assert hasattr(result, "confidence")


class TestClassificationEdgeCases:
    """Edge case tests for classification."""

    def test_mixed_document_types(self):
        """Test document with mixed keywords."""
        classifier = DocumentClassifier()
        
        # Document with both invoice and receipt keywords
        text = """
        Receipt/Invoice
        Transaction ID: 12345
        Invoice Number: INV-001
        Total: $100
        Thank you for your purchase!
        """
        
        result = classifier.classify(text)
        
        # Should classify as one type, not fail
        assert result.document_type in [DocumentType.INVOICE, DocumentType.RECEIPT]

    def test_case_insensitivity(self):
        """Test that classification is case-insensitive."""
        classifier = DocumentClassifier()
        
        text1 = "INVOICE NUMBER: 123"
        text2 = "invoice number: 123"
        text3 = "Invoice Number: 123"
        
        result1 = classifier.classify(text1)
        result2 = classifier.classify(text2)
        result3 = classifier.classify(text3)
        
        # All should classify similarly
        assert result1.document_type == result2.document_type == result3.document_type

    def test_special_characters(self):
        """Test classification with special characters."""
        classifier = DocumentClassifier()
        
        text = "Invoice #123!!! Total: $$$500.00*** @@@"
        
        result = classifier.classify(text)
        
        # Should still classify correctly
        assert result is not None
