"""
Test OCR Round-Trip Verification on Passport Document
"""
import cv2
import numpy as np
from pathlib import Path
from src.services.verification.image_verification import OCRVerificationService

def test_passport_verification():
    # Initialize verification service
    verification_service = OCRVerificationService()
    
    # Load passport image
    image_path = "sample_passport.png"
    print(f"\n{'='*60}")
    print(f"Testing Passport Document: {image_path}")
    print(f"{'='*60}\n")
    
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Error: Could not load {image_path}")
        return
    
    print(f"Image loaded: {image.shape}")
    
    # Run verification
    print("\n=== Running OCR and Reconstruction ===")
    
    # First run OCR
    from src.services.ocr.ocr_service import OCRService
    ocr_service = OCRService()
    from pathlib import Path
    ocr_result = ocr_service.process_image(image, Path(image_path))
    
    # Extract detections
    if hasattr(ocr_result, 'detections'):
        ocr_detections = ocr_result.detections
    elif isinstance(ocr_result, dict):
        ocr_detections = ocr_result.get('detections', [])
    else:
        print(f"❌ Error: Unknown OCR result format: {type(ocr_result)}")
        return
    
    print(f"OCR detected {len(ocr_detections)} text regions")
    
    # Convert OCRDetection objects to dict format for reconstruction compatibility
    def convert_detection_to_dict(det):
        """Convert OCRDetection object or dict to standard dict format"""
        if hasattr(det, '__dict__'):
            # It's an object with attributes
            return {
                'text': det.text if hasattr(det, 'text') else '',
                'confidence': det.confidence if hasattr(det, 'confidence') else 0,
                'bounding_box': det.bounding_box if hasattr(det, 'bounding_box') else (det.box if hasattr(det, 'box') else [])
            }
        else:
            # Already a dict
            return det
    
    ocr_detections_dict = [convert_detection_to_dict(d) for d in ocr_detections]
    print(f"Converted {len(ocr_detections_dict)} detections to dict format")
    
    # Now run verification
    result = verification_service.verify(image, ocr_detections_dict)
    
    # Print results
    print(f"\n=== Verification Results ===\n")
    print(f"Total detections: {len(ocr_detections)}")
    
    # Save reconstructed image
    reconstructed = result.reconstructed_image
    if reconstructed is not None:
        output_path = "passport_verification_result.png"
        cv2.imwrite(output_path, reconstructed)
        print(f"\n✅ Reconstructed image saved: {output_path}")
        
        # Also save artifact copy
        artifact_path = "/home/aarav/.gemini/antigravity/brain/00e7b072-6439-4b08-815e-4c1cd117a3fc/passport_verification.png"
        cv2.imwrite(artifact_path, reconstructed)
        print(f"✅ Artifact saved: {artifact_path}")
        
        # Create side-by-side comparison
        original_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        reconstructed_rgb = cv2.cvtColor(reconstructed, cv2.COLOR_BGR2RGB)
        
        # Resize to same height if needed
        h1, h2 = original_rgb.shape[0], reconstructed_rgb.shape[0]
        if h1 != h2:
            scale = h1 / h2
            new_w = int(reconstructed_rgb.shape[1] * scale)
            reconstructed_rgb = cv2.resize(reconstructed_rgb, (new_w, h1))
        
        comparison = np.hstack([original_rgb, reconstructed_rgb])
        comparison_bgr = cv2.cvtColor(comparison, cv2.COLOR_RGB2BGR)
        
        comparison_path = "passport_comparison.png"
        cv2.imwrite(comparison_path, comparison_bgr)
        print(f"✅ Comparison image saved: {comparison_path}")
        
        artifact_comparison = "/home/aarav/.gemini/antigravity/brain/00e7b072-6439-4b08-815e-4c1cd117a3fc/passport_comparison.png"
        cv2.imwrite(artifact_comparison, comparison_bgr)
    
    # Print some detected text
    print(f"\n=== Sample Detected Text (first 10) ===\n")
    for i, det in enumerate(ocr_detections[:10], 1):
        # Handle both dict and OCRDetection object formats
        if hasattr(det, 'text'):
            text = det.text
            conf = det.confidence if hasattr(det, 'confidence') else 0
        else:
            text = det.get('text', '')
            conf = det.get('confidence', 0)
        print(f"{i}. '{text}' (conf: {conf:.2f})")
    
    print(f"\n{'='*60}")
    print(f"✅ Passport verification complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    test_passport_verification()
