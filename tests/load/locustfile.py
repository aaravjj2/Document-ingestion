"""Locust load testing file for Document Ingestion Service."""

import io
import random
from locust import HttpUser, between, task
from PIL import Image, ImageDraw


class DocumentIngestionUser(HttpUser):
    """
    Simulated user for load testing the Document Ingestion Service.
    
    Run with:
        locust -f tests/load/locustfile.py --host=http://localhost:8000
    """
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a simulated user starts."""
        # Generate test documents for this user
        self.test_documents = []

    def generate_test_image(self) -> bytes:
        """Generate a random test image."""
        # Create a simple image with random content
        width, height = 800, 600
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)
        
        # Add some random "text" lines
        for y in range(50, height - 50, 30):
            line_width = random.randint(200, 500)
            draw.line([(50, y), (50 + line_width, y)], fill="black", width=2)
        
        # Add a title area
        draw.rectangle([50, 20, 300, 45], fill="black")
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()

    def generate_test_pdf(self) -> bytes:
        """Generate a simple test PDF."""
        # Simple PDF content (minimal valid PDF)
        # In production, use reportlab for proper PDFs
        pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer << /Size 4 /Root 1 0 R >>
startxref
193
%%EOF"""
        return pdf_content

    @task(10)
    def upload_image(self):
        """Upload a test image document."""
        image_data = self.generate_test_image()
        
        files = {
            "file": (
                f"test_image_{random.randint(1000, 9999)}.png",
                io.BytesIO(image_data),
                "image/png",
            )
        }
        
        with self.client.post(
            "/api/v1/documents/upload",
            files=files,
            catch_response=True,
        ) as response:
            if response.status_code == 202:
                data = response.json()
                self.test_documents.append(data.get("job_id"))
                response.success()
            else:
                response.failure(f"Upload failed: {response.status_code}")

    @task(5)
    def upload_pdf(self):
        """Upload a test PDF document."""
        pdf_data = self.generate_test_pdf()
        
        files = {
            "file": (
                f"test_doc_{random.randint(1000, 9999)}.pdf",
                io.BytesIO(pdf_data),
                "application/pdf",
            )
        }
        
        with self.client.post(
            "/api/v1/documents/upload",
            files=files,
            catch_response=True,
        ) as response:
            if response.status_code == 202:
                data = response.json()
                self.test_documents.append(data.get("job_id"))
                response.success()
            else:
                response.failure(f"Upload failed: {response.status_code}")

    @task(15)
    def check_document_status(self):
        """Check status of a previously uploaded document."""
        if not self.test_documents:
            return
        
        doc_id = random.choice(self.test_documents)
        
        with self.client.get(
            f"/api/v1/documents/{doc_id}/status",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status check failed: {response.status_code}")

    @task(10)
    def list_documents(self):
        """List documents with pagination."""
        page = random.randint(1, 5)
        
        with self.client.get(
            f"/api/v1/documents?page={page}&page_size=20",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"List failed: {response.status_code}")

    @task(8)
    def search_documents(self):
        """Search for documents."""
        queries = ["invoice", "receipt", "total", "date", "amount"]
        query = random.choice(queries)
        
        with self.client.get(
            f"/api/v1/search?q={query}",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")

    @task(5)
    def get_dashboard_metrics(self):
        """Fetch dashboard metrics."""
        with self.client.get(
            "/api/v1/dashboard/metrics",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.status_code}")

    @task(3)
    def get_queue_status(self):
        """Check processing queue status."""
        with self.client.get(
            "/api/v1/dashboard/queue",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Queue status failed: {response.status_code}")

    @task(2)
    def health_check(self):
        """Perform health check."""
        with self.client.get(
            "/api/v1/dashboard/health",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")


class HeavyUploadUser(HttpUser):
    """
    User that focuses on heavy upload scenarios.
    
    Use this to stress test the upload and processing pipeline.
    """
    
    wait_time = between(0.5, 1)  # More aggressive timing

    def generate_large_image(self, size_mb: float = 2.0) -> bytes:
        """Generate a larger test image."""
        # Calculate dimensions to approximate target size
        # PNG compression varies, so this is approximate
        pixels_per_mb = 350000  # Rough estimate
        total_pixels = int(pixels_per_mb * size_mb)
        width = int((total_pixels * 4 / 3) ** 0.5)
        height = int(width * 3 / 4)
        
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)
        
        # Add content
        for y in range(0, height, 20):
            draw.line([(0, y), (width, y)], fill="black", width=1)
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()

    @task
    def upload_large_document(self):
        """Upload a larger document to stress test."""
        image_data = self.generate_large_image(size_mb=2.0)
        
        files = {
            "file": (
                f"large_doc_{random.randint(1000, 9999)}.png",
                io.BytesIO(image_data),
                "image/png",
            )
        }
        
        with self.client.post(
            "/api/v1/documents/upload",
            files=files,
            catch_response=True,
        ) as response:
            if response.status_code == 202:
                response.success()
            else:
                response.failure(f"Large upload failed: {response.status_code}")
