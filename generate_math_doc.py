
from PIL import Image, ImageDraw, ImageFont
import os

def create_math_doc():
    # Create white image
    width, height = 1200, 1600
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw Heading
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()
    
    draw.text((100, 100), "Physics Homework - Chapter 4", font=font_large, fill='black')
    
    draw.text((100, 300), "Problem 1: Calculate the rest energy of an electron.", font=font_med, fill='black')
    
    # Draw "Equation" region (Standard Font)
    # The MathService heuristic looks for contours with width 200-800 and height 20-150
    # Let's draw a box or large text that fits this
    
    equation_text = "E = mc^2"
    # We draw a rectangle to ensure contour detection picks it up as a block
    # Box at (200, 500) size 400x100
    draw.rectangle([200, 500, 600, 600], outline="black", width=2)
    draw.text((250, 520), equation_text, font=font_large, fill='black')
    
    draw.text((100, 700), "Where m is mass and c is speed of light.", font=font_med, fill='black')
    
    # Save
    img.save("sample_math_doc.png")
    print("Created sample_math_doc.png")

if __name__ == "__main__":
    create_math_doc()
