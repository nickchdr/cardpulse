import requests

headers = {
    "User-Agent": "TCGPriceMovers/0.1"
}

url = "https://tcgcsv.com/tcgplayer/3/3406/products"

response = requests.get(url, headers=headers)

data = response.json()["results"]

search_term = input("Search Card: ").lower()

matches = []

for card in data:
    if search_term in card["name"].lower():
        matches.append(card)

for card in matches[:20]:
    print()
    print(card["name"])
    print("Product ID:", card["productId"])
