#!/usr/bin/env python3
"""Test extraction on multiple identity documents."""
import requests
import time
import os
import json

API_BASE_URL = "http://localhost:8001/api/v1"

def test_document(filepath):
    """Upload and test a single document."""
    print(f"\n{'='*60}")
    print(f"TESTING: {filepath}")
    print('='*60)
    
    if not os.path.exists(filepath):
        print(f"Error: File not found")
        return None
    
    # Upload
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f, 'image/png')}
        resp = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
    
    if resp.status_code not in [200, 202]:
        print(f"Upload failed: {resp.status_code}")
        return None
    
    doc_id = resp.json().get('job_id')
    print(f"Document ID: {doc_id}")
    
    # Poll
    for i in range(20):
        time.sleep(3)
        r = requests.get(f"{API_BASE_URL}/documents/{doc_id}")
        data = r.json()
        status = data.get('status')
        
        if status in ['completed', 'failed', 'needs_review']:
            print(f"\nStatus: {status}")
            print(f"Type: {data.get('document_type')}")
            print(f"OCR Confidence: {(data.get('ocr_confidence') or 0) * 100:.1f}%")
            print(f"Classification: {(data.get('classification_confidence') or 0) * 100:.1f}%")
            
            extracted = data.get('extracted_data', {})
            if extracted:
                print("\n📋 EXTRACTED FIELDS:")
                print("-" * 40)
                for field, value in extracted.items():
                    if value is not None:
                        label = field.replace("_", " ").title()
                        print(f"  {label:25} : {value}")
            else:
                print("\nNo extracted data")
            
            return data
    
    print("Timeout")
    return None


def main():
    # Test all sample documents
    import glob
    documents = sorted(glob.glob("sample_*.png") + glob.glob("sample_*.webp"))
    
    if not documents:
        print("No sample documents found!")
        return
    
    results = {}
    for doc in documents:
        result = test_document(doc)
        if result:
            doc_type = result.get('document_type', 'unknown')
            fields = len([v for v in result.get('extracted_data', {}).values() if v])
            results[doc] = f"{doc_type} ({fields} fields)"
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for doc, info in results.items():
        print(f"  {doc}: {info}")


if __name__ == "__main__":
    main()
