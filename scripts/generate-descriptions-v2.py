#!/usr/bin/env python3
"""Generate accurate hashtag descriptions + FG Fit scores using Gemini API.
Improved version with better JSON error handling."""

import json, urllib.request, os, time, re
from datetime import datetime

GEMINI_KEY = "AIzaSyBsQAMhp6EQ-J3khEtZDXElJYZbZJN0va4"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FG_CONTEXT = """FibreGuard makes premium stain-resistant upholstery fabric for sofas, chairs, cushions. 
FG Fit Score (0-10):
- 8-10: Direct match (cleaning, stain removal, furniture, sofa/couch, fabric, upholstery)
- 5-7: Strong lifestyle fit (home decor, interior design, family/kids, pets at home, cozy living, home renovation)
- 3-4: Moderate fit (outdoor living/patio, DIY furniture, organization, food/drink spill moments)
- 1-2: Tangential (general lifestyle/home adjacent, comedy with cleaning angle)
- 0: Not relevant (gaming, celebrity news, politics, sports, music trends, dance challenges, animals without home context)"""

def call_gemini(prompt):
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096}
    }).encode()
    req = urllib.request.Request(GEMINI_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
        return result["candidates"][0]["content"]["parts"][0]["text"]

def extract_json_array(text):
    """Try to extract and parse JSON from text, handling malformed responses."""
    text = text.strip()
    
    # Remove markdown code blocks
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    
    # Try direct parse first
    try:
        return json.loads(text)
    except:
        pass
    
    # Try to find JSON array in text
    match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    # Try to extract individual objects and build array
    objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
    if objects:
        valid_objects = []
        for obj_str in objects:
            try:
                valid_objects.append(json.loads(obj_str))
            except:
                pass
        if valid_objects:
            return valid_objects
    
    return None

def process_batch(batch):
    """Process a batch of hashtags with Gemini. Returns dict of {hashtag: {about, fg_score}}."""
    hashtag_lines = []
    for item in batch:
        line = f'#{item["hashtag"]}'
        if item.get("industry"):
            line += f' | Industry: {item["industry"]}'
        if item.get("interests"):
            line += f' | Audience interests: {", ".join(item["interests"][:3])}'
        hashtag_lines.append(line)
    
    prompt = f"""{FG_CONTEXT}

For each hashtag below, identify what the TikTok trend is actually about (based on the hashtag name and context clues) and give an FG Fit score.

IMPORTANT RULES:
- Base your answer on what the hashtag is ACTUALLY trending about on TikTok, not just the literal word meaning
- For example: #punch is about a viral zoo monkey named Punch, NOT boxing
- Use the audience interests as strong context clues about the real topic
- "Other Animals" interest = likely animal/pet content
- "Toys & Collectables" + animal interests = likely viral animal video
- Keep "about" to 1 short sentence (max 10 words)
- Be specific and accurate

Hashtags to analyse:
{chr(10).join(hashtag_lines)}

Respond in valid JSON only, as an array:
[
  {{"hashtag": "name", "about": "one line description", "fg_score": 0}},
  ...
]
No markdown, no explanation, just the JSON array."""

    try:
        raw = call_gemini(prompt)
        results = extract_json_array(raw)
        
        if not results:
            print(f"  ⚠️ Batch parse failed (no JSON found)")
            return {}
        
        output = {}
        for r in results:
            if isinstance(r, dict) and "hashtag" in r:
                output[r["hashtag"]] = {
                    "about": r.get("about", ""),
                    "fg_score": int(r.get("fg_score", 0))
                }
        return output
    except Exception as e:
        print(f"  ⚠️ Batch error: {e}")
        return {}

def main():
    # Load existing data
    with open(os.path.join(BASE, "fibreguard-v5-data.json")) as f:
        data = json.load(f)
    with open(os.path.join(BASE, "hashtag-descriptions.json")) as f:
        descs = json.load(f)
    
    # Build unique hashtag map with all available context
    all_items = {}
    for cc, items in data["countries"].items():
        for item in items:
            ht = item["hashtag"]
            if ht not in all_items:
                all_items[ht] = item
    
    print(f"Total unique hashtags: {len(all_items)}")
    print(f"Already have descriptions: {len(descs)}")
    print(f"Missing: {len(all_items) - len(descs)}")
    
    # Find missing hashtags
    missing = [item for ht, item in all_items.items() if ht not in descs]
    print(f"Processing {len(missing)} missing hashtags in batches of 25...")
    
    BATCH_SIZE = 25
    updated = 0
    errors = 0
    
    for i in range(0, len(missing), BATCH_SIZE):
        batch = missing[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(missing) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} hashtags)...")
        
        results = process_batch(batch)
        
        for ht, entry in results.items():
            descs[ht] = entry
            updated += 1
        
        if not results:
            errors += 1
        
        # Rate limit: pause between batches
        if i + BATCH_SIZE < len(missing):
            time.sleep(2)
    
    # Save
    out_path = os.path.join(BASE, "hashtag-descriptions.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(descs, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Done! Updated {updated} descriptions, {errors} batch errors")
    print(f"Total descriptions now: {len(descs)}")
    print(f"Saved to {out_path}")
    
    # Print sample results
    print("\nSample results:")
    for ht in ["punch", "punchmonkey", "alysaliu", "homedesign", "cleaning", "sofa"]:
        if ht in descs:
            print(f"  #{ht}: {descs[ht]}")

if __name__ == "__main__":
    main()
