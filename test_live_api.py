#!/usr/bin/env python3
import requests
import time
import sys
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os # Added for file existence check

# Configuration
API_BASE_URL = "http://localhost:8001/api/v1"
TEST_PDF_PATH = "test_document.pdf"
TEST_IMG_PATH = "test_invoice.png"

def create_test_invoice() -> BytesIO:
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except:
        font = None
    
    draw.text((50, 50), "INVOICE", fill='black')
    draw.text((50, 100), "Invoice #: INV-LIVE-002", fill='black')
    draw.text((50, 140), "Date: 2024-12-31", fill='black')
    draw.text((50, 180), "Total Amount: $1234.56", fill='black')
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

def test_api():
    print(f"Testing API at {API_BASE_URL}...")
    
    # Check health
    try:
        resp = requests.get(f"{API_BASE_URL}/dashboard/health")
        print(f"Health Check: {resp.status_code} - {resp.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    print("\nUploading test document...")
    
    files = {}
    if os.path.exists(TEST_IMG_PATH):
        print(f"Using existing test image: {TEST_IMG_PATH}")
        files = {'file': ('invoice.png', open(TEST_IMG_PATH, 'rb'), 'image/png')}
    else:
        print("Creating synthetic test PDF...")
        pdf_data = create_test_invoice()
        files = {'file': ('test_invoice.pdf', pdf_data, 'application/pdf')}

    resp = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
    
    if resp.status_code not in [200, 202]:
        print(f"Upload Failed: {resp.status_code} - {resp.text}")
        return
    
    upload_data = resp.json()
    # In this app, job_id in response is actually the document_id
    doc_id = upload_data.get('job_id')
    print(f"Upload Success ({resp.status_code}): Document ID (from job_id) = {doc_id}")

    if not doc_id:
        print("Error: No job_id/document_id returned")
        return

    # 3. Poll for status
    print(f"\nPolling for processing status for document {doc_id}...")
    max_retries = 20
    for i in range(max_retries):
        resp = requests.get(f"{API_BASE_URL}/documents/{doc_id}")
        if resp.status_code == 200:
            doc_data = resp.json()
            status = doc_data.get('status')
            print(f"Attempt {i+1}: Status = {status}")
            if status in ['completed', 'failed', 'needs_review']:
                if status == 'completed':
                    print("✓ Document processing completed successfully!")
                elif status == 'needs_review':
                    print("⚠ Document processed but needs review (low confidence).")
                else:
                    print(f"✗ Document processing failed. Error log: {doc_data.get('error_log')}")
                break
        else:
            print(f"Attempt {i+1}: Failed to get details: {resp.status_code}")
        time.sleep(5)
    else:
        print("Polling timed out.")

    # 4. Final verification
    resp = requests.get(f"{API_BASE_URL}/documents/{doc_id}")
    if resp.status_code == 200:
        final_data = resp.json()
        print(f"\nFinal Document Data:")
        print(f"  Type: {final_data.get('document_type')}")
        raw_text = final_data.get('raw_text') or ""
        print(f"  Text Snippet: {raw_text[:100]}...")
    else:
        print(f"Final check failed: {resp.status_code}")

if __name__ == "__main__":
    test_api()
