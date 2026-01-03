import asyncio
import os
import sys
import time
from pathlib import Path
import httpx
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

API_URL = "http://localhost:8000/api/v1"
TEMP_DIR = Path("temp_test_downloads")

HANDWRITTEN_URLS = [
    "https://upload.wikimedia.org/wikipedia/commons/7/7f/Handwritten_letter_from_Kevin_Trudeau.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/18/Receipt_from_Josiah_Wedgwood_1770.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/8/8c/John_Green_Receipt_July_3,_1794_-_NARA_-_192965.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/7/70/Elijah_Adams_Receipt_August_28,_1792_-_NARA_-_192875.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/3/39/Benjamin_Russell_Receipt_March_18,_1786_-_NARA_-_192861.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/11/Robert_Treat_Paine_Receipt_March_13,_1787_-_NARA_-_193010.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/f/fd/Receipt_for_Wine_and_Kegs_Purchased_by_Meriwether_Lewis_for_the_Expedition_to_the_West_-_NARA_-_300351.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/f/fd/J%C3%B3zef_Che%C5%82mo%C5%84ski_list_1859.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/6/6a/Samuel_Fletcher_Receipt_September_18,_1769_-_NARA_-_193023.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/b/b4/Thomas_Crafts_Receipt_January,_1792_-_NARA_-_193036.jpg"
]

SAMPLE_URLS = [
    {
        "url": url,
        "name": f"handwritten_{i}.jpg",
        "type": "handwritten"
    } for i, url in enumerate(HANDWRITTEN_URLS, 1)
]

async def download_file(client: httpx.AsyncClient, url: str, path: Path):
    logger.info(f"Downloading {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        resp = await client.get(url, headers=headers, follow_redirects=True)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        logger.info(f"Saved to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

async def upload_document(client: httpx.AsyncClient, file_path: Path):
    logger.info(f"Uploading {file_path.name}...")
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "image/jpeg")}
            resp = await client.post(f"{API_URL}/documents/upload", files=files)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to upload {file_path.name}: {e}")
        return None

async def poll_status(client: httpx.AsyncClient, doc_id: str):
    logger.info(f"Polling status for {doc_id}...")
    start_time = time.time()
    while time.time() - start_time < 120:  # 2 minute timeout
        try:
            resp = await client.get(f"{API_URL}/documents/{doc_id}")
            resp.raise_for_status()
            data = resp.json()
            status = data["status"]
            
            if status in ["completed", "failed", "needs_review"]:
                return data
            
            logger.info(f"Status: {status}. Waiting...")
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Error polling {doc_id}: {e}")
            await asyncio.sleep(2)
    
    logger.error(f"Timeout polling {doc_id}")
    return None

async def cleanup_invalid_docs(client: httpx.AsyncClient):
    logger.info("Cleaning up invalid documents...")
    try:
        resp = await client.get(f"{API_URL}/documents")
        resp.raise_for_status()
        data = resp.json()
        documents = data.get("documents", [])
        
        for doc in documents:
            if doc["status"] == "failed":
                logger.info(f"Deleting failed document {doc['id']}...")
                try:
                    del_resp = await client.delete(f"{API_URL}/documents/{doc['id']}")
                    if del_resp.status_code == 200:
                        logger.info(f"Deleted {doc['id']}")
                    else:
                        logger.warning(f"Could not delete {doc['id']}: {del_resp.status_code}")
                except Exception as e:
                    logger.warning(f"Delete failed for {doc['id']}: {e}")
                    
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

async def run_test():
    TEMP_DIR.mkdir(exist_ok=True)
    
    async with httpx.AsyncClient() as client:
        # 0. Cleanup first
        await cleanup_invalid_docs(client)
        
        # 1. Download files
        downloaded_files = []
        for item in SAMPLE_URLS:
            file_path = TEMP_DIR / item["name"]
            if await download_file(client, item["url"], file_path):
                downloaded_files.append((file_path, item["type"]))
            await asyncio.sleep(2) # Be nice to the server
        
        if not downloaded_files:
            logger.error("No files downloaded!")
            return

        # 2. Upload and Poll
        results = []
        for file_path, doc_type in downloaded_files:
            upload_resp = await upload_document(client, file_path)
            if upload_resp:
                doc_id = upload_resp.get("job_id") or upload_resp.get("id")
                if not doc_id:
                    logger.error(f"No ID in response: {upload_resp}")
                    results.append({
                        "file": file_path.name,
                        "status": "upload_failed",
                        "type": "unknown",
                        "ocr_conf": 0
                    })
                    continue

                final_state = await poll_status(client, doc_id)
                
                if final_state:
                    ocr_conf = final_state.get("ocr_confidence", 0)
                    results.append({
                        "file": file_path.name,
                        "status": final_state["status"],
                        "type": final_state.get("document_type", "unknown"),
                        "ocr_conf": ocr_conf
                    })
                else:
                    results.append({
                        "file": file_path.name,
                        "status": "timeout",
                        "type": "unknown",
                        "ocr_conf": 0
                    })
            else:
                results.append({
                    "file": file_path.name,
                    "status": "upload_failed",
                    "type": "unknown",
                    "ocr_conf": 0
                })

        # 3. Report
        print("\n" + "="*50)
        print("TEST RESULTS")
        print("="*50)
        success_count = 0
        for res in results:
            icon = "✅" if res["status"] == "completed" else "❌"
            if res["status"] == "completed":
                success_count += 1
            print(f"{icon} File: {res['file']}")
            print(f"   Status: {res['status']}")
            print(f"   Type: {res['type']}")
            print(f"   OCR Conf: {res['ocr_conf']}")
            print("-" * 30)
        
        print(f"\nSuccess Rate: {success_count}/{len(results)}")
        if success_count == len(results):
            print("🎉 ALL TESTS PASSED!")
        else:
            print("⚠️ SOME TESTS FAILED")

if __name__ == "__main__":
    asyncio.run(run_test())
