#!/usr/bin/env python3
"""Generate accurate hashtag descriptions + nuanced FG Fit scores with creative reasoning.
Uses Gemini to think like a creative marketing director for FibreGuard."""

import json, urllib.request, os, time
from datetime import datetime

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYSTEM_PROMPT = """You are a creative marketing director for FibreGuard — a premium stain-resistant upholstery fabric brand for sofas, chairs, and cushions. Your audience: homeowners, parents with young kids, pet owners, interior design lovers.

Content that naturally works for FibreGuard:
- Stain demos, sofa/chair makeovers, fabric close-ups
- Pet-at-home moments (fur, scratching, muddy paws)
- Family life, kids, toddlers, messy moments
- Cozy living, home aesthetics, interior design
- Cleaning, organising, satisfying before/afters
- Outdoor living, patio, garden furniture

FG Fit Score scale (be a creative marketer — think beyond keywords):
- 9-10: Perfect direct demo (stain removal, furniture, sofa reveal, fabric test)
- 7-8: Strong natural fit — FibreGuard is the obvious product for this audience/moment
- 5-6: Good fit — lifestyle content where FibreGuard slots in naturally
- 3-4: Creative angle needed — stretch but doable and believable
- 1-2: Big reach — only works with humour or very lateral thinking, feels forced
- 0: Truly impossible — zero conceivable connection (political scandals, tragedy, pure celeb drama with no home angle)

IMPORTANT RULES:
- Almost nothing scores 0. Even #punch (viral zoo monkey rejected by mom) scores 1-2 because 'finding comfort' is a lateral hook, even if it's a comedy stretch.
- Think like a creative director: "Could we make a piece of content with this hashtag that feels believable for FibreGuard?"
- Score generously at the low end (1-2) for anything with any conceivable angle
- Be accurate about what the trend is actually about — use audience interests as strong context
- fg_reason must be 1-2 sentences explaining the score in plain English. For high scores: what content angle. For low scores: why it doesn't fit and any thin creative angle.

For each hashtag, you will receive: hashtag name, TikTok industry category, and audience interests."""

def call_gemini(prompt):
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8000,
            "thinkingConfig": {"thinkingBudget": 0}
        }
    }).encode()
    req = urllib.request.Request(GEMINI_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
        return result["candidates"][0]["content"]["parts"][0]["text"]

def process_batch(batch):
    hashtag_lines = []
    for item in batch:
        line = f'#{item["hashtag"]}'
        if item.get("industry"):
            line += f' | Industry: {item["industry"]}'
        if item.get("interests"):
            line += f' | Audience interests: {", ".join(item["interests"][:3])}'
        hashtag_lines.append(line)

    prompt = f"""{SYSTEM_PROMPT}

Analyse each hashtag below. For each one:
1. Identify what the TikTok trend is actually about (use context clues — don't just go by the word)
2. Give a FG Fit score (0-10) using creative marketing thinking
3. Write a fg_reason explaining the score in 1-2 sentences

Hashtags:
{chr(10).join(hashtag_lines)}

Respond ONLY as a valid JSON array (no markdown, no explanation):
[
  {{
    "hashtag": "name_without_hash",
    "about": "What this trend is actually about on TikTok",
    "fg_score": 5,
    "fg_reason": "1-2 sentence explanation of the score and any content angle"
  }}
]"""

    try:
        raw = call_gemini(prompt)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        results = json.loads(raw)
        return {
            r["hashtag"].lstrip("#"): {
                "about": r["about"],
                "fg_score": int(r["fg_score"]),
                "fg_reason": r.get("fg_reason", "")
            }
            for r in results
        }
    except Exception as e:
        print(f"  ⚠️ Batch error: {e}")
        return {}

def main():
    with open(os.path.join(BASE, "fibreguard-v5-data.json")) as f:
        data = json.load(f)
    with open(os.path.join(BASE, "hashtag-descriptions.json")) as f:
        descs = json.load(f)

    # Build unique hashtag map
    all_items = {}
    for cc, items in data["countries"].items():
        for item in items:
            ht = item["hashtag"]
            if ht not in all_items:
                all_items[ht] = item

    to_process = list(all_items.values())
    print(f"Processing {len(to_process)} hashtags in batches of 20...")

    BATCH_SIZE = 20
    updated = 0
    errors = 0

    for i in range(0, len(to_process), BATCH_SIZE):
        batch = to_process[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(to_process) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Batch {batch_num}/{total_batches}...", flush=True)

        results = process_batch(batch)
        for ht, entry in results.items():
            descs[ht] = entry
            updated += 1

        if not results:
            errors += 1

        if i + BATCH_SIZE < len(to_process):
            time.sleep(1)

    out_path = os.path.join(BASE, "hashtag-descriptions.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(descs, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done! Updated {updated} entries, {errors} batch errors")

    # Verification
    print("\nSample scores:")
    for ht in ["punch", "punchmonkey", "winterloungewear", "lowcortisol", "textiles", "alysaliu"]:
        if ht in descs:
            d = descs[ht]
            print(f"  #{ht} [{d.get('fg_score','?')}/10]: {d.get('about','')}")
            print(f"    → {d.get('fg_reason','')}")

if __name__ == "__main__":
    main()
