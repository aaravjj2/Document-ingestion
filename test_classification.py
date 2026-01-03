
import requests
import time
import sys
import os

API_BASE_URL = "http://localhost:8001/api/v1"
BLANK_IMG_PATH = "blank_test_doc.png"
HANDWRITTEN_IMG_PATH = "test_live_invoice_2.png" # Using previous name but will be treated as handwritten simulation

def test_document(name, filepath, expect_fail=False):
    print(f"\n--- Testing {name} ---")
    if not os.path.exists(filepath):
        print(f"Skipping {name}: File not found {filepath}")
        return

    files = {'file': (os.path.basename(filepath), open(filepath, 'rb'), 'image/png')}
    resp = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
    
    if resp.status_code not in [200, 202]:
        print(f"Upload Failed: {resp.status_code}")
        return
    
    doc_id = resp.json().get('job_id')
    print(f"Uploaded {doc_id}. Polling...")

    for i in range(15):
        time.sleep(2)
        r = requests.get(f"{API_BASE_URL}/documents/{doc_id}")
        status = r.json().get('status')
        print(f"Status: {status}")
        
        if status in ['completed', 'failed', 'needs_review']:
            if expect_fail:
                if status == 'failed':
                     print("SUCCESS: Document failed as expected.")
                else:
                     print(f"FAILURE: Expected failed, got {status}")
            else:
                if status in ['completed', 'needs_review']:
                    print(f"SUCCESS: Document finished with status {status}")
                    print(f"Type: {r.json().get('document_type')}")
                    print(f"Confidence: {r.json().get('classification_confidence')}")
                else:
                    print(f"FAILURE: Unexpected status {status}")
                    print(r.json().get('error_log'))
            return

    print("TIMEOUT")

if __name__ == "__main__":
    test_document("Blank Document", BLANK_IMG_PATH, expect_fail=True)
    # Note: We are reusing the 'test_invoice.png' as a proxy for a valid document to ensure no regression
    # Ideally we'd have a real handwritten one, but consistent with instructions we test logic.
    test_document("Valid Document (Regression)", "test_invoice.png", expect_fail=False)
