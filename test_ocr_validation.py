"""Comprehensive OCR testing and improvement validation."""
import asyncio
import sys
from pathlib import Path
import httpx
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

API_URL = "http://localhost:8000/api/v1"

async def test_single_document(client: httpx.AsyncClient, file_path: Path) -> dict:
    """Upload and process a single document."""
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "image/jpeg")}
            resp = await client.post(f"{API_URL}/documents/upload", files=files, timeout=30.0)
            
            if resp.status_code != 202:
                return {"error": f"Upload failed: {resp.status_code}"}
            
            resp_data = resp.json()
            doc_id = resp_data.get("job_id") or resp_data.get("document_id")
            
            # Poll for completion (max 2 minutes)
            for _ in range(60):
                await asyncio.sleep(2)
                resp = await client.get(f"{API_URL}/documents/{doc_id}", timeout=10.0)
                if resp.status_code != 200:
                    continue
                    
                doc = resp.json()
                status = doc["status"]
                
                if status in ["completed", "needs_review"]:
                    return {
                        "file": file_path.name,
                        "status": status,
                        "confidence": doc.get("ocr_confidence", 0.0),
                        "text_length": len(doc.get("raw_text", "")),
                        "text_preview": doc.get("raw_text", "")[:200] + "..." if doc.get("raw_text") else "",
                        "has_newlines": "\\n" in doc.get("raw_text", ""),
                        "line_count": doc.get("raw_text", "").count("\\n") + 1 if doc.get("raw_text") else 0
                    }
                elif status == "failed":
                    return {"error": f"Processing failed: {doc.get('error_log', 'Unknown error')}"}
            
            return {"error": "Timeout waiting for processing"}
            
    except Exception as e:
        return {"error": str(e)}

async def run_ocr_tests():
    """Run comprehensive OCR tests."""
    test_dir = Path("temp_test_downloads")
    if not test_dir.exists():
        logger.error("Test directory not found!")
        return
    
    test_files = sorted(test_dir.glob("*.jpg"))[:3]  # Test first 3 documents
    
    logger.info("=" * 80)
    logger.info("OCR ENHANCEMENT VALIDATION TEST")
    logger.info("=" * 80)
    logger.info(f"Testing {len(test_files)} documents\\n")
    
    async with httpx.AsyncClient() as client:
        results = []
        for i, file_path in enumerate(test_files, 1):
            logger.info(f"[{i}/{len(test_files)}] Processing: {file_path.name}")
            result = await test_single_document(client, file_path)
            results.append(result)
            
            if "error" in result:
                logger.info(f"  ❌ Error: {result['error']}")
            else:
                logger.info(f"  ✓ Status: {result['status']}")
                logger.info(f"  ✓ Confidence: {result['confidence']:.1%}")
                logger.info(f"  ✓ Text Length: {result['text_length']} chars")
                logger.info(f"  ✓ Lines Detected: {result['line_count']}")
                logger.info(f"  ✓ Formatting Preserved: {'Yes' if result['has_newlines'] else 'No'}")
                logger.info(f"\\n  Preview:\\n  {result['text_preview']}\\n")
    
    # Summary
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    successful = [r for r in results if "error" not in r]
    completed = [r for r in successful if r["status"] == "completed"]
    avg_confidence = sum(r["confidence"] for r in successful) / len(successful) if successful else 0
    formatted = [r for r in successful if r["has_newlines"]]
    
    logger.info(f"Total Tests: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Completed: {len(completed)}")
    logger.info(f"Average Confidence: {avg_confidence:.1%}")
    logger.info(f"Documents with Formatting: {len(formatted)}/{len(successful)}")
    
    if avg_confidence >= 0.5 and len(formatted) > 0:
        logger.info("\\n✅ OCR ENHANCEMENTS VALIDATED!")
    else:
        logger.info("\\n⚠️  OCR needs further improvement")

if __name__ == "__main__":
    asyncio.run(run_ocr_tests())
