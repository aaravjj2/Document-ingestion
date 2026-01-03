"""
API integration tests for the dashboard.
Tests that API endpoints work correctly and return expected data.
"""
import os

import pytest
import requests


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API_BASE = f"{BASE_URL}/api/v1"


class TestAPIEndpoints:
    """Test API endpoints used by the dashboard."""
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = requests.get(f"{API_BASE}/dashboard/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "components" in data
        assert data["status"] in ["healthy", "unhealthy"]
        
    def test_health_components(self):
        """Test health endpoint returns component status."""
        response = requests.get(f"{API_BASE}/dashboard/health")
        data = response.json()
        
        components = data["components"]
        assert "database" in components
        assert "celery" in components
        assert "workers" in components
        
        # Check component statuses
        assert components["database"] in ["healthy", "unhealthy"]
        assert components["celery"] in ["healthy", "unhealthy"]
        assert isinstance(components["workers"], list)
        
    def test_list_documents_endpoint(self):
        """Test documents list endpoint."""
        response = requests.get(f"{API_BASE}/documents")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "documents" in data
        assert "total" in data
        assert isinstance(data["documents"], list)
        assert isinstance(data["total"], int)
        
    def test_list_documents_structure(self):
        """Test document list returns proper structure."""
        response = requests.get(f"{API_BASE}/documents")
        data = response.json()
        
        if data["total"] > 0:
            doc = data["documents"][0]
            
            # Check required fields
            assert "id" in doc
            assert "filename" in doc
            assert "status" in doc
            assert "document_type" in doc
            assert "upload_timestamp" in doc
            
    def test_pagination_parameters(self):
        """Test pagination parameters work."""
        response = requests.get(f"{API_BASE}/documents?page=1&page_size=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "page" in data
        assert "page_size" in data
        assert data["page"] == 1
        assert data["page_size"] == 5


class TestAPIResponseFormats:
    """Test API response formats and data types."""
    
    def test_health_response_format(self):
        """Test health endpoint response format."""
        response = requests.get(f"{API_BASE}/dashboard/health")
        data = response.json()
        
        # Validate data types
        assert isinstance(data["status"], str)
        assert isinstance(data["components"], dict)
        assert isinstance(data["components"]["workers"], list)
        
    def test_documents_list_format(self):
        """Test documents list response format."""
        response = requests.get(f"{API_BASE}/documents")
        data = response.json()
        
        # Validate data types
        assert isinstance(data["documents"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)
        
    def test_document_status_values(self):
        """Test document status has valid values."""
        response = requests.get(f"{API_BASE}/documents")
        data = response.json()
        
        valid_statuses = ["pending", "processing", "completed", "failed"]
        
        for doc in data["documents"]:
            assert doc["status"] in valid_statuses, f"Invalid status: {doc['status']}"


class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_invalid_document_id(self):
        """Test getting invalid document ID returns error."""
        response = requests.get(f"{API_BASE}/documents/invalid-uuid-12345")
        
        # Should return 404 or 422
        assert response.status_code in [404, 422]
        
    def test_invalid_pagination(self):
        """Test invalid pagination parameters."""
        response = requests.get(f"{API_BASE}/documents?page=-1")
        
        # Should handle gracefully (either error or default)
        assert response.status_code in [200, 400, 422]


class TestAPIPerformance:
    """Test API performance and response times."""
    
    def test_health_endpoint_response_time(self):
        """Test health endpoint responds quickly."""
        import time
        
        start = time.time()
        response = requests.get(f"{API_BASE}/dashboard/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Health check too slow: {elapsed:.2f}s"
        
    def test_documents_list_response_time(self):
        """Test documents list responds in reasonable time."""
        import time
        
        start = time.time()
        response = requests.get(f"{API_BASE}/documents")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"Documents list too slow: {elapsed:.2f}s"


class TestCORSHeaders:
    """Test CORS headers are set correctly."""
    
    def test_cors_headers_present(self):
        """Test CORS headers are present in responses."""
        response = requests.get(f"{API_BASE}/dashboard/health")
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers or \
               "Access-Control-Allow-Origin" in response.headers
               
    def test_options_request(self):
        """Test OPTIONS request for CORS preflight."""
        response = requests.options(f"{API_BASE}/documents")
        
        # Should allow OPTIONS requests
        assert response.status_code in [200, 204]
