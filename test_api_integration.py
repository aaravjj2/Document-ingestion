#!/usr/bin/env python3
"""
Full API Integration Test Script

Tests the complete API workflow with PostgreSQL and Redis.
"""

import asyncio
import sys
import time
from pathlib import Path
import subprocess
import signal
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import httpx

print("=" * 80)
print("DOCUMENT INGESTION API - FULL INTEGRATION TEST")
print("=" * 80)
print()

# Check if services are running
def check_service(url: str, name: str) -> bool:
    """Check if a service is accessible."""
    try:
        import requests
        response = requests.get(url, timeout=2)
        return response.status_code < 500
    except:
        return False

def create_test_invoice() -> BytesIO:
    """Create a test invoice image."""
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Invoice content
    draw.text((50, 50), "INVOICE", fill='black', font=font)
    draw.text((50, 100), "Invoice #: INV-2024-001", fill='black', font=font_small)
    draw.text((50, 140), "Date: 2024-01-15", fill='black', font=font_small)
    draw.text((50, 180), "Total Amount: $385.00", fill='black', font=font)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

# Start required services
print("Checking services...")
print()

postgres_running = check_service("http://localhost:5432", "PostgreSQL")
redis_running = check_service("http://localhost:6379", "Redis")

if not postgres_running:
    print("⚠️  PostgreSQL not running. Starting...")
    subprocess.run([
        "docker", "run", "-d",
        "--name", "doc_test_postgres",
        "-p", "5432:5432",
        "-e", "POSTGRES_PASSWORD=postgres",
        "-e", "POSTGRES_DB=document_ingestion",
        "postgres:14-alpine"
    ], capture_output=True)
    print("   Waiting for PostgreSQL to start...")
    time.sleep(5)

if not redis_running:
    print("⚠️  Redis not running. Starting...")
    subprocess.run([
        "docker", "run", "-d",
        "--name", "doc_test_redis",
        "-p", "6379:6379",
        "redis:7-alpine"
    ], capture_output=True)
    print("   Waiting for Redis to start...")
    time.sleep(2)

# Run migrations
print("🗄️  Running database migrations...")
result = subprocess.run(
    ["alembic", "upgrade", "head"],
    capture_output=True,
    text=True
)
if result.returncode != 0:
    print(f"   Warning: Migration output: {result.stderr[:200]}")

# Start API server
print("🚀 Starting API server...")
api_process = subprocess.Popen(
    ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Wait for API to be ready
print("   Waiting for API to be ready...")
max_retries = 30
for i in range(max_retries):
    try:
        import requests
        response = requests.get("http://localhost:8000/api/v1/dashboard/health", timeout=1)
        if response.status_code == 200:
            print("   ✓ API is ready!")
            break
    except:
        pass
    time.sleep(1)
    if i % 5 == 0:
        print(f"   ... still waiting ({i}/{max_retries})")
else:
    print("   ✗ API failed to start")
    api_process.terminate()
    sys.exit(1)

print()
print("=" * 80)
print("RUNNING API TESTS")
print("=" * 80)
print()

try:
    import requests
    
    # Test 1: Health Check
    print("TEST 1: Health Check")
    response = requests.get("http://localhost:8000/api/v1/dashboard/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"
    health_data = response.json()
    print(f"  ✓ Status: {health_data.get('status')}")
    print(f"  ✓ Database: {health_data.get('database')}")
    print(f"  ✓ Redis: {health_data.get('redis')}")
    print()
    
    # Test 2: Dashboard Metrics
    print("TEST 2: Dashboard Metrics")
    response = requests.get("http://localhost:8000/api/v1/dashboard/metrics")
    assert response.status_code == 200
    metrics = response.json()
    print(f"  ✓ Total documents: {metrics.get('total_documents', 0)}")
    print(f"  ✓ Pending: {metrics.get('pending', 0)}")
    print(f"  ✓ Processing: {metrics.get('processing', 0)}")
    print(f"  ✓ Completed: {metrics.get('completed', 0)}")
    print()
    
    # Test 3: Upload Document
    print("TEST 3: Upload Document")
    test_image = create_test_invoice()
    files = {'file': ('test_invoice.png', test_image, 'image/png')}
    response = requests.post("http://localhost:8000/api/v1/documents/upload", files=files)
    assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
    upload_result = response.json()
    document_id = upload_result.get('document_id')
    print(f"  ✓ Document uploaded: {document_id}")
    print(f"  ✓ Job ID: {upload_result.get('job_id')}")
    print(f"  ✓ Status: {upload_result.get('status')}")
    print()
    
    # Test 4: Get Document Status
    print("TEST 4: Get Document Status")
    time.sleep(2)  # Give it time to process
    response = requests.get(f"http://localhost:8000/api/v1/documents/{document_id}/status")
    assert response.status_code == 200
    status = response.json()
    print(f"  ✓ Status: {status.get('status')}")
    print(f"  ✓ Filename: {status.get('filename')}")
    print()
    
    # Test 5: List Documents
    print("TEST 5: List Documents")
    response = requests.get("http://localhost:8000/api/v1/documents")
    assert response.status_code == 200
    docs = response.json()
    print(f"  ✓ Found {len(docs)} documents")
    if docs:
        print(f"  ✓ First document: {docs[0].get('filename')}")
    print()
    
    # Test 6: Search (basic)
    print("TEST 6: Search Functionality")
    response = requests.get("http://localhost:8000/api/v1/search?q=invoice")
    assert response.status_code == 200
    search_results = response.json()
    print(f"  ✓ Search completed: {search_results.get('total', 0)} results")
    print()
    
    print("=" * 80)
    print("✅ ALL API TESTS PASSED!")
    print("=" * 80)
    print()
    
except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Cleanup
    print()
    print("Cleaning up...")
    
    # Stop API
    print("  → Stopping API server...")
    api_process.terminate()
    api_process.wait(timeout=5)
    
    # Stop Docker containers
    print("  → Stopping test containers...")
    subprocess.run(["docker", "stop", "doc_test_postgres"], capture_output=True)
    subprocess.run(["docker", "rm", "doc_test_postgres"], capture_output=True)
    subprocess.run(["docker", "stop", "doc_test_redis"], capture_output=True)
    subprocess.run(["docker", "rm", "doc_test_redis"], capture_output=True)
    
    print("  ✓ Cleanup complete")
    print()

print("=" * 80)
print("INTEGRATION TEST COMPLETE")
print("=" * 80)
