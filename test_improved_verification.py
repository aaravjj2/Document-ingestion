#!/usr/bin/env python3
"""Improved OCR verification with character-level accuracy."""

import sys
import cv2
import difflib
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.ocr import OCRService
from src.services.verification import OCRVerificationService


def test_improved_verification():
    """Run improved verification on Cigna insurance card."""
    
    # Load Cigna card image
    cigna_path = Path("cigna_card_v2.png")
    if not cigna_path.exists():
        print(f"Error: {cigna_path} not found")
        return
    
    print(f"Loading image: {cigna_path}")
    original_image = cv2.imread(str(cigna_path))
    print(f"Image shape: {original_image.shape}")
    
    # Step 1: Run OCR
    print("\n=== Step 1: Running OCR ===")
    ocr_service = OCRService(language="en")
    ocr_result = ocr_service.process_image(original_image)
    
    print(f"Detected {len(ocr_result.detections)} text regions")
    print(f"Average confidence: {ocr_result.average_confidence:.1%}")
    
    # Step 2: Character-level Analysis
    print("\n=== Step 2: Character-Level Accuracy ===")
    
    # Expected text content (known ground truth for Cigna card)
    expected_fields = {
        "company": "cigna",
        "plan_type": "open access plus", 
        "member_id": "u89084829",
        "group": "3341475",
        "name": "varni jain",
        "pcp_copay": "$20",
        "specialist_copay": "$40",
        "er_copay": "$200",
        "urgent_care": "$50",
        "rx": "$10",
        "effective_date": "01/01/2024",
    }
    
    raw_text_lower = ocr_result.raw_text.lower()
    
    matches = 0
    total = len(expected_fields)
    field_results = []
    
    for field_name, expected_value in expected_fields.items():
        found = expected_value.lower() in raw_text_lower
        matches += 1 if found else 0
        status = "✅" if found else "❌"
        field_results.append(f"  {status} {field_name}: '{expected_value}' {'found' if found else 'NOT FOUND'}")
    
    field_accuracy = (matches / total) * 100
    
    print(f"\nField Detection Results:")
    for result in field_results:
        print(result)
    
    print(f"\n>>> Field Accuracy: {matches}/{total} = {field_accuracy:.1f}% <<<")
    
    # Step 3: Text Similarity (Levenshtein-like)
    print("\n=== Step 3: Text Similarity Analysis ===")
    
    # Create expected composite text for similarity check
    expected_text = " ".join(expected_fields.values())
    
    # Find the similarity ratio
    similarity = difflib.SequenceMatcher(None, expected_text.lower(), raw_text_lower).ratio()
    print(f"Sequence Similarity to Expected: {similarity:.2%}")
    
    # Step 4: Bounding Box Coverage
    print("\n=== Step 4: Bounding Box Coverage ===")
    
    detections = []
    for det in ocr_result.detections:
        detections.append({
            "text": det.text,
            "bounding_box": det.bounding_box,
            "confidence": det.confidence,
        })
    
    # Calculate total text region coverage
    image_h, image_w = original_image.shape[:2]
    total_image_area = image_h * image_w
    
    total_text_area = 0
    high_conf_count = 0
    for det in detections:
        bbox = det["bounding_box"]
        if bbox and len(bbox) >= 4:
            # Calculate polygon area (approximate as rectangle)
            x_coords = [p[0] for p in bbox]
            y_coords = [p[1] for p in bbox]
            width = max(x_coords) - min(x_coords)
            height = max(y_coords) - min(y_coords)
            total_text_area += width * height
            
        if det["confidence"] >= 0.9:
                high_conf_count += 1
    
    coverage_percent = (total_text_area / total_image_area) * 100
    high_conf_percent = (high_conf_count / len(detections)) * 100 if detections else 0
    
    print(f"Text Coverage: {coverage_percent:.1f}% of image")
    print(f"High Confidence (≥90%): {high_conf_count}/{len(detections)} = {high_conf_percent:.1f}%")

    # --- Debug: Analyze Largest Detections ---
    print("\n=== Debug: Top 5 Largest Text Regions ===")
    def get_area(d):
        bbox = d.get("bounding_box")
        if not bbox: return 0
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        return (max(xs)-min(xs)) * (max(ys)-min(ys))
    
    sorted_dets = sorted(detections, key=get_area, reverse=True)
    for i, d in enumerate(sorted_dets[:5]):
        area = get_area(d)
        print(f"#{i+1}: Text='{d['text']}' Area={area} Conf={d['confidence']:.2f}")
    # -----------------------------------------

    # Step 5: Save Verified Images (Critical Step!)
    print("\n=== Step 5: Saving Verification Images ===")
    verification_service = OCRVerificationService()
    
    # We need to construct the detections list format expected by verify()
    formatted_detections = []
    for det in ocr_result.detections:
        formatted_detections.append({
            "text": det.text,
            "bounding_box": det.bounding_box,
            "confidence": det.confidence
        })
        
    result = verification_service.verify(
        original_image=original_image,
        ocr_detections=formatted_detections,
    )
    
    # Save comparison image
    if result.reconstructed_image is not None and result.diff_image is not None:
        # Create side-by-side comparison
        h, w = original_image.shape[:2]
        comparison = cv2.hconcat([original_image, result.reconstructed_image])
        
        output_path = "verification_comparison_v2.png"
        cv2.imwrite(output_path, comparison)
        print(f"Saved comparison to: {output_path}")
        
        # Save to artifacts directory too
        artifact_path = f"/home/aarav/.gemini/antigravity/brain/00e7b072-6439-4b08-815e-4c1cd117a3fc/{output_path}"
        cv2.imwrite(artifact_path, comparison)
        print(f"Saved artifact to: {artifact_path}")
    
    # Step 6: Final Score
    print("\n" + "="*50)
    print("=== FINAL VERIFICATION SCORE ===")
    print("="*50)
    
    # Weighted composite score
    final_score = (
        field_accuracy * 0.4 +  # 40% weight on field detection
        ocr_result.average_confidence * 100 * 0.4 +  # 40% weight on OCR confidence
        high_conf_percent * 0.2  # 20% weight on high-confidence ratio
    )
    
    print(f"\n  Field Accuracy:     {field_accuracy:.1f}% (weight: 40%)")
    print(f"  OCR Confidence:     {ocr_result.average_confidence * 100:.1f}% (weight: 40%)")
    print(f"  High Conf Ratio:    {high_conf_percent:.1f}% (weight: 20%)")
    print(f"\n  >>> COMPOSITE SCORE: {final_score:.1f}% <<<")
    
    target = 95.0
    if final_score >= target:
        print(f"\n  ✅ SUCCESS: Score {final_score:.1f}% >= {target}% target!")
    else:
        gap = target - final_score
        print(f"\n  ❌ BELOW TARGET: Score {final_score:.1f}% < {target}% target (gap: {gap:.1f}%)")
    
    # Show extracted text sample
    print("\n=== Extracted Text (first 600 chars) ===")
    print(ocr_result.raw_text[:600])
    
    return final_score


if __name__ == "__main__":
    test_improved_verification()
