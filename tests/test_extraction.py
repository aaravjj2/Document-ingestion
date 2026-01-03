"""Tests for LLM extraction service."""

import json
from unittest.mock import MagicMock

import pytest

from src.models.enums import DocumentType
from src.services.extraction import ExtractionService


class TestExtractionService:
    """Tests for ExtractionService class."""

    @pytest.fixture
    def mock_llm_response_invoice(self):
        """Mock LLM response for invoice extraction."""
        return json.dumps({
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-01-15",
            "vendor_name": "Acme Corp",
            "total_amount": 1234.56,
            "currency": "USD",
        })

    @pytest.fixture
    def mock_llm_response_medical(self):
        """Mock LLM response for medical document."""
        return json.dumps({
            "patient_name": "John Doe",
            "provider_name": "Dr. Smith",
            "diagnosis": ["Hypertension"],
            "medications": [{"name": "Lisinopril", "dosage": "10mg"}],
        })

    @pytest.fixture
    def mock_service(self):
        """Create a mock extraction service without invoking __init__."""
        service = object.__new__(ExtractionService)
        service.use_local_llm = False
        service.model_name = "test-model"
        service.llm_client = MagicMock()
        return service

    def test_extract_invoice_fields(self, mock_service, mock_llm_response_invoice):
        """Test invoice field extraction."""
        mock_service.llm_client.generate.return_value = mock_llm_response_invoice
        
        text = "Invoice #INV-2024-001 from Acme Corp dated 2024-01-15. Total: $1,234.56"
        result = mock_service.extract(text, DocumentType.INVOICE)
        
        assert result.get("invoice_number") == "INV-2024-001"
        assert result.get("vendor_name") == "Acme Corp"
        assert result.get("total_amount") == 1234.56

    def test_extract_medical_fields(self, mock_service, mock_llm_response_medical):
        """Test medical document field extraction."""
        mock_service.llm_client.generate.return_value = mock_llm_response_medical
        
        text = "Patient: John Doe. Diagnosis: Hypertension. Rx: Lisinopril 10mg"
        result = mock_service.extract(text, DocumentType.MEDICAL)
        
        assert result.get("patient_name") == "John Doe"
        assert "Hypertension" in result.get("diagnosis", [])

    def test_extract_empty_text(self, mock_service):
        """Test extraction with empty text."""
        result = mock_service.extract("", DocumentType.INVOICE)
        
        assert result == {}

    def test_extract_handles_invalid_json(self, mock_service):
        """Test handling of invalid JSON from LLM."""
        mock_service.llm_client.generate.return_value = "not valid json at all"
        
        result = mock_service.extract("some text", DocumentType.INVOICE)
        
        # Should handle gracefully, returning error or empty
        assert "error" in result or result == {}

    def test_extract_handles_markdown_wrapped_json(self, mock_service):
        """Test extraction when LLM wraps JSON in markdown."""
        json_content = '{"invoice_number": "123", "total_amount": 100}'
        markdown_response = f"```json\n{json_content}\n```"
        mock_service.llm_client.generate.return_value = markdown_response
        
        result = mock_service.extract("Invoice #123 Total: $100", DocumentType.INVOICE)
        
        assert result.get("invoice_number") == "123"

    def test_extract_with_confidence(self, mock_service):
        """Test extraction with confidence score."""
        mock_response = json.dumps({
            "invoice_number": "123",
            "invoice_date": "2024-01-01",
            "total_amount": 500,
        })
        mock_service.llm_client.generate.return_value = mock_response
        
        data, confidence = mock_service.extract_with_confidence(
            "Invoice content",
            DocumentType.INVOICE,
        )
        
        assert data is not None
        assert 0 <= confidence <= 1

    def test_parse_json_with_trailing_comma(self, mock_service):
        """Test JSON parsing handles trailing commas."""
        # JSON with trailing comma (invalid but common LLM output)
        bad_json = '{"field": "value",}'
        
        result = mock_service._parse_json_response(bad_json)
        
        assert result.get("field") == "value"

    def test_parse_json_with_single_quotes(self, mock_service):
        """Test JSON parsing handles single quotes."""
        # JSON with single quotes
        bad_json = "{'field': 'value'}"
        
        result = mock_service._parse_json_response(bad_json)
        
        assert result.get("field") == "value"


class TestExtractionSchemas:
    """Tests for extraction schema validation."""

    def test_invoice_schema_validation(self):
        """Test invoice schema validates correctly."""
        from src.services.extraction import InvoiceExtraction
        
        valid_data = {
            "invoice_number": "123",
            "total_amount": 100.50,
            "vendor_name": "Test Vendor",
        }
        
        invoice = InvoiceExtraction.model_validate(valid_data)
        
        assert invoice.invoice_number == "123"
        assert invoice.total_amount == 100.50

    def test_invoice_schema_handles_missing_fields(self):
        """Test invoice schema handles missing optional fields."""
        from src.services.extraction import InvoiceExtraction
        
        minimal_data = {"invoice_number": "123"}
        
        invoice = InvoiceExtraction.model_validate(minimal_data)
        
        assert invoice.invoice_number == "123"
        assert invoice.total_amount is None

    def test_medical_schema_validation(self):
        """Test medical schema validates correctly."""
        from src.services.extraction import MedicalExtraction
        
        valid_data = {
            "patient_name": "John Doe",
            "diagnosis": ["Cold", "Flu"],
            "medications": [{"name": "Aspirin", "dosage": "100mg"}],
        }
        
        medical = MedicalExtraction.model_validate(valid_data)
        
        assert medical.patient_name == "John Doe"
        assert len(medical.diagnosis) == 2
