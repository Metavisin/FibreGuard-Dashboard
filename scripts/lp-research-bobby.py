#!/usr/bin/env python3
"""
LP CRM Research Automation v2
Runs hourly from 18:00-08:00 CET
Researches potential LP contacts and adds them to CRM
"""

import json
import os
import re
import requests
from datetime import datetime

WORKSPACE = "/Users/metavision/.openclaw/workspace"
LOG_FILE = f"{WORKSPACE}/memory/lp-cron.log"
DATA_FILE = f"{WORKSPACE}/MVICRM/data.json"
BRAVE_API_KEY = "BSA_HlRZTQYkCURWzCTxvDUmIHt4GPl"

def log(msg):
    """Write to log file"""
    timestamp = datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp}: {msg}\n")
    print(f"{timestamp}: {msg}")

def check_time():
    """Check if we're in research hours (18:00-08:00 CET)"""
    hour = datetime.now().hour
    return hour >= 18 or hour < 8

def search_lp_contacts():
    """Search for potential LP contacts"""
    queries = [
        "crypto family office managing director LinkedIn",
        "digital asset family office investment manager",
        "crypto hedge fund LP investor family office",
        "Web3 investor LinkedIn Singapore Dubai Hong Kong",
    ]
    
    all_results = []
    
    for query in queries:
        log(f"Searching: {query}")
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {"X-Subscription-Token": BRAVE_API_KEY}
            params = {"q": query, "count": 10}
            
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            data = resp.json()
            
            if "web" in data and "results" in data["web"]:
                for r in data["web"]["results"]:
                    result_url = r.get("url", "")
                    if "linkedin.com" in result_url.lower():
                        all_results.append({
                            "title": r.get("title", ""),
                            "url": result_url,
                            "description": r.get("description", ""),
                            "query": query
                        })
        except Exception as e:
            log(f"Search error: {e}")
    
    return all_results

def extract_contact_from_result(result):
    """Extract contact info from search result"""
    title = result.get("title", "")
    url = result.get("url", "")
    desc = result.get("description", "")
    
    # Extract name from title (usually "Name - Role - Company" format)
    parts = title.split(" - ")
    name = parts[0].strip() if parts else ""
    
    # Try to extract role and company
    role = ""
    company = ""
    if len(parts) > 1:
        role = parts[1].strip()
    if len(parts) > 2:
        company = parts[2].strip()
    
    # Extract location from description
    location = "To verify"
    location_match = re.search(r'(Singapore|Hong Kong|Dubai|Abu Dhabi|UAE|Switzerland|UK|London|New York|USA)', desc, re.IGNORECASE)
    if location_match:
        location = location_match.group(1)
    
    # Determine category based on keywords
    category = "other"
    desc_lower = desc.lower()
    if "family office" in desc_lower:
        category = "family_office"
    elif "angel" in desc_lower or "investor" in desc_lower:
        category = "crypto_angel"
    elif "founder" in desc_lower or "ceo" in desc_lower or "cto" in desc_lower:
        category = "founder"
    elif "hedge fund" in desc_lower or "asset management" in desc_lower:
        category = "allocator"
    
    # Clean name (remove common LinkedIn suffixes)
    name = re.sub(r'\s*[-|]\s*LinkedIn.*', '', name)
    name = name.strip()
    
    if not name or len(name) < 3:
        return None
    
    return {
        "name": name,
        "organization": company or "To verify",
        "role": role or "To verify",
        "location": location,
        "linkedin": url,
        "notes": f"Found via search: {result.get('query', '')}. {desc[:150]}",
        "category": category
    }

def load_existing_contacts():
    """Load existing CRM contacts"""
    try:
        with open(DATA_FILE) as f:
            data = json.load(f)
            return data.get("contacts", [])
    except:
        return []

def load_existing_linkedin():
    """Get existing LinkedIn URLs to avoid duplicates"""
    contacts = load_existing_contacts()
    return set(c.get("linkedin", "") for c in contacts if c.get("linkedin"))

def add_contacts_to_crm(new_contacts):
    """Add new contacts to CRM"""
    if not new_contacts:
        log("No new contacts to add")
        return 0
    
    contacts = load_existing_contacts()
    existing_linkedin = load_existing_linkedin()
    
    # Get max ID
    max_id = max([c.get("id", 0) for c in contacts], default=0)
    
    added = 0
    for c in new_contacts:
        # Skip duplicates
        if c["linkedin"] in existing_linkedin:
            continue
        
        max_id += 1
        c["id"] = max_id
        c["region"] = c.get("location", "To verify")
        c["source"] = "Automated LinkedIn research"
        c["email"] = "To verify"
        c["phone"] = "Not publicly available"
        contacts.append(c)
        existing_linkedin.add(c["linkedin"])
        added += 1
        log(f"  Added: {c['name']} - {c['organization']}")
    
    if added > 0:
        with open(DATA_FILE, "w") as f:
            json.dump({"contacts": contacts}, f, indent=2)
    
    log(f"Added {added} new contacts to CRM")
    return added

def main():
    log("=== Starting LP Research Cycle ===")
    
    if not check_time():
        log("Outside research hours (18:00-08:00), skipping")
        return
    
    # Search for LP contacts (LinkedIn profiles)
    results = search_lp_contacts()
    log(f"Found {len(results)} LinkedIn results")
    
    if not results:
        log("No results found")
        return
    
    # Extract contacts from results
    new_contacts = []
    for r in results:
        contact = extract_contact_from_result(r)
        if contact:
            new_contacts.append(contact)
    
    log(f"Extracted {len(new_contacts)} potential contacts")
    
    # Add to CRM
    count = add_contacts_to_crm(new_contacts)
    
    log(f"=== Research complete. Added {count} contacts ===")

if __name__ == "__main__":
    main()
