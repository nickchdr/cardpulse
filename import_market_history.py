import json
import shutil
import sqlite3
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timedelta, date

HEADERS = {"User-Agent": "TCGPriceMovers/0.1"}
DB_FILE = "tcg_market.db"
CATEGORY_ID = 3

def get_json(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()["results"]

def get_card_field(card, field):
    for item in card.get("extendedData", []):
        if item.get("name") == field:
            return item.get("value", "")
    return ""

def setup_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            group_id INTEGER,
            name TEXT,
            set_name TEXT,
            number TEXT,
            rarity TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            date TEXT,
            product_id INTEGER,
            group_id INTEGER,
            finish TEXT,
            market_price REAL,
            low_price REAL,
            direct_low_price REAL,
            PRIMARY KEY (date, product_id, finish)
        )
    """)

    conn.commit()
    return conn

def already_imported(conn, date_str):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM price_history WHERE date = ?", (date_str,))
    return cur.fetchone()[0] > 0

def latest_imported_date(conn):
    cur = conn.cursor()
    cur.execute("SELECT MAX(date) FROM price_history")
    value = cur.fetchone()[0]
    return value

def cache_products_for_group(conn, group_id, set_name):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM products WHERE group_id = ?", (group_id,))
    if cur.fetchone()[0] > 0:
        return

    try:
        products = get_json(f"https://tcgcsv.com/tcgplayer/{CATEGORY_ID}/{group_id}/products")
    except Exception as e:
        print(f"Could not fetch products for {set_name}: {e}")
        return

    for card in products:
        cur.execute("""
            INSERT OR REPLACE INTO products
            (product_id, group_id, name, set_name, number, rarity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            card["productId"],
            group_id,
            card["name"],
            set_name,
            get_card_field(card, "Number"),
            get_card_field(card, "Rarity")
        ))

    conn.commit()

def import_date(conn, date_str, group_lookup):
    if already_imported(conn, date_str):
        print(f"{date_str} already imported. Skipping.")
        return

    archive_name = f"prices-{date_str}.ppmd.7z"
    archive_url = f"https://tcgcsv.com/archive/tcgplayer/{archive_name}"
    folder = Path(date_str)

    try:
        if not Path(archive_name).exists():
            print(f"Downloading {archive_name}")
            subprocess.run(["curl", "-f", "-L", "-O", archive_url], check=True)

        if not folder.exists():
            print(f"Extracting {archive_name}")
            subprocess.run(["7z", "x", archive_name], check=True)

    except Exception:
        print(f"No archive available for {date_str}. Skipping.")
        if Path(archive_name).exists():
            Path(archive_name).unlink()
        return

    pokemon_folder = folder / str(CATEGORY_ID)

    if not pokemon_folder.exists():
        print(f"No Pokémon folder found for {date_str}")
        return

    cur = conn.cursor()
    imported = 0

    group_folders = [p for p in pokemon_folder.iterdir() if p.is_dir()]

    for group_path in group_folders:
        group_id = int(group_path.name)
        prices_file = group_path / "prices"

        if not prices_file.exists():
            continue

        set_name = group_lookup.get(group_id, f"Group {group_id}")
        cache_products_for_group(conn, group_id, set_name)

        try:
            data = json.loads(prices_file.read_text())
            price_rows = data.get("results", [])
        except Exception as e:
            print(f"Could not read {prices_file}: {e}")
            continue

        for price in price_rows:
            cur.execute("""
                INSERT OR REPLACE INTO price_history
                (date, product_id, group_id, finish, market_price, low_price, direct_low_price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str,
                price.get("productId"),
                group_id,
                price.get("subTypeName", ""),
                price.get("marketPrice"),
                price.get("lowPrice"),
                price.get("directLowPrice")
            ))
            imported += 1

    conn.commit()
    print(f"Imported {imported} Pokémon price rows for {date_str}")

    # Clean up extracted folder and archive so your Mac doesn't fill up
    if folder.exists():
        shutil.rmtree(folder)
    if Path(archive_name).exists():
        Path(archive_name).unlink()

def main():
    conn = setup_db()

    groups = get_json(f"https://tcgcsv.com/tcgplayer/{CATEGORY_ID}/groups")
    group_lookup = {int(g["groupId"]): g["name"] for g in groups}

    latest = latest_imported_date(conn)

    if latest:
        start = datetime.strptime(latest, "%Y-%m-%d") + timedelta(days=1)
    else:
        start = datetime.strptime("2024-02-08", "%Y-%m-%d")

    end = datetime.combine(date.today(), datetime.min.time())

    print(f"Importing from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")

    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        print()
        print(f"=== Importing {date_str} ===")
        import_date(conn, date_str, group_lookup)
        current += timedelta(days=1)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM price_history")
    print("Total price history rows:", cur.fetchone()[0])

    cur.execute("SELECT COUNT(DISTINCT date) FROM price_history")
    print("Dates imported:", cur.fetchone()[0])

    cur.execute("SELECT MIN(date), MAX(date) FROM price_history")
    print("Date range:", cur.fetchone())

    cur.execute("SELECT COUNT(*) FROM products")
    print("Products:", cur.fetchone()[0])

    conn.close()

if __name__ == "__main__":
    main()
