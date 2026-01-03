🗺️ Master Roadmap: Intelligent Document Ingestion Service
📚 Phase 0: Reference & Research (The "Library")
Before writing code, clone these repositories to understand how state-of-the-art systems solve specific problems. Do not copy blindly; use them as reference patterns.

1. The Core Engines (OCR & Handwriting)
Repo: https://github.com/PaddlePaddle/PaddleOCR

Purpose: The primary OCR engine. Excellent at detecting text in wild layouts and has specific models for handwriting.

Key File to Check: Look at their ppstructure folder to see how they detect tables vs. text blocks.

Repo: https://github.com/microsoft/unilm/tree/master/trocr

Purpose: TrOCR (Transformer OCR). If Paddle fails on cursive/messy handwriting, this is the fallback. It reads text line-by-line as a language translation task.

Repo: https://github.com/datalab-to/surya

Purpose: Document Layout Analysis. Use this to determine reading order (e.g., distinguishing a sidebar from the main body).

2. The Pipeline Wrappers (ETL Logic)
Repo: https://github.com/Unstructured-IO/unstructured

Purpose: The industry standard for cleaning text. Look at how they handle "chunking" text for storage.

Repo: https://github.com/docling-project/docling

Purpose: Study their PDF parsing logic. They excel at reconstructing the original structure of a document.

3. Testing & Augmentation
Repo: https://github.com/sparkfish/augraphy

Purpose: Crucial for testing. It artificially adds "coffee stains," "folds," and "bad lighting" to clean documents so you can stress-test your OCR.

🏗️ Phase 1: Infrastructure & Ingestion (Weeks 1-2)
Goal: Build the "pipes" that move files from the user to the worker.

1.1 Backend Setup (FastAPI)
Action: Initialize a FastAPI project.

Component: POST /upload endpoint.

Logic: Validate file type (PDF/PNG/JPG/TIFF).

Logic: Assign a unique request_id (UUID).

Storage: Save the raw file to a local temp/ folder (or MinIO/S3 if cloud-ready).

Response: Return {"status": "queued", "job_id": "xyz"} immediately. Don't process it yet.

1.2 Async Worker (Celery + Redis)
Action: Spin up a Redis container (docker run -d -p 6379:6379 redis).

Component: Celery Worker.

Create a task process_document(file_path, job_id).

Ensure the worker runs in a separate process/container from the API.

1.3 Database Schema (PostgreSQL)
Action: Create the documents table.

id (UUID, Primary Key)

filename (String)

status (Enum: PENDING, PROCESSING, COMPLETED, FAILED)

upload_timestamp (DateTime)

error_log (Text, for debugging failures)

👁️ Phase 2: The Vision Pipeline (Weeks 3-4)
Goal: Turn messy images into clean images, then into raw text.

2.1 Image Pre-processing (The "Cleaning Crew")
Before OCR, you must clean the image. This increases accuracy by ~30%.

Tool: OpenCV (cv2).

Pipeline Steps:

Grayscale: Convert color to B/W.

Denoise: Apply Gaussian Blur to remove grain/speckles.

Binarize: Use "Adaptive Thresholding" to make text pure black and background pure white.

Deskew: Detect the angle of the text and rotate the image so it is perfectly straight.

2.2 OCR Integration (PaddleOCR)
Action: Implement the OCRService class.

Logic:

Run PaddleOCR on the cleaned image.

Output: You will get a list of bounding boxes and text: [ [[x1,y1], [x2,y2]], "text", confidence ].

Confidence Check: If the average confidence is < 60%, flag the document as NEEDS_REVIEW in the database.

🧠 Phase 3: Intelligence & Extraction (Weeks 5-6)
Goal: Turn raw text strings into structured JSON.

3.1 Classification
Task: Determine what the document is.

Method: Keyword counting (simple) or Zero-shot classification (AI).

If text contains "Invoice" AND "Total" -> Type: INVOICE.

If text contains "Prescription" AND "Rx" -> Type: MEDICAL.

3.2 Field Extraction (LLM Integration)
Action: Use a local LLM (like Llama-3) or an API (OpenAI gpt-4o-mini).

Prompt Strategy:

"You are a data extraction assistant. Here is raw text from an OCR scan: {RAW_TEXT}. Extract the following fields: Date, Total Amount, Vendor Name. Return ONLY JSON."

Validation: Use Pydantic to validate that the JSON returned by the LLM is actually valid (e.g., ensure "Total Amount" is a number, not text).

💾 Phase 4: Storage & Search (Week 7)
Goal: Save the data so it can be found later.

4.1 Structured Storage
Database: Update PostgreSQL.

Table: extracted_metadata

document_id (FK)

document_type (String)

data (JSONB column - allows flexible queries like data->>'total' > 500).

4.2 Full-Text Search
Action: Store the full raw OCR text in a TSVECTOR column in Postgres.

Benefit: Allows you to perform high-speed text searches (e.g., "Find documents containing the word 'Lithium'").

📊 Phase 5: Frontend Dashboard (Week 8)
Goal: Visual proof that it works.

5.1 The "Monitor"
Stack: Next.js or Streamlit (for speed).

Metrics to Display:

Total Documents Processed.

Average Confidence Score.

Queue Depth (how many docs are waiting).

5.2 The "Review Station"
Feature: A page listing documents with status=NEEDS_REVIEW.

UI: Split screen.

Left: The original image (with bounding boxes drawn over detected text).

Right: The extracted JSON fields (editable inputs).

Action: When the user clicks "Save", update the database and train the system (optional future step).

🧪 Phase 6: Testing & QA Strategy (Week 9)
How to prove it works.

6.1 Unit Testing (Code Logic)
Tool: pytest.

Tests:

Test that PDF uploads are accepted but .exe files are rejected.

Test that the JSON extractor handles missing fields gracefully (returns null instead of crashing).

6.2 "Augraphy" Stress Testing (Robustness)
Concept: Use the augraphy library to generate test data.

Workflow:

Take a clean digital PDF.

Use Augraphy to apply a "crumpled paper" effect and a "coffee stain."

Run this "dirty" file through your pipeline.

Pass Condition: The extracted data matches the original clean PDF data.

6.3 Accuracy Benchmarking (The Metric)
Metric: CER (Character Error Rate) and WER (Word Error Rate).

Tool: Use jiwer (Python library).

Calculation: Compare the OCR output against a "Ground Truth" (manually typed version of the document).

Goal: CER < 5% for printed text, CER < 15% for handwriting.

6.4 Load Testing
Tool: Locust.

Scenario: Simulate 50 concurrent users uploading 5MB PDFs simultaneously.

Monitor: Watch Redis memory usage and Celery worker lag.