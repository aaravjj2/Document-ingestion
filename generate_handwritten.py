#!/usr/bin/env python3
"""Generate a synthetic handwritten doctor's note for OCR testing."""
from PIL import Image, ImageDraw, ImageFont
import random

def create_handwritten_note():
    # Create a slightly off-white background (like paper)
    img = Image.new('RGB', (800, 600), color=(252, 250, 245))
    draw = ImageDraw.Draw(img)
    
    # Try to use a handwriting-like font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # Draw lined paper effect
    for y in range(80, 550, 35):
        draw.line([(50, y), (750, y)], fill=(200, 200, 255), width=1)
    
    # Header
    draw.text((300, 30), "Dr. Smith's Clinic", fill=(0, 0, 100), font=font)
    draw.text((280, 55), "123 Main St, New York", fill=(80, 80, 80), font=font)
    
    # Date
    draw.text((600, 100), "Jan 1, 2026", fill=(30, 30, 50), font=font)
    
    # Content - slightly offset to simulate handwriting
    lines = [
        "Patient: John Doe",
        "DOB: 05/15/1985",
        "",
        "Chief Complaint: Headache for 3 days",
        "Diagnosis: Tension headache",
        "",
        "Treatment:",
        "  - Ibuprofen 400mg as needed",
        "  - Rest and hydration",
        "  - Follow up in 1 week if no improvement",
        "",
        "Excused from work: Jan 1-3, 2026",
    ]
    
    y = 130
    for i, line in enumerate(lines):
        # Add slight randomness to simulate handwriting
        x_offset = random.randint(-3, 3)
        y_offset = random.randint(-2, 2)
        draw.text((60 + x_offset, y + y_offset), line, fill=(20, 20, 40), font=font)
        y += 35
    
    # Signature
    draw.text((500, 520), "Dr. A. Smith, MD", fill=(0, 0, 100), font=font)
    
    # Save
    img.save("handwritten_doctor_note.png")
    print("Created: handwritten_doctor_note.png")

if __name__ == "__main__":
    create_handwritten_note()
