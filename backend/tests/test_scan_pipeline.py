"""
Test Scan Pipeline Endpoint with Authentic ES256 Supabase Token.
"""

import io
import sys
import httpx
from pathlib import Path
from PIL import Image, ImageDraw

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from auth.dependencies import get_jwks_client, decode_token

print("==================================================")
print("1. Generating User Session Token via Supabase Auth")
print("==================================================")

sb_url = "https://pmcoytoyqzfcbvgvbkro.supabase.co"
service_role_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBtY295dG95cXpmY2J2Z3Zia3JvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NzY2Mjk3MywiZXhwIjoyMTAzMjM4OTczfQ.eWmhlXW_rgKhhvqyuY7bskW44LeygVo3H0KjqL13_8w"

auth_url = f"{sb_url}/auth/v1/token?grant_type=password"
test_email = "consumer_audit@example.com"
test_password = "Password123!"

with httpx.Client(timeout=15.0) as client:
    res = client.post(auth_url, json={"email": test_email, "password": test_password}, headers={"apikey": service_role_key, "Content-Type": "application/json"})
    data = res.json()
    user_token = data.get("access_token")

print("User token generated:", bool(user_token))

print("\n==================================================")
print("2. Testing Full Scan Pipeline with Live ES256 Token")
print("==================================================")

# Create a sample product label image
img = Image.new('RGB', (400, 200), color='white')
d = ImageDraw.Draw(img)
d.text((10, 10), 'Tata Salt Iodised 1kg MRP Rs 28.00 Mfg 12/2026 Batch TS202601', fill='black')
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

files = {'file': ('tata_label.jpg', buf.getvalue(), 'image/jpeg')}
data = {'barcode': '8901030300000'}
headers = {'Authorization': f'Bearer {user_token}'}

client = TestClient(app)
res = client.post('/api/scans/scan', files=files, data=data, headers=headers)

print("Scan Endpoint Status Code:", res.status_code)
if res.status_code == 200:
    res_data = res.json()
    print("\nSUCCESS! Complete scan pipeline response keys:")
    print(" ", list(res_data.keys()))
    print("\nOCR Output:")
    print("  Provider:", res_data.get("ocr", {}).get("provider"))
    print("  Extracted Text:", res_data.get("ocr", {}).get("full_text", "")[:80])
    print("\nCompliance Output:")
    print("  Score:", res_data.get("compliance", {}).get("compliance_score"))
    print("  Status:", res_data.get("compliance", {}).get("status"))
    print("  Passed Declarations:", res_data.get("compliance", {}).get("passed_declarations"))
    print("  Failed Declarations:", res_data.get("compliance", {}).get("failed_declarations"))
else:
    print("Scan failed:", res.text)
