"""
Barcode Dataset Generator & Seeder.

Generates 1,000+ FMCG product barcode records (EAN-13, EAN-8, UPC-A), saves
to backend/models/barcode_catalog.json (~150 KB, under 200 MB), and syncs to Supabase.
"""

import json
import random
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_PATH = MODEL_DIR / "barcode_catalog.json"

FMCG_CATALOG_TEMPLATES = [
    {"brand": "Tata", "products": [("Tata Salt Iodised", "Spices & Condiments", "1 kg", 28.00, "Tata Consumer Products Ltd, Mumbai", "10014011000189", "Edible Salt, Potassium Iodate"), ("Tata Sampann Turmeric Powder", "Spices", "200 g", 52.00, "Tata Consumer Products Ltd", "10014011000189", "100% Pure Turmeric"), ("Tata Tea Gold", "Beverages", "500 g", 340.00, "Tata Consumer Products Ltd", "10014011000189", "Black Tea, CTC Leaf")]},
    {"brand": "Amul", "products": [("Amul Pasteurised Butter", "Dairy", "100 g", 56.00, "GCMMF Ltd, Anand 388001", "10012021000071", "Milk Fat, Salt"), ("Amul Taaza Toned Milk", "Dairy", "1 L", 54.00, "GCMMF Ltd, Anand", "10012021000071", "Toned Milk, Vitamin A & D"), ("Amul Dark Chocolate 55%", "Confectionery", "150 g", 125.00, "GCMMF Ltd, Anand", "10012021000071", "Cocoa Solids, Sugar, Cocoa Butter")]},
    {"brand": "Britannia", "products": [("Britannia Good Day Butter Biscuits", "Snacks", "150 g", 30.00, "Britannia Industries Ltd, Kolkata", "10015043001122", "Wheat Flour, Butter, Sugar"), ("Britannia Marie Gold", "Snacks", "250 g", 35.00, "Britannia Industries Ltd", "10015043001122", "Refined Wheat Flour, Sugar, Palm Oil"), ("Britannia Milk Bikis", "Snacks", "100 g", 15.00, "Britannia Industries Ltd", "10015043001122", "Wheat Flour, Milk Solids")]},
    {"brand": "Parle", "products": [("Parle-G Glucose Biscuits", "Snacks", "130 g", 10.00, "Parle Products Pvt Ltd, Mumbai", "10012022000456", "Wheat Flour, Sugar, RBD Palm Oil"), ("Parle Monaco Salted Biscuits", "Snacks", "120 g", 20.00, "Parle Products Pvt Ltd", "10012022000456", "Wheat Flour, Vegetable Oil, Salt"), ("Parle Hide & Seek Chocolate Chip", "Snacks", "100 g", 30.00, "Parle Products Pvt Ltd", "10012022000456", "Wheat Flour, Choco Chips, Sugar")]},
    {"brand": "Fortune", "products": [("Fortune Sunlite Sunflower Oil", "Edible Oils", "1 L", 145.00, "Adani Wilmar Ltd, Ahmedabad", "10013021000889", "Refined Sunflower Oil, Vitamin A & D"), ("Fortune Kachi Ghani Mustard Oil", "Edible Oils", "1 L", 165.00, "Adani Wilmar Ltd", "10013021000889", "Mustard Oil"), ("Fortune Basmati Rice Everyday", "Grains", "5 kg", 499.00, "Adani Wilmar Ltd", "10013021000889", "Basmati Rice")]},
    {"brand": "Dabur", "products": [("Dabur 100% Pure Honey", "Health Foods", "500 g", 199.00, "Dabur India Ltd, Ghaziabad", "10012011000111", "100% Pure Natural Honey"), ("Dabur Red Toothpaste", "Personal Care", "200 g", 115.00, "Dabur India Ltd", "10012011000111", "Laung, Pudina, Tomar seed"), ("Real Fruit Power Orange Juice", "Beverages", "1 L", 110.00, "Dabur India Ltd", "10012011000111", "Water, Orange Juice Concentrate")]},
    {"brand": "HUL", "products": [("Surf Excel Easy Wash Detergent", "Household", "1 kg", 140.00, "Hindustan Unilever Ltd, Mumbai", "10012022000222", "Sodium Carbonate, Linear Alkylbenzene Sulfonate"), ("Brooke Bond Red Label Tea", "Beverages", "500 g", 260.00, "Hindustan Unilever Ltd", "10012022000222", "Black Tea"), ("Kissan Mixed Fruit Jam", "Packaged Foods", "500 g", 160.00, "Hindustan Unilever Ltd", "10012022000222", "Fruit Pulp, Sugar, Pectin")]},
    {"brand": "Nestle", "products": [("Maggi 2-Minute Masala Noodles", "Packaged Foods", "280 g", 56.00, "Nestle India Ltd, Gurgaon", "10012011000012", "Refined Wheat Flour, Palm Oil, Spices"), ("Nescafe Classic Instant Coffee", "Beverages", "100 g", 320.00, "Nestle India Ltd", "10012011000012", "100% Pure Coffee Beans"), ("Nestle EveryDay Dairy Whitener", "Dairy", "400 g", 240.00, "Nestle India Ltd", "10012011000012", "Milk Solids, Sugar")]},
    {"brand": "Haldiram", "products": [("Haldiram Bhujia Sev", "Snacks", "400 g", 110.00, "Haldiram Foods International, Nagpur", "10012022000333", "Moth Bean Flour, Besan, Spices, Oil"), ("Haldiram All in One Namkeen", "Snacks", "350 g", 95.00, "Haldiram Foods International", "10012022000333", "Besan, Peanuts, Rice Flakes, Spices"), ("Haldiram Gulab Jamun", "Sweets", "1 kg", 220.00, "Haldiram Foods International", "10012022000333", "Sugar, Water, Chhana, Milk Solids")]},
    {"brand": "Catch", "products": [("Catch Red Chilli Powder", "Spices", "100 g", 48.00, "DS Group, Noida", "10012051000444", "Ground Red Chilli"), ("Catch Garam Masala", "Spices", "100 g", 85.00, "DS Group, Noida", "10012051000444", "Coriander, Cumin, Black Pepper, Cinnamon")]},
]


def generate_ean13_barcode(index: int) -> str:
    """Generate a valid 13-digit EAN-13 barcode string starting with 890 (India country code)."""
    seq = str(index).zfill(9)
    raw12 = f"890{seq}"
    
    odd_sum = sum(int(raw12[i]) for i in range(0, 12, 2))
    even_sum = sum(int(raw12[i]) for i in range(1, 12, 2))
    total = odd_sum + (even_sum * 3)
    check_digit = (10 - (total % 10)) % 10
    
    return f"{raw12}{check_digit}"


def seed_and_save_dataset(total_records: int = 1000):
    """Generate 1,000 barcode objects, save to barcode_catalog.json, and attempt Supabase insert."""
    print("==========================================================")
    print(f"Generating {total_records} FMCG Product Barcodes...")
    print("==========================================================")
    
    catalog_dict = {}
    
    # Common real-world barcodes for instant testing
    test_barcodes = {
        "5449000000996": ("Coca-Cola Original Taste 500ml", "Coca-Cola", "Beverages", "500 ml", 40.00, "Coca-Cola India Pvt Ltd", "10012011000001", "Carbonated Water, Sugar, Caffeine"),
        "8901030300000": ("Tata Salt Iodised 1kg", "Tata", "Spices & Condiments", "1 kg", 28.00, "Tata Consumer Products Ltd", "10014011000189", "Edible Salt, Potassium Iodate"),
        "8901262150059": ("Amul Pasteurised Butter 100g", "Amul", "Dairy", "100 g", 56.00, "GCMMF Ltd, Anand", "10012021000071", "Milk Fat, Salt"),
        "8901063000010": ("Britannia Good Day Butter 150g", "Britannia", "Snacks", "150 g", 30.00, "Britannia Industries Ltd", "10015043001122", "Wheat Flour, Butter, Sugar"),
        "8901410000010": ("Parle-G Glucose Biscuits 130g", "Parle", "Snacks", "130 g", 10.00, "Parle Products Pvt Ltd", "10012022000456", "Wheat Flour, Sugar, Palm Oil"),
    }
    
    for bc, data in test_barcodes.items():
        catalog_dict[bc] = {
            "barcode": bc,
            "product_name": data[0],
            "brand": data[1],
            "category": data[2],
            "net_quantity": data[3],
            "mrp": data[4],
            "manufacturer": data[5],
            "country_of_origin": "India",
            "fssai_lic": data[6],
            "ingredients": data[7],
            "found": True,
        }

    for i in range(1, total_records + 1):
        barcode = generate_ean13_barcode(i)
        brand_info = random.choice(FMCG_CATALOG_TEMPLATES)
        prod_tuple = random.choice(brand_info["products"])
        
        name, cat, qty, mrp, mfg, fssai, ingr = prod_tuple
        variant_suffix = f" (Pack {i % 5 + 1})" if i > 50 else ""
        
        catalog_dict[barcode] = {
            "barcode": barcode,
            "product_name": f"{name}{variant_suffix}",
            "brand": brand_info["brand"],
            "category": cat,
            "net_quantity": qty,
            "mrp": float(mrp),
            "manufacturer": mfg,
            "country_of_origin": "India",
            "fssai_lic": fssai,
            "ingredients": ingr,
            "found": True,
        }

    # Save to JSON file (~150 KB)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog_dict, f, indent=2)
        
    print(f"[OK] Saved {len(catalog_dict)} barcodes to {CATALOG_PATH}")
    
    # Attempt Supabase sync if credentials work
    try:
        from database import supabase
        records = list(catalog_dict.values())
        batch_size = 100
        inserted_count = 0
        for b_start in range(0, len(records), batch_size):
            batch = records[b_start : b_start + batch_size]
            # Strip non-db fields if any
            db_batch = [{k: v for k, v in r.items() if k != "found"} for r in batch]
            supabase.table("product_barcodes").upsert(db_batch, on_conflict="barcode").execute()
            inserted_count += len(batch)
        print(f"[OK] Synced {inserted_count} barcodes to Supabase product_barcodes table!")
    except Exception as exc:
        print(f"[NOTE] Supabase sync deferred (will use local barcode_catalog.json): {exc}")

    print("==========================================================")
    print(f"[SUCCESS] Barcode catalog ready with {len(catalog_dict)} products!")
    print("==========================================================")


if __name__ == "__main__":
    seed_and_save_dataset(1000)
