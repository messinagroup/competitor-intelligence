import json
import os
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

CAREERS_URL = "https://tuskstrategies.com/culture-careers/"
STATE_FILE = "tusk_careers_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

def scrape_careers():
    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(CAREERS_URL, wait_until="networkidle")
        try:
            page.click("text=Jobs", timeout=5000)
            page.wait_for_timeout(1000)
        except:
            pass
        links = page.query_selector_all("a")
        for link in links:
            title = link.inner_text().strip()
            href = link.get_attribute("href") or ""
            if "current-openings" in href and title:
                jobs.append({
                    "title": title,
                    "url": href,
                    "location": "New York, NY",
                    "competitor_id": "tusk",
                    "published_date": datetime.now().strftime("%Y-%m-%d")
                })
        browser.close()
    return jobs

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
        print("⚠️  LOVABLE_FUNCTION_URL not set")
        return False
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    r = requests.post(LOVABLE_URL, json=payload, headers=headers, timeout=30)
    print(f"  → {r.status_code} {r.text}")
    return r.status_code in [200, 201]

def main():
    print("=" * 50)
    print("🏢 TUSK STRATEGIES CAREERS MONITOR")
    print("=" * 50)
    previous = load_state()
    prev_titles = {j["title"] for j in previous}
    print(f"\n🔍 Scraping {CAREERS_URL}...")
    current = scrape_careers()
    print(f"✅ Found {len(current)} jobs:")
    for j in current:
        print(f"  • {j['title']}")
    new_jobs = [j for j in current if j["title"] not in prev_titles]
    removed_jobs = [j for j in previous if j["title"] not in {c["title"] for c in current}]
    if new_jobs:
        print(f"\n🆕 {len(new_jobs)} new job(s):")
        for j in new_jobs:
            print(f"  + {j['title']}")
        send_to_lovable(new_jobs)
    elif not previous:
        print(f"\n🆕 First run — sending all {len(current)} jobs...")
        send_to_lovable(current)
    else:
        print("\n✓ No new jobs detected")
    if removed_jobs:
        print(f"\n🗑️  {len(removed_jobs)} job(s) removed:")
        for j in removed_jobs:
            print(f"  - {j['title']}")
    save_state(current)
    print("\n✅ Done")

if __name__ == "__main__":
    main()
