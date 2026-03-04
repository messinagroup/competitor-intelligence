import json
import os
import requests
from playwright.sync_api import sync_playwright

SERVICES_URL = "https://flint-global.com/our-services"
STATE_FILE = "flint_services_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

def scrape_services():
    found = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SERVICES_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        links = page.query_selector_all("a")
        for link in links:
            href = link.get_attribute("href") or ""
            name = link.inner_text().strip().split("\n")[0].strip()
            if ("/our-service/" in href or "/our-services/" in href) and name and len(name) > 3:
                found.append({
                    "name": name,
                    "description": "",
                    "competitor_id": "flint",
                    "url": href
                })
        browser.close()
    seen = set()
    unique = []
    for s in found:
        if s["name"] not in seen:
            seen.add(s["name"])
            unique.append(s)
    return unique

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return []

def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f, indent=2)

def send_to_lovable(payload):
    if not LOVABLE_URL:
        print("LOVABLE_FUNCTION_URL not set")
        return False
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    for attempt in range(3):
        try:
            r = requests.post(LOVABLE_URL, json=payload, headers=headers, timeout=60)
            break
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            if attempt == 2: return False
            import time; time.sleep(5)
    print(f"  {r.status_code} {r.text[:100]}")
    return r.status_code in [200, 201]

def main():
    print("FLINT GLOBAL SERVICES MONITOR")
    previous = load_state()
    prev_names = {s["name"] for s in previous}
    print(f"Scraping {SERVICES_URL}...")
    current = scrape_services()
    print(f"Found {len(current)} services:")
    for s in current:
        print(f"  • {s['name']}")
    new_services = [s for s in current if s["name"] not in prev_names]
    removed = [s for s in previous if s["name"] not in {c["name"] for c in current}]
    if not previous:
        print(f"First run - sending all {len(current)} services...")
        send_to_lovable(current)
    elif new_services:
        print(f"{len(new_services)} new services found")
        send_to_lovable(new_services)
    else:
        print("No changes detected")
    if removed:
        print(f"{len(removed)} removed:")
        for s in removed:
            print(f"  - {s['name']}")
    save_state(current)
    print("Done")

if __name__ == "__main__":
    main()
