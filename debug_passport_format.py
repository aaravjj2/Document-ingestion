"""Debug script to check OCR detection format for passport"""
import cv2
from pathlib import Path
from src.services.ocr.ocr_service import OCRService

# Load passport
image = cv2.imread("sample_passport.png")
print(f"Image shape: {image.shape}")

# Run OCR
ocr_service = OCRService()
ocr_result = ocr_service.process_image(image, Path("sample_passport.png"))

# Extract detections
if hasattr(ocr_result, 'detections'):
    ocr_detections = ocr_result.detections
else:
    ocr_detections = ocr_result.get('detections', [])

print(f"\nTotal detections: {len(ocr_detections)}")
print(f"Detection type: {type(ocr_detections[0]) if ocr_detections else 'N/A'}")

# Check first few detections
print("\n=== First 3 Detections ===")
for i, det in enumerate(ocr_detections[:3], 1):
    print(f"\nDetection {i}:")
    print(f"  Type: {type(det)}")
    print(f"  Has 'get' method: {hasattr(det, 'get')}")
    print(f"  Has 'text' attr: {hasattr(det, 'text')}")
    print(f"  Has 'bounding_box' attr: {hasattr(det, 'bounding_box')}")
    print(f"  Has 'box' attr: {hasattr(det, 'box')}")
    
    if hasattr(det, 'text'):
        print(f"  Text (attr): {det.text}")
        print(f"  Confidence: {det.confidence if hasattr(det, 'confidence') else 'N/A'}")
        if hasattr(det, 'bounding_box'):
            print(f"  BBox (attr): {det.bounding_box}")
    
    if hasattr(det, '__dict__'):
        print(f"  __dict__ keys: {det.__dict__.keys()}")
