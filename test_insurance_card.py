#!/usr/bin/env python3
"""Test insurance card OCR and extraction."""
import requests
import time
import os
import json

API_BASE_URL = "http://localhost:8001/api/v1"
TEST_FILE = "insurance_card_test.png"

def test_insurance_card():
    print(f"Testing insurance card OCR and extraction...")
    
    if not os.path.exists(TEST_FILE):
        print(f"Error: {TEST_FILE} not found")
        return
    
    # Upload
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (TEST_FILE, f, 'image/png')}
        resp = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
    
    if resp.status_code not in [200, 202]:
        print(f"Upload failed: {resp.status_code} {resp.text}")
        return
    
    doc_id = resp.json().get('job_id')
    print(f"Uploaded: {doc_id}")
    
    # Poll
    for i in range(20):
        time.sleep(3)
        r = requests.get(f"{API_BASE_URL}/documents/{doc_id}")
        data = r.json()
        status = data.get('status')
        print(f"Status: {status}")
        
        if status in ['completed', 'failed', 'needs_review']:
            print(f"\n=== Results ===")
            print(f"Type: {data.get('document_type')}")
            print(f"OCR Confidence: {(data.get('ocr_confidence') or 0) * 100:.1f}%")
            print(f"Classification Confidence: {(data.get('classification_confidence') or 0) * 100:.1f}%")
            print(f"\nRaw Text:")
            print(data.get('raw_text', ''))
            print(f"\n=== Extracted Data ===")
            print(json.dumps(data.get('extracted_data'), indent=2))
            return data
    
    print("Timeout")
    return None

if __name__ == "__main__":
    test_insurance_card()
