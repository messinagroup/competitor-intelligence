import json
import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

CAREERS_URL = "https://fgsglobal.com/join-us/opportunities"
STATE_FILE = "fgs_careers_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

REGIONS = ["North America", "Continental Europe", "United Kingdom",
           "Asia Pacific", "Middle East", "Latin America"]

def scrape_jobs():
    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(CAREERS_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        lines = [l.strip() for l in page.inner_text("body").split("\n") if l.strip()]
        i = 0
        while i < len(lines):
            line = lines[i]
            if "|" in line and any(r in line for r in REGIONS):
                parts = line.split("|")
                date = parts[0].strip()
                location = parts[1].strip() if len(parts) > 1 else ""
                if i + 1 < len(lines):
                    title = lines[i + 1].strip()
                    if title and len(title) > 5:
                        jobs.append({
                            "title": title,
                            "location": location,
                            "url": CAREERS_URL,
                            "published_date": datetime.now().strftime("%Y-%m-%d"),
                            "competitor_id": "fgs"
                        })
                        i += 2
                        continue
            i += 1
        browser.close()
    # Deduplicate
    seen = set()
    unique = []
    for j in jobs:
        key = f"{j['title']}|{j['location']}"
        if key not in seen:
            seen.add(key)
            unique.append(j)
    return unique

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return []

def save_state(jobs):
    with open(STATE_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

def send_to_lovable(payload):
    if not LOVABLE_URL:
        print("LOVABLE_FUNCTION_URL not set")
        return False
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    r = requests.post(LOVABLE_URL, json=payload, headers=headers, timeout=30)
    print(f"  {r.status_code} {r.text[:100]}")
    return r.status_code in [200, 201]

def main():
    print("FGS CAREERS MONITOR")
    previous = load_state()
    prev_keys = {f"{j['title']}|{j['location']}" for j in previous}
    print(f"Scraping {CAREERS_URL}...")
    current = scrape_jobs()
    print(f"Found {len(current)} jobs")
    new_jobs = [j for j in current if f"{j['title']}|{j['location']}" not in prev_keys]
    removed = [j for j in previous if f"{j['title']}|{j['location']}" not in {f"{c['title']}|{c['location']}" for c in current}]
    if not previous:
        print(f"First run - sending all {len(current)} jobs...")
        send_to_lovable(current)
    elif new_jobs:
        print(f"{len(new_jobs)} new jobs found:")
        for j in new_jobs:
            print(f"  + {j['title']} ({j['location']})")
        send_to_lovable(new_jobs)
    else:
        print("No new jobs detected")
    if removed:
        print(f"{len(removed)} jobs removed:")
        for j in removed:
            print(f"  - {j['title']}")
    save_state(current)
    print("Done")

if __name__ == "__main__":
    main()
