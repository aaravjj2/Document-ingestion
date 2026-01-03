"""Tests for the document upload API."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client with proper async handling."""
    # Use context manager to properly handle event loop lifecycle
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


class TestUploadEndpoint:
    """Tests for POST /upload endpoint."""

    def test_upload_valid_pdf(self, client, temp_dir: Path):
        """Test uploading a valid PDF file."""
        # Create a simple PDF-like file
        pdf_content = b"%PDF-1.4 test content"
        
        with patch("src.api.documents.process_document") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-123")
            
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            )
        
        # Should return 202 Accepted (queued for processing)
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["status"] == "queued"
        assert "job_id" in data

    def test_upload_valid_image(self, client, sample_image: Path):
        """Test uploading a valid image file."""
        with open(sample_image, "rb") as f:
            image_content = f.read()
        
        with patch("src.api.documents.process_document") as mock_task:
            mock_task.delay.return_value = MagicMock(id="task-123")
            
            response = client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.png", io.BytesIO(image_content), "image/png")},
            )
        
        assert response.status_code == status.HTTP_202_ACCEPTED

    def test_upload_invalid_file_type(self, client):
        """Test that .exe files are rejected."""
        exe_content = b"MZ executable content"
        
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("malware.exe", io.BytesIO(exe_content), "application/x-msdownload")},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not allowed" in response.json()["detail"].lower()

    def test_upload_invalid_extension_txt(self, client):
        """Test that .txt files are rejected."""
        txt_content = b"Some text content"
        
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("document.txt", io.BytesIO(txt_content), "text/plain")},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_no_file(self, client):
        """Test upload without file."""
        response = client.post("/api/v1/documents/upload")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_upload_empty_filename(self, client):
        """Test upload with empty filename."""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("", io.BytesIO(b"content"), "application/pdf")},
        )
        
        # FastAPI may return 400 or 422 for invalid filename
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]


class TestDocumentEndpoints:
    """Tests for document CRUD endpoints."""

    def test_get_document_not_found(self, client):
        """Test getting a non-existent document."""
        response = client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_documents_empty(self, client):
        """Test listing documents when empty."""
        response = client.get("/api/v1/documents")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "documents" in data
        assert "total" in data

    def test_list_documents_with_filters(self, client):
        """Test listing documents with status filter."""
        response = client.get("/api/v1/documents?status=completed")
        
        assert response.status_code == status.HTTP_200_OK

    def test_list_documents_pagination(self, client):
        """Test document list pagination."""
        response = client.get("/api/v1/documents?page=1&page_size=10")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10


class TestSearchEndpoints:
    """Tests for search endpoints."""

    def test_search_empty_query(self, client):
        """Test search with empty query."""
        response = client.get("/api/v1/search?q=")
        
        # Should fail validation (min_length=1)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_valid_query(self, client):
        """Test search with valid query."""
        response = client.get("/api/v1/search?q=invoice")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert "total" in data


class TestDashboardEndpoints:
    """Tests for dashboard endpoints."""

    def test_get_metrics(self, client):
        """Test getting dashboard metrics."""
        response = client.get("/api/v1/dashboard/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_documents" in data
        assert "documents_processed" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/dashboard/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "components" in data
