import requests
import pandas as pd
from datetime import date

HEADERS = {"User-Agent": "TCGPriceMovers/0.1"}
OUTFILE = "live_market_history.csv"

def get_json(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()["results"]

def ext(card, key):
    for item in card.get("extendedData", []):
        if item.get("name") == key:
            return item.get("value", "")
    return ""

groups = get_json("https://tcgcsv.com/tcgplayer/3/groups")

rows = []
today = str(date.today())

for i, group in enumerate(groups, start=1):
    group_id = group["groupId"]
    set_name = group["name"]

    print(f"[{i}/{len(groups)}] Snapshotting {set_name}")

    try:
        products = get_json(f"https://tcgcsv.com/tcgplayer/3/{group_id}/products")
        prices = get_json(f"https://tcgcsv.com/tcgplayer/3/{group_id}/prices")

        price_lookup = {}
        for p in prices:
            product_id = p["productId"]
            if product_id not in price_lookup:
                price_lookup[product_id] = p

        for card in products:
            price = price_lookup.get(card["productId"])
            if not price:
                continue

            number = ext(card, "Number")
            rarity = ext(card, "Rarity")
            finish = price.get("subTypeName", "")

            rows.append({
                "date": today,
                "product_id": f"{card['name']} | {set_name} | {number} | {finish}",
                "name": card["name"],
                "set_name": set_name,
                "number": number,
                "rarity": rarity,
                "finish": finish,
                "market_price": price.get("marketPrice"),
                "low_price": price.get("lowPrice"),
                "group_id": group_id,
                "tcg_product_id": card["productId"]
            })

    except Exception as e:
        print(f"Skipped {set_name}: {e}")

new_df = pd.DataFrame(rows)

try:
    old_df = pd.read_csv(OUTFILE)
    combined = pd.concat([old_df, new_df], ignore_index=True)
except FileNotFoundError:
    combined = new_df

combined = combined.drop_duplicates(["date", "product_id"], keep="last")
combined.to_csv(OUTFILE, index=False)

print()
print(f"Saved {len(new_df)} product prices for {today} into {OUTFILE}")
