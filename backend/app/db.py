import os
import sqlite3
from collections import OrderedDict

# Use an absolute DB path located at the repository root so callers get the
# same database regardless of the current working directory when running
# scripts or tests.
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "grocery_cache.db"
# ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# DB_PATH = os.path.join(ROOT_DIR, 'grocery_cache.db')

def get_connection():
    # print("DB PATH:", os.path.abspath(DB_PATH))
    return sqlite3.connect(DB_PATH)

def normalize_item_key(item: str) -> str:
    return item.strip().lower()

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Item cache table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS item_cache (
        item TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        normalized_name TEXT NOT NULL,
        source TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


    #     Store (brand)
    #   └── Location
    #         └── Zones / Aisles
    #               └── Categories

    cur.execute("""
    CREATE TABLE IF NOT EXISTS stores (
        store_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        chain TEXT,
        UNIQUE(name)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS store_locations (
        location_id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_id INTEGER NOT NULL,
        city TEXT,
        state TEXT,
        postal_code TEXT,
        FOREIGN KEY(store_id) REFERENCES stores(store_id),
        UNIQUE(store_id, postal_code)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS store_zones (
        zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
        location_id INTEGER NOT NULL,
        zone_name TEXT NOT NULL,
        zone_order INTEGER NOT NULL,
        FOREIGN KEY(location_id) REFERENCES store_locations(location_id),
        UNIQUE(location_id, zone_order)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS zone_categories (
        zone_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        PRIMARY KEY (zone_id, category),
        FOREIGN KEY(zone_id) REFERENCES store_zones(zone_id)
    );
    """)

    conn.commit()
    conn.close()

def get_cached_item(item: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT category, normalized_name, source FROM item_cache WHERE item = ?",
        (item,)
    )
    row = cur.fetchone()
    conn.close()

    if row:
        return {
            "category": row[0],
            "normalized_name": row[1],
            "source": row[2]
        }

    return None

def cache_item(item: str, category: str, normalized_name: str, source: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO item_cache
        (item, category, normalized_name, source)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(item) DO UPDATE SET
            category = excluded.category,
            normalized_name = excluded.normalized_name,
            source = excluded.source
        WHERE item_cache.source != 'manual'
    """, (normalize_item_key(item), category, normalized_name, source))

    conn.commit()
    conn.close()

def get_store_details(store_name: str, postal_code: str = None):
    """Return store_id, name, chain, zip, location_id for a given store name
      and optional postal code."""
    conn = get_connection()
    cur = conn.cursor()

    if postal_code:
        cur.execute("""
            SELECT s.store_id, s.name, s.chain, sl.postal_code, sl.location_id
            FROM stores s
            JOIN store_locations sl ON s.store_id = sl.store_id
            WHERE s.name = ? AND sl.postal_code = ?
            LIMIT 1
        """, (store_name, postal_code))
    else:
        cur.execute("""
            SELECT s.store_id, s.name, s.chain, sl.postal_code, sl.location_id
            FROM stores s
            JOIN store_locations sl ON s.store_id = sl.store_id
            WHERE s.name = ?
            LIMIT 1
        """, (store_name,))

    row = cur.fetchone()
    conn.close()

    if row:
        return {
            "store_id": row[0], 
            "name": row[1],
            "chain": row[2],
            "postal_code": row[3],
            "location_id": row[4]
        }
    else:
        raise ValueError(f"Store '{store_name}' with postal code '{postal_code}' not found.")


def get_store_id(store_name: str, postal_code: str = None) -> int:
    """Return store_id for a given store name and optional postal code."""
    conn = get_connection()
    cur = conn.cursor()

    if postal_code:
        cur.execute("""
            SELECT s.store_id
            FROM stores s
            JOIN store_locations sl ON s.store_id = sl.store_id
            WHERE s.name = ? AND sl.postal_code = ?
            LIMIT 1
        """, (store_name, postal_code))
    else:
        cur.execute("""
            SELECT s.store_id
            FROM stores s
            WHERE s.name = ?
            LIMIT 1
        """, (store_name,))

    row = cur.fetchone()
    conn.close()

    if row:
        return row[0]
    else:
        raise ValueError(f"Store '{store_name}' with postal code '{postal_code}' not found.")

def get_store_layout(store_id: int = None, store_name: str = None, postal_code: str = None):
    """Return list of (zone_name, [categories]) for a store.

    If `postal_code` is provided, returns the layout for that specific
    location. If not provided, picks the first matching location for the
    store (by insertion order) and returns its layout. Returns an empty
    list when no matching store/location is found.
    """
    conn = get_connection()
    cur = conn.cursor()
    if not store_id:
        if store_name:
            return get_store_layout(store_id = get_store_id(store_name, postal_code))
            
        else:
            raise ValueError("Either store_id or store_name must be provided.")

    cur.execute("""
        SELECT sz.zone_name, zc.category
        FROM stores s
        JOIN store_locations sl ON s.store_id = sl.store_id
        JOIN store_zones sz ON sl.location_id = sz.location_id
        JOIN zone_categories zc ON sz.zone_id = zc.zone_id
        WHERE s.store_id = ? 
        ORDER BY sz.zone_order ASC
    """, (store_id,))

    rows = cur.fetchall()
    if not rows:
        conn.close()
        return []

    zones = OrderedDict()
    for zone_name, category in rows:
        if zone_name not in zones:
            zones[zone_name] = []
        zones[zone_name].append(category)

    conn.close()
    return list(zones.items())

def override_item(item: str, category: str, normalized_name: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO item_cache
        (item, category, normalized_name, source)
        VALUES (?, ?, ?, 'manual')
    """, (normalize_item_key(item), category, normalized_name))

    conn.commit()
    conn.close()

def get_or_create_store(conn, name, chain):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO stores (name, chain)
        VALUES (?, ?)
    """, (name, chain))

    cur.execute("SELECT store_id FROM stores WHERE name = ?", (name,))
    return cur.fetchone()[0]

def get_or_create_location(conn, store_id, city, state, postal_code):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO store_locations
        (store_id, city, state, postal_code)
        VALUES (?, ?, ?, ?)
    """, (store_id, city, state, postal_code))

    cur.execute("""
        SELECT location_id
        FROM store_locations
        WHERE store_id = ? AND postal_code = ?
    """, (store_id, postal_code))

    return cur.fetchone()[0]

def insert_zones(conn, location_id, zones):
    cur = conn.cursor()
    zone_ids = {}

    for order, (zone_name, categories) in enumerate(zones, start=1):
        cur.execute("""
            INSERT OR IGNORE INTO store_zones
            (location_id, zone_name, zone_order)
            VALUES (?, ?, ?)
        """, (location_id, zone_name, order))

        cur.execute("""
            SELECT zone_id
            FROM store_zones
            WHERE location_id = ? AND zone_name = ?
        """, (location_id, zone_name))

        zone_id = cur.fetchone()[0]
        zone_ids[zone_name] = zone_id

        for category in categories:
            cur.execute("""
                INSERT OR IGNORE INTO zone_categories
                (zone_id, category)
                VALUES (?, ?)
            """, (zone_id, category))

    return zone_ids


def add_store_layout(store_name, chain, city, state, postal_code, zones):
    conn = sqlite3.connect(DB_PATH)

    store_id = get_or_create_store(conn, store_name, chain)
    print(f"Created/Retrieved store_id for {store_name}: {store_id}")
    location_id = get_or_create_location(conn, store_id, city, state, postal_code)
    print(f"Created/Retrieved location_id for {store_name}: {location_id}")

    zone_ids = insert_zones(conn, location_id, zones)
    for name, zone_id in zone_ids.items():
        print(f"Created/Retrieved zone_id for {name}: {zone_id}")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # init_db()
    # print("Database initialized.")
    import os
    print("SQLite DB path:", os.path.abspath(DB_PATH))
