#!/usr/bin/env python3
"""Fetch TikTok trending hashtags for US + EU countries via Apify api-empire scraper.
Saves combined data for FibreGuard Trend Spotter v5 dashboard."""

import json, sys, time, urllib.request, os
from datetime import datetime

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "APIFY_TOKEN_NOT_SET")
ACTOR = "api-empire~tiktok-trending-hashtags-analytics-scraper"
BASE_URL = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items?token={APIFY_TOKEN}"

# TikTok age level mapping
AGE_MAP = {1: "18-24", 2: "25-34", 3: "35-44", 4: "45-54", 5: "55+"}

COUNTRIES = {
    "US": "United States",
    "FR": "France",
    "DE": "Germany",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "GB": "United Kingdom"
}

def fetch_country(country_code, period="7"):
    """Fetch trending hashtags for a specific country."""
    body = json.dumps({
        "country": country_code,
        "period": str(period)
    }).encode()
    req = urllib.request.Request(BASE_URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
            print(f"  ✅ {country_code}: {len(data)} hashtags")
            return data
    except Exception as e:
        print(f"  ❌ {country_code}: {e}")
        return []

def parse_hashtag(item, country_code):
    """Parse a single hashtag item from the API response."""
    info = item.get("analytics", {}).get("info", item)
    
    # Handle both formats (direct and nested)
    hashtag_name = item.get("hashtag_name") or info.get("hashtag_name", "")
    
    # Age data
    ages = info.get("audience_ages", [])
    age_data = {}
    top_age = None
    top_age_score = 0
    for a in ages:
        level = a.get("age_level", 0)
        score = a.get("score", 0)
        label = AGE_MAP.get(level, f"L{level}")
        age_data[label] = score
        if score > top_age_score:
            top_age_score = score
            top_age = label
    
    # Trend data (7-day)
    trend = info.get("trend", [])
    trend_values = [t.get("value", 0) if isinstance(t, dict) else t for t in trend]
    
    # Direction from last 7 days
    direction = "stable"
    if len(trend_values) >= 3:
        recent = trend_values[-1]
        mid = trend_values[len(trend_values)//2]
        if recent > mid + 0.05:
            direction = "rising"
        elif recent < mid - 0.05:
            direction = "falling"
    
    # Audience interests
    interests = info.get("audience_interests", [])
    top_interests = []
    for i in interests[:3]:
        interest_info = i.get("interest_info", {})
        top_interests.append(interest_info.get("value", ""))
    
    return {
        "hashtag": hashtag_name,
        "country": country_code,
        "views": info.get("video_views", 0),
        "views_7d": info.get("video_views", 0),
        "views_all": info.get("video_views_all", info.get("video_views", 0)),
        "posts": info.get("publish_cnt", 0),
        "posts_all": info.get("publish_cnt_all", info.get("publish_cnt", 0)),
        "rank": info.get("rank", item.get("rank", 0)),
        "promoted": info.get("is_promoted", False),
        "industry": info.get("industry_info", item.get("industryInfo", {})).get("value", ""),
        "direction": direction,
        "trend": trend_values[-7:] if len(trend_values) >= 7 else trend_values,
        "top_age": top_age or "N/A",
        "age_data": age_data,
        "interests": top_interests,
    }

def main():
    output = {
        "version": "v5",
        "fetched": datetime.utcnow().isoformat() + "Z",
        "countries": {},
    }
    
    countries_to_fetch = sys.argv[1:] if len(sys.argv) > 1 else list(COUNTRIES.keys())
    
    for code in countries_to_fetch:
        name = COUNTRIES.get(code, code)
        print(f"📡 Fetching {name} ({code})...")
        raw = fetch_country(code)
        
        parsed = []
        for item in raw:
            h = parse_hashtag(item, code)
            if not h["promoted"]:  # Skip promoted
                parsed.append(h)
        
        # Sort by views descending, take top 50
        parsed.sort(key=lambda x: x["views"], reverse=True)
        output["countries"][code] = parsed[:100]  # Keep 100, dashboard shows 50
        
        if code != countries_to_fetch[-1]:
            print("  ⏳ Waiting 3s to avoid rate limits...")
            time.sleep(3)
    
    # Save
    outpath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fibreguard-v5-data.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    
    total = sum(len(v) for v in output["countries"].values())
    print(f"\n✅ Saved {total} hashtags across {len(output['countries'])} countries to fibreguard-v5-data.json")

if __name__ == "__main__":
    main()
