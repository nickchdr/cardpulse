import requests
import pandas as pd

CATEGORY_ID = 3
GROUP_ID = 3170

headers = {
    "User-Agent": "TCGPriceMovers/0.1"
}

products_url = f"https://tcgcsv.com/tcgplayer/{CATEGORY_ID}/{GROUP_ID}/products"
prices_url = f"https://tcgcsv.com/tcgplayer/{CATEGORY_ID}/{GROUP_ID}/prices"

products = requests.get(products_url, headers=headers).json()["results"]
prices = requests.get(prices_url, headers=headers).json()["results"]

price_lookup = {}

for price in prices:
    product_id = price["productId"]

    # Keep first price entry
    if product_id not in price_lookup:
        price_lookup[product_id] = price

rows = []

for product in products:
    product_id = product["productId"]

    if product_id not in price_lookup:
        continue

    price = price_lookup[product_id]

    rows.append({
        "productId": product_id,
        "name": product["name"],
        "marketPrice": price.get("marketPrice"),
        "lowPrice": price.get("lowPrice"),
        "subType": price.get("subTypeName")
    })

df = pd.DataFrame(rows)

print(df.head(20))

df.to_csv("silver_tempest_prices.csv", index=False)

print()
print(f"Saved {len(df)} products")
