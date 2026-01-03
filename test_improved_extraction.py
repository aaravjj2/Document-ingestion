#!/usr/bin/env python3
"""Test improved insurance card extraction."""
import requests
import time
import os
import json

API_BASE_URL = "http://localhost:8001/api/v1"
TEST_FILE = "cigna_card_v2.png"

def test_extraction():
    print(f"Testing improved extraction with {TEST_FILE}...")
    
    if not os.path.exists(TEST_FILE):
        print(f"Error: {TEST_FILE} not found")
        return None
    
    # Upload
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (TEST_FILE, f, 'image/png')}
        resp = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
    
    if resp.status_code not in [200, 202]:
        print(f"Upload failed: {resp.status_code} {resp.text}")
        return None
    
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
            print(f"\n{'='*50}")
            print(f"DOCUMENT TYPE: {data.get('document_type')}")
            print(f"OCR Confidence: {(data.get('ocr_confidence') or 0) * 100:.1f}%")
            print(f"Classification Confidence: {(data.get('classification_confidence') or 0) * 100:.1f}%")
            print(f"{'='*50}")
            
            extracted = data.get('extracted_data', {})
            if extracted:
                print("\n📋 EXTRACTED DATA:")
                print("-" * 40)
                for field, value in extracted.items():
                    if value is not None:
                        # Format label nicely
                        label = field.replace("_", " ").title()
                        print(f"  {label:25} : {value}")
                print("-" * 40)
            else:
                print("\nNo extracted data")
            
            return data
    
    print("Timeout")
    return None

if __name__ == "__main__":
    test_extraction()
