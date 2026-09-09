"""
Poshmark Resale Data Scraper — Project-thrift
Pulls active listings for 30 target brands (Attainable Luxury / Premium / Niche tiers)
via Poshmark's internal text-search API (/vm-rest/posts), filtered to exact-brand
matches. No auth token needed. Saves progress to disk after every brand so a
crash or rate-limit can never wipe out collected data — just rerun and it
resumes where it left off.
"""

import requests
import time
import json
import os

# ── Config ────────────────────────────────────────────────

URL = "https://poshmark.com/vm-rest/posts"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
}
SAVE_FILE = "poshmark_thrift_data.json"
MAX_ITEMS_PER_BRAND = 150

# (brand name exactly as it appears in Poshmark's brand field, tier)
BRANDS = [
    ("Michael Kors", "attainable luxury"),
    ("Coach", "attainable luxury"),
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
    """Raised when Poshmark blocks us after retries — signals the whole run should stop."""
    pass


def fetch_page(brand_name, max_id=None, retries=2):
    """Fetch one page (48 items) of text-search results for a brand."""
    request_filter = {
        "filters": {"department": "All", "inventory_status": ["available"]},
        "query": brand_name,
        "sort_by": "relevance_v2",
        "experience": "all",
        "sizeSystem": "us",
        "count": "48",
        "static_facets": "false",
    }
    if max_id:
        request_filter["max_id"] = max_id

    params = {
        "request": json.dumps(request_filter),
        "summarize": "true",
        "pm_version": "2026.34.00",
    }

    last_status = None
    for attempt in range(retries):
        response = requests.get(URL, params=params, headers=HEADERS)
        last_status = response.status_code
        if response.status_code == 200 and "data" in response.json():
            return response.json()
        print(f"  retry {attempt + 1} (status {response.status_code})")
        time.sleep(3)
    raise RateLimited(f"blocked after {retries} retries (last status {last_status})")


def fetch_full_brand(brand_name, max_items=MAX_ITEMS_PER_BRAND):
    """Pull up to max_items listings for one brand, filtered to exact-match brand field.
    Raises RateLimited if blocked — caller decides what to do (run_collection stops the whole run)."""
    items = []
    max_id = None
    while len(items) < max_items:
        data = fetch_page(brand_name, max_id=max_id)  # raises RateLimited if blocked
        for obj in data["data"]:
            if obj.get("brand") == brand_name:
                items.append(obj)
        more = data.get("more", {})
        if not more.get("is_next_max_id_present"):
            break
        max_id = more.get("next_max_id")
        time.sleep(1.5)  # polite delay between pages
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

    for brand_name, tier in BRANDS:
        if brand_name in done_brands:
            continue

        try:
            brand_items = fetch_full_brand(brand_name)
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

        time.sleep(8)  # polite delay between brands

    print(f"\nDONE. TOTAL: {len(all_items)} items collected")
    return all_items