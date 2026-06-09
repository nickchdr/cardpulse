import os
import requests
import pandas as pd
import sqlite3
import streamlit as st
from datetime import date

st.set_page_config(page_title="Live TCG Price Tracker", page_icon="📈", layout="wide")

st.markdown("""
<style>
/* TCG MODERN STYLE */
.block-container {
    padding-top: 1.4rem;
    max-width: 1500px;
}
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
}
[data-testid="stHeader"] {
    background: rgba(255,255,255,0);
}
.hero {
    padding: 26px 30px;
    border-radius: 22px;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 55%, #334155 100%);
    color: white;
    margin-bottom: 20px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.18);
}
.hero h1 {
    margin: 0;
    font-size: 2.4rem;
    letter-spacing: -0.04em;
}
.hero p {
    margin-top: 8px;
    color: #cbd5e1;
    font-size: 1rem;
}
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e5e7eb;
    padding: 16px;
    border-radius: 18px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    background: white;
    border-radius: 999px;
    padding: 10px 18px;
    border: 1px solid #e5e7eb;
}
.stTabs [aria-selected="true"] {
    background: #0f172a !important;
    color: white !important;
}
div[data-testid="stDataFrame"] {
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid #e5e7eb;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}
</style>
""", unsafe_allow_html=True)


TCG_HEADERS = {"User-Agent": "TCGPriceMovers/0.1"}

LIVE_WATCHLIST_FILE = "live_watchlist.csv"
LIVE_INVENTORY_FILE = "live_inventory.csv"
LIVE_HISTORY_FILE = "live_price_history.csv"

st.markdown("""
<div class="hero">
    <h1>📈 Live TCG Market Intelligence</h1>
    <p>Historical Pokémon price movement, buyer signals, live search, inventory repricing, and market opportunity tracking.</p>
</div>
""", unsafe_allow_html=True)

def money(x):
    if pd.isna(x):
        return "—"
    return f"${float(x):,.2f}"

def signed_money(x):
    if pd.isna(x):
        return "—"
    x = float(x)
    return f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}"

def read_csv(path, cols):
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)
    return pd.read_csv(path)

def save_csv(path, df):
    df.to_csv(path, index=False)

def ext(card, key):
    for item in card.get("extendedData", []):
        if item.get("name") == key:
            return item.get("value", "")
    return ""

def product_key(row):
    return f"{row['Name']} | {row['Set']} | {row['Number']} | {row['Finish']}"

@st.cache_data(ttl=3600)
def groups():
    return requests.get("https://tcgcsv.com/tcgplayer/3/groups", headers=TCG_HEADERS, timeout=20).json()["results"]

@st.cache_data(ttl=3600)
def products(group_id):
    return requests.get(f"https://tcgcsv.com/tcgplayer/3/{group_id}/products", headers=TCG_HEADERS, timeout=20).json()["results"]

@st.cache_data(ttl=3600)
def prices(group_id):
    return requests.get(f"https://tcgcsv.com/tcgplayer/3/{group_id}/prices", headers=TCG_HEADERS, timeout=20).json()["results"]

watchlist = read_csv(LIVE_WATCHLIST_FILE, ["product_id", "name", "set_name", "number", "rarity", "finish", "market_price", "low_price", "group_id", "tcg_product_id"])
inventory = read_csv(LIVE_INVENTORY_FILE, ["product_id", "name", "set_name", "number", "rarity", "finish", "qty", "sticker_price", "market_price", "low_price", "group_id", "tcg_product_id"])
history = read_csv(LIVE_HISTORY_FILE, ["date", "product_id", "name", "set_name", "number", "rarity", "finish", "market_price", "low_price", "group_id", "tcg_product_id"])

inventory["qty"] = pd.to_numeric(inventory.get("qty", 0), errors="coerce").fillna(0)
inventory["sticker_price"] = pd.to_numeric(inventory.get("sticker_price", 0), errors="coerce").fillna(0)
inventory["market_price"] = pd.to_numeric(inventory.get("market_price", 0), errors="coerce")
inventory["market_value"] = inventory["qty"] * inventory["market_price"]
inventory["sticker_vs_market"] = inventory["market_price"] - inventory["sticker_price"]
inventory["potential_gain"] = inventory["sticker_vs_market"] * inventory["qty"]

tab_home, tab_search, tab_watchlist, tab_inventory, tab_repricing, tab_snapshots, tab_movers = st.tabs([
    "🏠 Home",
    "🔍 Live Search",
    "⭐ Watchlist",
    "📦 Inventory",
    "💰 Repricing",
    "📸 Snapshots",
    "🔥 Live Movers"
])

with tab_home:
    st.subheader("🏠 Live Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Watchlist Items", len(watchlist))
    c2.metric("Inventory Items", len(inventory))
    c3.metric("Inventory Value", money(inventory["market_value"].sum() if len(inventory) else 0))
    c4.metric("Potential Gain", signed_money(inventory["potential_gain"].sum() if len(inventory) else 0))

    st.markdown("### Top Repricing Opportunities")
    if len(inventory):
        show = inventory.sort_values("potential_gain", ascending=False).head(10).copy()
        show = show.rename(columns={
            "name": "Name", "set_name": "Set", "number": "Number", "finish": "Finish",
            "qty": "Qty", "sticker_price": "Sticker", "market_price": "Market",
            "sticker_vs_market": "Gain Each", "potential_gain": "Total Gain"
        })
        show["Sticker"] = show["Sticker"].apply(money)
        show["Market"] = show["Market"].apply(money)
        show["Gain Each"] = show["Gain Each"].apply(signed_money)
        show["Total Gain"] = show["Total Gain"].apply(signed_money)
        st.dataframe(show[["Name", "Set", "Number", "Finish", "Qty", "Sticker", "Market", "Gain Each", "Total Gain"]], use_container_width=True)
    else:
        st.info("Add live inventory items to see repricing opportunities.")

with tab_search:
    st.subheader("🔍 Live Product Search")

    col1, col2, col3 = st.columns([2, 2, 1])
    query = col1.text_input("Product name", placeholder="Umbreon VMAX")
    set_filter = col2.text_input("Set filter", placeholder="Evolving")
    max_sets = col3.number_input("Max sets", min_value=5, max_value=216, value=40)

    if query:
        all_groups = groups()
        if set_filter:
            all_groups = [g for g in all_groups if set_filter.lower() in g["name"].lower()]
        else:
            all_groups = all_groups[:int(max_sets)]

        results = []

        with st.spinner("Searching live TCGCSV..."):
            for group in all_groups:
                try:
                    group_id = group["groupId"]
                    product_list = products(group_id)
                    price_list = prices(group_id)

                    price_lookup = {}
                    for p in price_list:
                        if p["productId"] not in price_lookup:
                            price_lookup[p["productId"]] = p

                    for card in product_list:
                        if query.lower() in card["name"].lower():
                            price = price_lookup.get(card["productId"], {})
                            results.append({
                                "Display": f"{card['name']} | {group['name']} | {ext(card, 'Number')} | {price.get('subTypeName', '')}",
                                "Name": card["name"],
                                "Set": group["name"],
                                "Number": ext(card, "Number"),
                                "Rarity": ext(card, "Rarity"),
                                "Finish": price.get("subTypeName", ""),
                                "Market Price": price.get("marketPrice"),
                                "Low Price": price.get("lowPrice"),
                                "Group ID": group_id,
                                "TCG Product ID": card["productId"]
                            })
                except Exception:
                    pass

        if results:
            results_df = pd.DataFrame(results)
            display = results_df.drop(columns=["Display"]).copy()
            display["Market Price"] = display["Market Price"].apply(money)
            display["Low Price"] = display["Low Price"].apply(money)
            st.dataframe(display, use_container_width=True)

            selected = st.selectbox("Choose product", results_df["Display"].tolist())
            row = results_df[results_df["Display"] == selected].iloc[0].to_dict()
            key = product_key(row)

            st.markdown("### 📊 Product Detail")
            d1, d2, d3 = st.columns(3)
            d1.metric("Market Price", money(row["Market Price"]))
            d2.metric("Low Price", money(row["Low Price"]))
            d3.metric("TCG Product ID", row["TCG Product ID"])

            st.write(f"**Name:** {row['Name']}")
            st.write(f"**Set:** {row['Set']}")
            st.write(f"**Number:** {row['Number']}")
            st.write(f"**Rarity:** {row['Rarity']}")
            st.write(f"**Finish:** {row['Finish']}")

            b1, b2 = st.columns(2)

            if b1.button("⭐ Add to Watchlist"):
                new = pd.DataFrame([{
                    "product_id": key,
                    "name": row["Name"],
                    "set_name": row["Set"],
                    "number": row["Number"],
                    "rarity": row["Rarity"],
                    "finish": row["Finish"],
                    "market_price": row["Market Price"],
                    "low_price": row["Low Price"],
                    "group_id": row["Group ID"],
                    "tcg_product_id": row["TCG Product ID"]
                }])
                existing = read_csv(LIVE_WATCHLIST_FILE, new.columns.tolist())
                existing = existing[existing["product_id"] != key]
                save_csv(LIVE_WATCHLIST_FILE, pd.concat([existing, new], ignore_index=True))
                st.success("Added to watchlist.")
                st.rerun()

            with b2:
                qty = st.number_input("Qty owned", min_value=0, value=1)
                sticker_default = float(row["Market Price"]) if pd.notna(row["Market Price"]) else 0.0
                sticker = st.number_input("Sticker price", min_value=0.0, value=sticker_default, step=1.0)

                if st.button("📦 Save to Inventory"):
                    new = pd.DataFrame([{
                        "product_id": key,
                        "name": row["Name"],
                        "set_name": row["Set"],
                        "number": row["Number"],
                        "rarity": row["Rarity"],
                        "finish": row["Finish"],
                        "qty": qty,
                        "sticker_price": sticker,
                        "market_price": row["Market Price"],
                        "low_price": row["Low Price"],
                        "group_id": row["Group ID"],
                        "tcg_product_id": row["TCG Product ID"]
                    }])
                    existing = read_csv(LIVE_INVENTORY_FILE, new.columns.tolist())
                    existing = existing[existing["product_id"] != key]
                    save_csv(LIVE_INVENTORY_FILE, pd.concat([existing, new], ignore_index=True))
                    st.success("Saved to inventory.")
                    st.rerun()
        else:
            st.info("No products found.")

with tab_watchlist:
    st.subheader("⭐ Live Watchlist")
    if len(watchlist):
        show = watchlist.copy()
        show = show.rename(columns={"name": "Name", "set_name": "Set", "number": "Number", "rarity": "Rarity", "finish": "Finish", "market_price": "Market", "low_price": "Low"})
        show["Market"] = show["Market"].apply(money)
        show["Low"] = show["Low"].apply(money)
        st.dataframe(show[["Name", "Set", "Number", "Rarity", "Finish", "Market", "Low"]], use_container_width=True)
    else:
        st.info("No watchlist items yet.")

with tab_inventory:
    st.subheader("📦 Live Inventory")
    if len(inventory):
        show = inventory.copy()
        show = show.rename(columns={"name": "Name", "set_name": "Set", "number": "Number", "rarity": "Rarity", "finish": "Finish", "qty": "Qty", "sticker_price": "Sticker", "market_price": "Market", "sticker_vs_market": "Gain Each", "potential_gain": "Total Gain"})
        show["Sticker"] = show["Sticker"].apply(money)
        show["Market"] = show["Market"].apply(money)
        show["Gain Each"] = show["Gain Each"].apply(signed_money)
        show["Total Gain"] = show["Total Gain"].apply(signed_money)
        st.dataframe(show[["Name", "Set", "Number", "Rarity", "Finish", "Qty", "Sticker", "Market", "Gain Each", "Total Gain"]], use_container_width=True)
    else:
        st.info("No inventory yet.")

with tab_repricing:
    st.subheader("💰 Live Repricing")
    if len(inventory):
        up = inventory[inventory["sticker_vs_market"] > 0].sort_values("potential_gain", ascending=False)
        down = inventory[inventory["sticker_vs_market"] < 0].sort_values("potential_gain")

        c1, c2, c3 = st.columns(3)
        c1.metric("Items to Review", len(inventory))
        c2.metric("Potential Upside", signed_money(up["potential_gain"].sum() if len(up) else 0))
        c3.metric("Potential Downside", signed_money(down["potential_gain"].sum() if len(down) else 0))

        st.markdown("### Reprice Up")
        if len(up):
            show = up.rename(columns={"name": "Name", "set_name": "Set", "number": "Number", "finish": "Finish", "qty": "Qty", "sticker_price": "Sticker", "market_price": "Market", "sticker_vs_market": "Gain Each", "potential_gain": "Total Gain"})
            show["Sticker"] = show["Sticker"].apply(money)
            show["Market"] = show["Market"].apply(money)
            show["Gain Each"] = show["Gain Each"].apply(signed_money)
            show["Total Gain"] = show["Total Gain"].apply(signed_money)
            st.dataframe(show[["Name", "Set", "Number", "Finish", "Qty", "Sticker", "Market", "Gain Each", "Total Gain"]], use_container_width=True)
        else:
            st.info("No underpriced inventory.")

        st.markdown("### Reprice Down")
        if len(down):
            show = down.rename(columns={"name": "Name", "set_name": "Set", "number": "Number", "finish": "Finish", "qty": "Qty", "sticker_price": "Sticker", "market_price": "Market", "sticker_vs_market": "Gain Each", "potential_gain": "Total Gain"})
            show["Sticker"] = show["Sticker"].apply(money)
            show["Market"] = show["Market"].apply(money)
            show["Gain Each"] = show["Gain Each"].apply(signed_money)
            show["Total Gain"] = show["Total Gain"].apply(signed_money)
            st.dataframe(show[["Name", "Set", "Number", "Finish", "Qty", "Sticker", "Market", "Gain Each", "Total Gain"]], use_container_width=True)
        else:
            st.info("No overpriced inventory.")
    else:
        st.info("No inventory yet.")

with tab_snapshots:
    st.subheader("📸 Save Live Price Snapshot")
    st.write("This saves current watchlist and inventory prices into live_price_history.csv. Run this daily to build real movers.")

    if st.button("Save Snapshot Now"):
        tracked = pd.concat([
            watchlist[["product_id", "name", "set_name", "number", "rarity", "finish", "market_price", "low_price", "group_id", "tcg_product_id"]] if len(watchlist) else pd.DataFrame(),
            inventory[["product_id", "name", "set_name", "number", "rarity", "finish", "market_price", "low_price", "group_id", "tcg_product_id"]] if len(inventory) else pd.DataFrame()
        ], ignore_index=True).drop_duplicates("product_id")

        rows = []
        for _, item in tracked.iterrows():
            try:
                price_list = prices(int(item["group_id"]))
                matched = [p for p in price_list if int(p["productId"]) == int(item["tcg_product_id"])]
                if matched:
                    p = matched[0]
                    rows.append({
                        "date": str(date.today()),
                        "product_id": item["product_id"],
                        "name": item["name"],
                        "set_name": item["set_name"],
                        "number": item["number"],
                        "rarity": item["rarity"],
                        "finish": item["finish"],
                        "market_price": p.get("marketPrice"),
                        "low_price": p.get("lowPrice"),
                        "group_id": item["group_id"],
                        "tcg_product_id": item["tcg_product_id"]
                    })
            except Exception:
                pass

        if rows:
            old = read_csv(LIVE_HISTORY_FILE, ["date", "product_id", "name", "set_name", "number", "rarity", "finish", "market_price", "low_price", "group_id", "tcg_product_id"])
            new_history = pd.concat([old, pd.DataFrame(rows)], ignore_index=True)
            new_history = new_history.drop_duplicates(["date", "product_id"], keep="last")
            save_csv(LIVE_HISTORY_FILE, new_history)
            st.success(f"Saved {len(rows)} live price snapshots.")
        else:
            st.warning("No tracked items to snapshot.")

    if len(history):
        st.dataframe(history.sort_values("date", ascending=False), use_container_width=True)
    else:
        st.info("No snapshots saved yet.")


def detect_product_type(row):
    number = str(row.get("number", "")).strip()
    rarity = str(row.get("rarity", "")).strip()
    name = str(row.get("name", "")).lower()

    sealed_words = [
        "booster box", "booster pack", "elite trainer box", "etb",
        "booster bundle", "collection", "tin", "case", "blister",
        "build & battle", "trainer box", "premium collection",
        "box", "pack", "display"
    ]

    if number and rarity:
        return "Single"

    if any(word in name for word in sealed_words):
        return "Sealed"

    return "Other"

def detect_era(set_name):
    s = str(set_name).lower()

    if "scarlet" in s or "violet" in s or s.startswith("sv") or "paldea" in s or "obsidian" in s or "temporal" in s or "twilight" in s or "surging" in s or "prismatic" in s or "journey together" in s or "destined rivals" in s:
        return "Scarlet & Violet"

    if "swsh" in s or "sword" in s or "shield" in s or "evolving skies" in s or "chilling reign" in s or "fusion strike" in s or "brilliant stars" in s or "silver tempest" in s or "lost origin" in s or "astral radiance" in s or "crown zenith" in s:
        return "Sword & Shield"

    if "sun" in s or "moon" in s or "sm" in s or "hidden fates" in s or "cosmic eclipse" in s or "unbroken bonds" in s or "team up" in s:
        return "Sun & Moon"

    if "xy" in s or "evolutions" in s or "phantom forces" in s or "flashfire" in s or "ancient origins" in s or "roaring skies" in s:
        return "XY"

    if "black" in s or "white" in s or "bw" in s or "plasma" in s or "legendary treasures" in s:
        return "Black & White"

    if "diamond" in s or "pearl" in s or "platinum" in s or "heartgold" in s or "soulsilver" in s or "hgss" in s:
        return "DP/HGSS"

    if "ex" in s or "ruby" in s or "sapphire" in s or "emerald" in s or "firered" in s or "leafgreen" in s:
        return "EX Era"

    if "base" in s or "jungle" in s or "fossil" in s or "rocket" in s or "gym" in s or "neo" in s or "legendary collection" in s or "ecard" in s or "aquapolis" in s or "skyridge" in s:
        return "Vintage/WOTC"

    return "Other/Promo"

with tab_movers:
    st.subheader("🔥 Real Historical Movers")
    st.write("Buyer-grade movers using the full TCGCSV historical archive stored in `tcg_market.db`.")

    top1, top2, top3 = st.columns(3)

    with top1:
        timeframe = st.selectbox(
            "Compare timeframe",
            ["1 Day", "7 Days", "30 Days", "90 Days", "1 Year", "All Time"],
            index=2
        )

    with top2:
        price_source = st.selectbox(
            "Price source",
            ["Market Price", "Low Price", "Direct Low"]
        )

    with top3:
        sort_mode = st.selectbox(
            "Sort by",
            ["Biggest $ gain", "Biggest % gain", "Biggest $ drop", "Biggest % drop"]
        )

    price_column_map = {
        "Market Price": "market_price",
        "Low Price": "low_price",
        "Direct Low": "direct_low_price"
    }

    selected_price_column = price_column_map[price_source]

    filter1, filter2, filter3 = st.columns(3)

    with filter1:
        min_current_price = st.number_input(
            "Minimum current price",
            min_value=0.0,
            value=10.0,
            step=5.0
        )

    with filter2:
        max_previous_price = st.number_input(
            "Maximum previous price",
            min_value=0.0,
            value=0.0,
            step=5.0,
            help="Use 0 for no maximum. Example: set to 50 to find cards that used to be under $50."
        )

    with filter3:
        min_percent_move = st.number_input(
            "Minimum percent move",
            min_value=0.0,
            value=10.0,
            step=5.0
        )

    product_type_filter = st.multiselect(
        "Product type",
        ["Single", "Sealed", "Other"],
        default=["Single", "Sealed"]
    )

    era_filter = st.multiselect(
        "Era / generation",
        [
            "Scarlet & Violet",
            "Sword & Shield",
            "Sun & Moon",
            "XY",
            "Black & White",
            "DP/HGSS",
            "EX Era",
            "Vintage/WOTC",
            "Other/Promo"
        ],
        default=[
            "Scarlet & Violet",
            "Sword & Shield",
            "Sun & Moon",
            "XY",
            "Black & White",
            "DP/HGSS",
            "EX Era"
        ]
    )

    st.caption("Vintage/WOTC is off by default because older TCGPlayer data can be noisy.")

    days_map = {
        "1 Day": 1,
        "7 Days": 7,
        "30 Days": 30,
        "90 Days": 90,
        "1 Year": 365,
        "All Time": None
    }

    days_back = days_map[timeframe]

    try:
        conn = sqlite3.connect("tcg_market.db")

        dates = pd.read_sql_query(
            "SELECT DISTINCT date FROM price_history ORDER BY date",
            conn
        )

        if len(dates) < 2:
            st.info("Not enough historical dates imported yet.")
        else:
            latest_date = dates["date"].max()

            if days_back is None:
                old_date = dates["date"].min()
            else:
                old_date_query = f"""
                    SELECT MAX(date) as old_date
                    FROM price_history
                    WHERE date <= date('{latest_date}', '-{days_back} day')
                """
                old_date = pd.read_sql_query(old_date_query, conn)["old_date"].iloc[0]

                if pd.isna(old_date):
                    old_date = dates["date"].min()

            query = f"""
                SELECT
                    p.name,
                    p.set_name,
                    p.number,
                    p.rarity,
                    new.finish,
                    old.{selected_price_column} AS old_price,
                    new.{selected_price_column} AS current_price,
                    new.{selected_price_column} - old.{selected_price_column} AS dollar_change,
                    ((new.{selected_price_column} - old.{selected_price_column}) / old.{selected_price_column}) * 100 AS percent_change
                FROM price_history new
                JOIN price_history old
                    ON new.product_id = old.product_id
                    AND new.finish = old.finish
                LEFT JOIN products p
                    ON new.product_id = p.product_id
                WHERE new.date = ?
                    AND old.date = ?
                    AND new.{selected_price_column} IS NOT NULL
                    AND old.{selected_price_column} IS NOT NULL
                    AND old.{selected_price_column} > 0
                    AND new.{selected_price_column} >= ?
            """

            params = [latest_date, old_date, min_current_price]

            if max_previous_price > 0:
                query += f" AND old.{selected_price_column} <= ?"
                params.append(max_previous_price)

            movers = pd.read_sql_query(query, conn, params=params)

            movers = movers[
                movers["percent_change"].abs() >= min_percent_move
            ].copy()

            movers["Product Type"] = movers.apply(detect_product_type, axis=1)
            movers["Era"] = movers["set_name"].apply(detect_era)

            movers = movers[
                movers["Product Type"].isin(product_type_filter)
                & movers["Era"].isin(era_filter)
            ].copy()

            if sort_mode == "Biggest $ gain":
                movers = movers.sort_values("dollar_change", ascending=False)
            elif sort_mode == "Biggest % gain":
                movers = movers.sort_values("percent_change", ascending=False)
            elif sort_mode == "Biggest $ drop":
                movers = movers.sort_values("dollar_change", ascending=True)
            else:
                movers = movers.sort_values("percent_change", ascending=True)

            st.caption(f"Comparing {old_date} → {latest_date} using {price_source}")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Matching Movers", len(movers))
            m2.metric("Latest Date", latest_date)
            m3.metric("Compared To", old_date)
            m4.metric("Data Points", f"{len(dates):,}")

            if len(movers):
                show = movers.rename(columns={
                    "name": "Name",
                    "set_name": "Set",
                    "number": "Number",
                    "rarity": "Rarity",
                    "finish": "Finish",
                    "old_price": "Old Price",
                    "current_price": "Current Price",
                    "dollar_change": "$ Change",
                    "percent_change": "% Change"
                })

                table = show[[
                    "Name",
                    "Set",
                    "Number",
                    "Rarity",
                    "Finish",
                    "Product Type",
                    "Era",
                    "Old Price",
                    "Current Price",
                    "$ Change",
                    "% Change"
                ]]

                st.dataframe(
                    table.style.format({
                        "Old Price": "${:,.2f}",
                        "Current Price": "${:,.2f}",
                        "$ Change": lambda x: f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}",
                        "% Change": "{:+.2f}%"
                    }),
                    use_container_width=True,
                    height=650
                )
            else:
                st.info("No movers match those filters.")

        conn.close()

    except Exception as e:
        st.error(f"Could not load historical movers: {e}")
