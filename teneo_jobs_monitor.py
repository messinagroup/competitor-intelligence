import json
import os
import requests
from playwright.sync_api import sync_playwright

JOBS_URL = "https://www.teneo.com/careers/open-positions/"
STATE_FILE = "teneo_jobs_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "").strip()
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

DEPARTMENTS = ["Strategy & Communications", "Financial Advisory", "Management Consulting",
               "Risk Advisory", "People Advisory", "Corporate", "UK Holdings Limited",
               "Financial Advisory Germany", "Financial Advisory Spain",
               "Strategy & Communications Netherlands"]

SKIP = ["Teneo", "Services", "People", "Insights", "News", "Careers", "Global",
        "Open Positions", "All Business Segments", "All Offices", "Americas",
        "Asia-Pacific", "Europe", "Middle East & Africa", "The Caribbean & Bermuda",
        "Cookie", "Consent", "Allow", "Skip to", "Join Our Team", "Overview",
        "Teneo Benefits", "Explore Open Positions", "LinkedIn Life",
        "New York", "San Francisco", "Beijing", "Hong Kong SAR", "Melbourne",
        "Shanghai", "Singapore", "Sydney", "Amsterdam", "Berlin", "Channel Islands",
        "Frankfurt", "London", "UK Regional", "Riyadh", "Bermuda",
        "British Virgin Islands", "Corporate"]

def scrape_jobs():
    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        try:
            page.goto(JOBS_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Warning: {e}")
        page.wait_for_timeout(3000)
        content = page.inner_text("body")
        browser.close()

    lines = [l.strip() for l in content.split("\n") if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if any(s.lower() == line.lower() for s in SKIP):
            i += 1
            continue
        if i + 1 < len(lines) and lines[i+1] in DEPARTMENTS:
            title = line
            department = lines[i+1]
            location = lines[i+2] if i + 2 < len(lines) else ""
            if location in DEPARTMENTS:
                location = ""
            jobs.append({
                "title": title,
                "location": location,
                "url": JOBS_URL,
                "competitor_id": "teneo"
            })
            i += 3
            continue
        i += 1

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
    for i in range(0, len(payload), 50):
        batch = payload[i:i+50]
        r = requests.post(LOVABLE_URL, json=batch, headers=headers, timeout=30)
        print(f"  Batch {i//50+1}: {r.status_code} {r.text[:80]}")
    return True

def main():
    print("TENEO JOBS MONITOR")
    previous = load_state()
    prev_keys = {f"{j['title']}|{j['location']}" for j in previous}
    print(f"Scraping {JOBS_URL}...")
    current = scrape_jobs()
    print(f"Found {len(current)} jobs:")
    for j in current[:10]:
        print(f"  {j['title']} - {j['location']}")
    if len(current) > 10:
        print(f"  ... and {len(current)-10} more")
    new_jobs = [j for j in current if f"{j['title']}|{j['location']}" not in prev_keys]
    removed = [j for j in previous if f"{j['title']}|{j['location']}" not in {f"{c['title']}|{c['location']}" for c in current}]
    if not previous:
        print(f"First run - sending all {len(current)} jobs...")
        send_to_lovable(current)
    elif new_jobs:
        print(f"{len(new_jobs)} new jobs found")
        send_to_lovable(new_jobs)
    else:
        print("No changes detected")
    if removed:
        print(f"{len(removed)} jobs removed")
    save_state(current)
    print("Done")

if __name__ == "__main__":
    main()
