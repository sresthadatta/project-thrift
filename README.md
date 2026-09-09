# Project Thrift — Resale Value Analysis

Analysis of resale value retention across 30 handbag brands (attainable luxury, premium, niche tiers), using data collected from eBay and Poshmark APIs.

## What's here
- `ebay_scraper.py` / `poshmark_scraper.py` — data collection scripts
- `combined_thrift_data.csv` — 9,000 cleaned listings across both platforms
- Regression model estimating brand-level price premiums
- Interactive Power BI dashboard with a price-prediction calculator (screenshot coming soon)

## Key finding
Chanel retains the most value by far (~$3,500 median resale). Some "niche" tier brands like Loewe and Miu Miu out-resell "premium" brands like Gucci and Dior — tier labels don't fully predict resale strength.
