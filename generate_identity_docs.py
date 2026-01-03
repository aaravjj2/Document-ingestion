#!/usr/bin/env python3
"""Generate synthetic identity documents for OCR testing."""
from PIL import Image, ImageDraw, ImageFont
import random

def create_passport():
    """Create a synthetic passport image."""
    img = Image.new('RGB', (800, 550), color=(245, 240, 230))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_mrz = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 16)
    except:
        font = font_small = font_mrz = ImageFont.load_default()
    
    # Header
    draw.rectangle([(0, 0), (800, 80)], fill=(0, 50, 100))
    draw.text((300, 25), "PASSPORT", fill="gold", font=font)
    draw.text((270, 55), "UNITED STATES OF AMERICA", fill="white", font=font_small)
    
    # Photo placeholder
    draw.rectangle([(50, 120), (220, 320)], fill=(200, 200, 200), outline="black")
    draw.text((100, 210), "PHOTO", fill=(100, 100, 100), font=font_small)
    
    # Personal info
    info = [
        ("Surname:", "SMITH"),
        ("Given Names:", "JOHN WILLIAM"),
        ("Nationality:", "UNITED STATES"),
        ("Date of Birth:", "15 MAR 1985"),
        ("Sex:", "M"),
        ("Place of Birth:", "NEW YORK, USA"),
        ("Date of Issue:", "01 JAN 2020"),
        ("Date of Expiry:", "01 JAN 2030"),
        ("Passport No:", "123456789"),
    ]
    
    y = 120
    for label, value in info:
        draw.text((250, y), label, fill="gray", font=font_small)
        draw.text((420, y), value, fill="black", font=font_small)
        y += 30
    
    # MRZ Zone
    draw.rectangle([(0, 450), (800, 550)], fill=(240, 240, 240))
    draw.text((30, 460), "P<USASMITH<<JOHN<WILLIAM<<<<<<<<<<<<<<<<<<<", fill="black", font=font_mrz)
    draw.text((30, 490), "1234567890USA8503155M3001019<<<<<<<<<<<<<<04", fill="black", font=font_mrz)
    
    img.save("sample_passport.png")
    print("Created: sample_passport.png")


def create_drivers_license():
    """Create a synthetic driver's license image."""
    img = Image.new('RGB', (600, 400), color=(240, 245, 250))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except:
        font = font_small = font_large = ImageFont.load_default()
    
    # Header
    draw.rectangle([(0, 0), (600, 50)], fill=(0, 80, 150))
    draw.text((150, 10), "DRIVER LICENSE", fill="white", font=font_large)
    draw.text((400, 35), "STATE OF NEW YORK", fill="lightyellow", font=font_small)
    
    # Photo placeholder
    draw.rectangle([(30, 70), (150, 200)], fill=(200, 200, 200), outline="black")
    draw.text((60, 125), "PHOTO", fill=(100, 100, 100), font=font_small)
    
    # Personal info
    draw.text((180, 70), "DL:", fill="gray", font=font_small)
    draw.text((220, 68), "D123-4567-8901", fill="black", font=font)
    
    draw.text((180, 100), "NAME:", fill="gray", font=font_small)
    draw.text((250, 98), "JANE DOE", fill="black", font=font)
    
    draw.text((180, 130), "ADDRESS:", fill="gray", font=font_small)
    draw.text((270, 128), "123 Main Street", fill="black", font=font_small)
    draw.text((270, 148), "New York, NY 10001", fill="black", font=font_small)
    
    draw.text((180, 180), "DOB:", fill="gray", font=font_small)
    draw.text((230, 178), "05/20/1990", fill="black", font=font)
    
    draw.text((350, 180), "SEX:", fill="gray", font=font_small)
    draw.text((400, 178), "F", fill="black", font=font)
    
    draw.text((450, 180), "HGT:", fill="gray", font=font_small)
    draw.text((500, 178), "5-06", fill="black", font=font)
    
    draw.text((180, 210), "ISSUED:", fill="gray", font=font_small)
    draw.text((250, 208), "01/15/2023", fill="black", font=font_small)
    
    draw.text((380, 210), "EXPIRES:", fill="gray", font=font_small)
    draw.text((460, 208), "05/20/2031", fill="black", font=font_small)
    
    # License class
    draw.text((30, 250), "CLASS:", fill="gray", font=font_small)
    draw.text((90, 248), "D", fill="black", font=font)
    
    # Endorsements/Restrictions
    draw.text((130, 250), "RESTRICTIONS:", fill="gray", font=font_small)
    draw.text((260, 248), "NONE", fill="black", font=font_small)
    
    # Barcode area
    draw.rectangle([(30, 300), (570, 380)], fill=(220, 220, 220))
    for i in range(50):
        x = 40 + i * 10
        w = random.randint(2, 6)
        draw.rectangle([(x, 310), (x+w, 370)], fill="black")
    
    img.save("sample_license.png")
    print("Created: sample_license.png")


def create_health_insurance_bcbs():
    """Create a Blue Cross Blue Shield insurance card."""
    img = Image.new('RGB', (600, 380), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_logo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        font = font_small = font_logo = ImageFont.load_default()
    
    # Header stripe
    draw.rectangle([(0, 0), (600, 60)], fill=(0, 90, 170))
    draw.text((30, 15), "Blue Cross Blue Shield", fill="white", font=font_logo)
    draw.text((420, 38), "PPO Plan", fill="lightskyblue", font=font_small)
    
    # Member info
    draw.text((30, 80), "Member Name:", fill="gray", font=font_small)
    draw.text((150, 78), "ROBERT JOHNSON", fill="black", font=font)
    
    draw.text((30, 110), "Member ID:", fill="gray", font=font_small)
    draw.text((150, 108), "XYZ987654321", fill="black", font=font)
    
    draw.text((350, 110), "Group:", fill="gray", font=font_small)
    draw.text((420, 108), "12345678", fill="black", font=font)
    
    draw.text((30, 140), "Effective Date:", fill="gray", font=font_small)
    draw.text((150, 138), "03/01/2025", fill="black", font=font)
    
    # Copays section
    draw.text((30, 180), "COPAYS", fill="navy", font=font)
    draw.text((30, 210), "PCP Visit:", fill="gray", font=font_small)
    draw.text((120, 208), "$25", fill="black", font=font)
    
    draw.text((200, 210), "Specialist:", fill="gray", font=font_small)
    draw.text((290, 208), "$50", fill="black", font=font)
    
    draw.text((370, 210), "ER:", fill="gray", font=font_small)
    draw.text((410, 208), "$150", fill="black", font=font)
    
    draw.text((480, 210), "Rx:", fill="gray", font=font_small)
    draw.text((520, 208), "$15/$35/$70", fill="black", font=font_small)
    
    # Deductible section
    draw.text((30, 250), "DEDUCTIBLE", fill="navy", font=font)
    draw.text((30, 280), "Individual:", fill="gray", font=font_small)
    draw.text((120, 278), "$1,000", fill="black", font=font)
    
    draw.text((220, 280), "Family:", fill="gray", font=font_small)
    draw.text((290, 278), "$2,500", fill="black", font=font)
    
    # Rx identifiers
    draw.text((30, 320), "RxBIN:", fill="gray", font=font_small)
    draw.text((100, 318), "610014", fill="black", font=font_small)
    
    draw.text((180, 320), "RxPCN:", fill="gray", font=font_small)
    draw.text((250, 318), "BCBSRX", fill="black", font=font_small)
    
    draw.text((340, 320), "RxGroup:", fill="gray", font=font_small)
    draw.text((420, 318), "87654321", fill="black", font=font_small)
    
    img.save("sample_bcbs_card.png")
    print("Created: sample_bcbs_card.png")


    print("Created: sample_bcbs_card.png")


def create_health_insurance_aetna():
    """Create an Aetna insurance card."""
    img = Image.new('RGB', (600, 380), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_logo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        font = font_small = font_logo = ImageFont.load_default()
    
    # Logo
    draw.text((30, 20), "aetna", fill="purple", font=font_logo)
    draw.rectangle([(130, 25), (145, 40)], fill="purple")
    draw.text((450, 25), "Choice POS II", fill="black", font=font_small)
    
    # Member info
    draw.text((30, 80), "ID", fill="gray", font=font_small)
    draw.text((30, 95), "W123456789", fill="black", font=font)
    
    draw.text((200, 80), "NAME", fill="gray", font=font_small)
    draw.text((200, 95), "DAVID SMITH", fill="black", font=font)
    
    draw.text((450, 80), "GRP", fill="gray", font=font_small)
    draw.text((450, 95), "887766-010-00001", fill="black", font=font_small)
    
    # Copays
    draw.line([(30, 140), (570, 140)], fill="gray")
    
    draw.text((30, 160), "PCP:", fill="black", font=font_small)
    draw.text((80, 160), "$15", fill="black", font=font)
    
    draw.text((150, 160), "SPEC:", fill="black", font=font_small)
    draw.text((200, 160), "$30", fill="black", font=font)
    
    draw.text((270, 160), "URGENT:", fill="black", font=font_small)
    draw.text((340, 160), "$50", fill="black", font=font)
    
    draw.text((420, 160), "ER:", fill="black", font=font_small)
    draw.text((460, 160), "$200", fill="black", font=font)
    
    # Rx
    draw.text((30, 220), "RX BIN:", fill="black", font=font_small)
    draw.text((100, 220), "610502", fill="black", font=font_small)
    
    draw.text((200, 220), "RX PCN:", fill="black", font=font_small)
    draw.text((270, 220), "MEDDADV", fill="black", font=font_small)
    
    img.save("sample_aetna_card.png")
    print("Created: sample_aetna_card.png")


def create_health_insurance_uhc():
    """Create a UnitedHealthcare insurance card."""
    img = Image.new('RGB', (600, 380), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_logo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        font = font_small = font_logo = ImageFont.load_default()
    
    # Header
    draw.text((30, 20), "UnitedHealthcare", fill="navy", font=font_logo)
    draw.text((30, 50), "StudentResources", fill="gray", font=font_small)
    
    # Member info - Card layout often has name then ID
    draw.text((30, 100), "Member ID:", fill="black", font=font_small)
    draw.text((130, 98), "SR987654321", fill="black", font=font)
    
    draw.text((300, 100), "Policy #:", fill="black", font=font_small)
    draw.text((380, 98), "2024-556677", fill="black", font=font)
    
    draw.text((30, 140), "Member:", fill="black", font=font_small)
    draw.text((130, 138), "EMILY DAVIS", fill="black", font=font)
    
    # Costs
    draw.rectangle([(20, 200), (580, 350)], outline="navy")
    
    draw.text((40, 220), "Copay:", fill="navy", font=font)
    draw.text((40, 250), "Office Visit: $20", fill="black", font=font_small)
    draw.text((200, 250), "Specialist: $40", fill="black", font=font_small)
    
    draw.text((40, 280), "Deductible:", fill="navy", font=font)
    draw.text((40, 310), "Ind: $500", fill="black", font=font_small)
    draw.text((200, 310), "Fam: $1500", fill="black", font=font_small)
    
    draw.text((350, 220), "Pharmacy (OptumRx)", fill="navy", font=font_small)
    draw.text((350, 250), "BIN: 610279", fill="black", font=font_small)
    draw.text((350, 270), "PCN: 9999", fill="black", font=font_small)
    draw.text((350, 290), "GRP: UHC123", fill="black", font=font_small)
    
    img.save("sample_uhc_card.png")
    print("Created: sample_uhc_card.png")


def create_california_license():
    """Create a synthetic California driver's license."""
    img = Image.new('RGB', (600, 400), color=(240, 248, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        font_heavy = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_script = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except:
        font = font_heavy = font_small = font_script = ImageFont.load_default()
    
    # Modern CA Design
    draw.text((350, 20), "California", fill="darkblue", font=font_script)
    draw.text((400, 50), "DRIVER LICENSE", fill="black", font=font_small)
    
    # Bear Graphic placeholder
    draw.rectangle([(450, 80), (550, 150)], outline="gold", width=3)
    draw.text((470, 110), "BEAR", fill="gold", font=font_small)
    
    # ID Number
    draw.text((300, 80), "DL F1234567", fill="black", font=font_heavy)
    
    # Details
    draw.text((250, 120), "EXP 08/31/2029", fill="red", font=font)
    draw.text((250, 150), "LN  WONG", fill="black", font=font)
    draw.text((250, 180), "FN  SARAH", fill="black", font=font)
    draw.text((250, 210), "123 SUNSET BLVD", fill="black", font=font_small)
    draw.text((250, 230), "LOS ANGELES, CA 90028", fill="black", font=font_small)
    
    draw.text((250, 260), "DOB 08/31/1995", fill="red", font=font)
    
    draw.text((250, 290), "RSTR NONE", fill="black", font=font_small)
    draw.text((400, 290), "CLASS C", fill="black", font=font_small)
    draw.text((250, 310), "SEX F", fill="black", font=font_small)
    draw.text((320, 310), "HGT 5'-04\"", fill="black", font=font_small)
    
    # Photo
    draw.rectangle([(30, 100), (200, 320)], fill="lightgray", outline="black")
    draw.text((80, 200), "PHOTO", fill="gray", font=font_small)
    
    # Signature
    draw.text((50, 350), "Sarah Wong", fill="black", font=font_script)
    
    img.save("sample_ca_license.png")
    print("Created: sample_ca_license.png")


if __name__ == "__main__":
    create_passport()
    create_drivers_license()
    create_health_insurance_bcbs()
    create_health_insurance_aetna()
    create_health_insurance_uhc()
    create_california_license()
    print("\nAll sample documents created!")
