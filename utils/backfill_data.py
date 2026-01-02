import csv
import sys
from pathlib import Path

# Add the repository root to sys.path so we can import backend modules
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.db import cache_item
from backend.app.db import add_store_layout, get_store_layout

# CSV file is in the same directory as this script
CSV_PATH = Path(__file__).parent / "item_cache.csv"

def import_csv(path: str):
    count = 0

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            item = row.get("item", "").strip()
            if not item:
                continue

            cache_item(
                item=item,
                category=row.get("category", "").strip(),
                normalized_name=row.get("normalized_name", "").strip(),
                source=row.get("source", "rules").strip()
            )
            count += 1

    print(f"Imported {count} rows into item_cache.")

if __name__ == "__main__":
    import_csv(CSV_PATH)

    zones = [
        ("Produce", ["Produce"]),
        ("Bakery", ["Bakery"]),
        ("Meat & Seafood", ["Meat", "Seafood", "Deli"]),
        ("Beverages", ["Beverages"]),
        ("Personal Care", ["Personal Care"]),
        ("Pantry", ["Pantry"]),
        ("Dairy", ["Dairy"]),
        ("Frozen", ["Frozen"]),
        ("Household", ["Household"]),
    ]

    add_store_layout(
        store_name="Wegmans",
        chain="Wegmans",
        city="Parsippany",
        state="NJ",
        postal_code="07054",
        zones=zones
    )

    zones = [
        ("Produce", ["Produce"]),
        ("Bakery", ["Bakery"]),
        ("Meat & Seafood", ["Meat", "Seafood", "Deli"]),
        ("Personal Care", ["Personal Care"]),
        ("Alcohol", ["Beer", "Wine", "Spirits"]),
        ("Beverages", ["Beverages"]),        
        ("Pantry", ["Pantry"]),
        ("Household", ["Household"]),
        ("Frozen", ["Frozen"]),
        ("Dairy", ["Dairy"]),
    ]

    add_store_layout(
        store_name="ShopRite of West Caldwell",
        chain="ShopRite",
        city="West Caldwell",
        state="NJ",
        postal_code="07006",
        zones=zones
    )

    zones = [
        ("Produce", ["Produce"]),
        ("Bakery", ["Bakery"]),
        ("Dairy", ["Dairy"]),
        ("Deli", ["Deli"]),
        ("Pantry", ["Pantry"]),
        ("Beverages", ["Beverages"]),
        ("Frozen", ["Frozen"]),
        ("Household", ["Household"]),
        ("Personal Care", ["Personal Care"]),
    ]

    add_store_layout(
        store_name="Trader Joe's",
        chain="Trader Joe's",
        city="Denville",
        state="NJ",
        postal_code="07054",
        zones=zones
    )
    
    # layout = get_store_layout("Wegmans", "07054")
    # print(f"Store Layout for Wegmans (07054): {layout}")