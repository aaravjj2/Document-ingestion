import cv2
import numpy as np
from pathlib import Path
from src.services.ocr.ocr_service import OCRService

# Load image  
img_path = "cigna_card_v2.png"
image = cv2.imread(img_path)

print(f"Analyzing OCR detections for: {img_path}")
print("=" * 60)

# Get OCR results using OCRService directly
ocr_service = OCRService()
ocr_result = ocr_service.process_image(image, Path(img_path))
detections = ocr_result.get("detections", [])

print(f"\nTotal detections: {len(detections)}")
print("\n" + "=" * 60)

# Group by text to find duplicates
text_groups = {}
for det in detections:
    text = det.get("text", "").strip()
    normalized = " ".join(text.lower().split())
    
    if normalized not in text_groups:
        text_groups[normalized] = []
    text_groups[normalized].append(det)

# Find and analyze duplicates
print("\n### DUPLICATE TEXT ANALYSIS ###\n")
duplicate_count = 0
for text, instances in sorted(text_groups.items(), key=lambda x: len(x[1]), reverse=True):
    if len(instances) > 1:
        duplicate_count += 1
        print(f"\n'{text}' appears {len(instances)} times:")
        for i, det in enumerate(instances, 1):
            bbox = det.get("bounding_box", [])
            if bbox:
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                center_x = sum(xs) / len(xs)
                center_y = sum(ys) / len(ys)
                area = (max(xs) - min(xs)) * (max(ys) - min(ys))
                width = max(xs) - min(xs)
                height = max(ys) - min(ys)
                conf = det.get("confidence", 0)
                print(f"  Instance {i}: Center({center_x:.0f}, {center_y:.0f}), "
                      f"Size({width:.0f}x{height:.0f}), Area={area:.0f}, Conf={conf:.2f}")
                
                # Calculate distance between instances
                if i > 1:
                    prev_bbox = instances[i-2].get("bounding_box", [])
                    if prev_bbox:
                        prev_xs = [p[0] for p in prev_bbox]
                        prev_ys = [p[1] for p in prev_bbox]
                        prev_cx = sum(prev_xs) / len(prev_xs)
                        prev_cy = sum(prev_ys) / len(prev_ys)
                        distance = ((center_x - prev_cx)**2 + (center_y - prev_cy)**2)**0.5
                        print(f"           Distance from previous: {distance:.0f} pixels")

print(f"\n\nTotal unique texts with duplicates: {duplicate_count}")

# Check for specific fields
print("\n" + "=" * 60)
print("\n### KEY FIELD ANALYSIS ###\n")

key_fields = {
    "id": ["id:", "u89084829"],
    "name": ["name:", "varni jain"],
    "group": ["group:", "3341475"],
}

for field_name, keywords in key_fields.items():
    print(f"\n{field_name.upper()} field:")
    found_count = 0
    for text, instances in text_groups.items():
        if any(kw in text for kw in keywords):
            found_count += len(instances)
            print(f"  Found: '{text}' ({len(instances)} instance(s))")
            for i, det in enumerate(instances, 1):
                bbox = det.get("bounding_box", [])
                if bbox:
                    xs = [p[0] for p in bbox]
                    ys = [p[1] for p in bbox]
                    center_x = sum(xs) / len(xs)
                    center_y = sum(ys) / len(ys)
                    print(f"    Instance {i}: Position({center_x:.0f}, {center_y:.0f})")
    if found_count == 0:
        print(f"  ⚠️  NOT FOUND")

# Analysis summary
print("\n" + "=" * 60)
print("\n### ANALYSIS SUMMARY ###\n")
print(f"Total detections: {len(detections)}")
print(f"Unique texts: {len(text_groups)}")
print(f"Texts with duplicates: {duplicate_count}")
print(f"Duplicate instances: {sum(len(instances) - 1 for instances in text_groups.values() if len(instances) > 1)}")
