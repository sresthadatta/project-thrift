"""
eBay Resale Data Scraper — Project-thrift
Pulls active, used-condition listings for 30 target brands (Attainable Luxury /
Premium / Niche tiers) via eBay's official Browse API. Official API = no
bot-detection fights, generous free quota (5,000 calls/day). Saves progress
to disk after every brand so a crash can never wipe out collected data —
just rerun and it resumes where it left off.
"""

import requests
import base64
import time
import json
import os
from ebay_secrets import APP_ID, CERT_ID

# ── Config ────────────────────────────────────────────────

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SAVE_FILE = "ebay_thrift_data.json"
MAX_ITEMS_PER_BRAND = 150
CATEGORY_ID = "169291"  # Women's Bags & Handbags

# (search name, tier)
BRANDS = [
    ("Coach", "attainable luxury"),
    ("Michael Kors", "attainable luxury"),
    ("Marc Jacobs", "attainable luxury"),
    ("Kate Spade", "attainable luxury"),
    ("Tory Burch", "attainable luxury"),
    ("Longchamp", "attainable luxury"),
    ("Furla", "attainable luxury"),
    ("Rebecca Minkoff", "attainable luxury"),
    ("Ted Baker", "attainable luxury"),
    ("Radley", "attainable luxury"),
    ("Gucci", "premium"),
    ("Prada", "premium"),
    ("Dior", "premium"),
    ("Louis Vuitton", "premium"),
    ("Chanel", "premium"),
    ("Burberry", "premium"),
    ("Saint Laurent", "premium"),
    ("Fendi", "premium"),
    ("Balenciaga", "premium"),
    ("Bottega Veneta", "premium"),
    ("Bally", "niche"),
    ("Salvatore Ferragamo", "niche"),
    ("Loewe", "niche"),
    ("Miu Miu", "niche"),
    ("Jimmy Choo", "niche"),
    ("Alexander McQueen", "niche"),
    ("Moschino", "niche"),
    ("Valentino", "niche"),
    ("Marni", "niche"),
    ("Acne Studios", "niche"),
]


# ── Functions ─────────────────────────────────────────────

class RateLimited(Exception):
    """Raised when eBay blocks us after retries — signals the whole run should stop."""
    pass


def get_access_token():
    credentials = base64.b64encode(f"{APP_ID}:{CERT_ID}".encode()).decode()
    response = requests.post(
        TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
    )
    return response.json()["access_token"]


def fetch_brand_page(token, brand_name, offset=0, retries=2):
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }
    params = {
        "q": f"{brand_name} handbag",
        "category_ids": CATEGORY_ID,
        "filter": "conditionIds:{3000|4000|5000|6000}",  # used/pre-owned only
        "limit": 50,
        "offset": offset,
    }
    last_status = None
    for attempt in range(retries):
        response = requests.get(SEARCH_URL, headers=headers, params=params)
        last_status = response.status_code
        if response.status_code == 200:
            return response.json()
        print(f"  retry {attempt + 1} (status {response.status_code})")
        time.sleep(3)
    raise RateLimited(f"blocked after {retries} retries (last status {last_status})")


def fetch_full_brand(token, brand_name, max_items=MAX_ITEMS_PER_BRAND):
    items = []
    offset = 0
    while len(items) < max_items:
        data = fetch_brand_page(token, brand_name, offset=offset)
        batch = data.get("itemSummaries", [])
        if not batch:
            break
        items.extend(batch)
        offset += len(batch)
        if offset >= data.get("total", 0):
            break
        time.sleep(1)  # polite delay between pages
    return items[:max_items]


def load_progress():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    return []


def run_collection():
    """Main loop: pulls all 30 brands, saving to disk after each one. Safe to rerun — resumes."""
    all_items = load_progress()
    done_brands = set(item["brand_name"] for item in all_items)
    print(f"Resuming — already have: {done_brands}" if done_brands else "Starting fresh.")

    token = get_access_token()  # valid for 2 hours

    for brand_name, tier in BRANDS:
        if brand_name in done_brands:
            continue

        try:
            brand_items = fetch_full_brand(token, brand_name)
        except RateLimited as e:
            print(f"\nSTOPPED — {e}")
            print(f"Not pushing further right now. You have {len(all_items)} items saved safely on disk.")
            print("Wait a bit, then just run `all_items = run_collection()` again — it resumes from here.")
            return all_items

        for item in brand_items:
            item["brand_name"] = brand_name
            item["tier"] = tier
        all_items.extend(brand_items)
        print(f"{brand_name}: {len(brand_items)} items  (running total: {len(all_items)})")

        with open(SAVE_FILE, "w") as f:
            json.dump(all_items, f)

        time.sleep(2)  # polite delay between brands

    print(f"\nDONE. TOTAL: {len(all_items)} items collected")
    return all_items