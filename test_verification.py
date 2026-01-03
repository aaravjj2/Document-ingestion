#!/usr/bin/env python3
"""Test OCR round-trip verification on Cigna card."""

import sys
import cv2
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.ocr import OCRService
from src.services.verification import OCRVerificationService


def test_cigna_verification():
    """Run verification on Cigna insurance card."""
    
    # Load Cigna card image
    cigna_path = Path("cigna_card_v2.png")
    if not cigna_path.exists():
        print(f"Error: {cigna_path} not found")
        return
    
    print(f"Loading image: {cigna_path}")
    original_image = cv2.imread(str(cigna_path))
    
    if original_image is None:
        print("Error: Could not load image")
        return
    
    print(f"Image shape: {original_image.shape}")
    
    # Step 1: Run OCR
    print("\n=== Step 1: Running OCR ===")
    ocr_service = OCRService(language="en")
    ocr_result = ocr_service.process_image(original_image)
    
    print(f"Detected {len(ocr_result.detections)} text regions")
    print(f"Average confidence: {ocr_result.average_confidence:.1%}")
    
    # Convert detections to dict format
    detections = []
    for det in ocr_result.detections:
        detections.append({
            "text": det.text,
            "bounding_box": det.bounding_box,
            "confidence": det.confidence,
        })
    
    # Print extracted text
    print("\n=== Extracted Text ===")
    print(ocr_result.raw_text[:500] + "..." if len(ocr_result.raw_text) > 500 else ocr_result.raw_text)
    
    # Step 2: Run Verification
    print("\n=== Step 2: Running Round-Trip Verification ===")
    verification_service = OCRVerificationService()
    result = verification_service.verify(original_image, detections)
    
    # Print results
    print("\n=== Verification Results ===")
    print(f"SSIM Score:          {result.ssim_score:.4f} (1.0 = perfect)")
    print(f"Pixel Match:         {result.pixel_match_percent:.2f}%")
    print(f"Text Region Match:   {result.text_region_match:.2f}%")
    
    overall = (result.ssim_score * 100 + result.pixel_match_percent + result.text_region_match) / 3
    print(f"\n>>> Overall Match:   {overall:.2f}% <<<")
    
    # Save outputs for inspection
    if result.reconstructed_image is not None:
        cv2.imwrite("verification_reconstructed.png", result.reconstructed_image)
        print("\nSaved: verification_reconstructed.png")
    
    if result.diff_image is not None:
        cv2.imwrite("verification_diff.png", result.diff_image)
        print("Saved: verification_diff.png")
    
    # Save side-by-side
    if result.reconstructed_image is not None:
        # Ensure same size
        h, w = original_image.shape[:2]
        recon = cv2.resize(result.reconstructed_image, (w, h))
        
        # Create side-by-side
        side_by_side = cv2.hconcat([original_image, recon])
        cv2.imwrite("verification_comparison.png", side_by_side)
        print("Saved: verification_comparison.png")
    
    # Target check
    target = 95.0
    if overall >= target:
        print(f"\n✅ SUCCESS: Match {overall:.2f}% >= {target}% target!")
    else:
        print(f"\n❌ BELOW TARGET: Match {overall:.2f}% < {target}% target")
        print("   Review verification_diff.png to identify problem areas")
    
    return result


if __name__ == "__main__":
    test_cigna_verification()
