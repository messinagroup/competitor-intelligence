import json
import os
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

SERVICES_URL = "https://tuskstrategies.com/services/"
STATE_FILE = "tusk_services_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

KNOWN_SERVICES = [
    "Public Affairs Campaigns",
    "Communications",
    "Lobbying",
    "Creative and Paid Media",
    "Crypto and Advanced Tech",
    "Latino Engagement"
]

def scrape_services():
    services = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SERVICES_URL, wait_until="networkidle")
        # Click all + buttons to expand
        buttons = page.query_selector_all("button")
        for btn in buttons:
            try:
                btn.click()
                page.wait_for_timeout(300)
            except:
                pass
        body_text = page.inner_text("body")
        browser.close()

    # Extract each service and any description after it
    lines = [l.strip() for l in body_text.split("\n") if l.strip()]
    for i, line in enumerate(lines):
        if line in KNOWN_SERVICES:
            # Grab next non-empty line as description if it's not another service/nav item
            description = ""
            for j in range(i+1, min(i+5, len(lines))):
                candidate = lines[j]
                if candidate not in KNOWN_SERVICES and len(candidate) > 20 and "©" not in candidate:
                    description = candidate
                    break
            services.append({
                "name": line,
                "description": description or f"Tusk Strategies {line} practice",
                "competitor_id": "tusk",
                "url": SERVICES_URL
            })
    return services

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return []

def save_state(services):
    with open(STATE_FILE, "w") as f:
        json.dump(services, f, indent=2)

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
    print("🛠️  TUSK STRATEGIES SERVICES MONITOR")
    print("=" * 50)
    previous = load_state()
    prev_names = {s["name"] for s in previous}
    print(f"\n🔍 Scraping {SERVICES_URL}...")
    current = scrape_services()
    print(f"✅ Found {len(current)} services:")
    for s in current:
        print(f"  • {s['name']}")
    new_services = [s for s in current if s["name"] not in prev_names]
    removed = [s for s in previous if s["name"] not in {c["name"] for c in current}]
    if new_services:
        print(f"\n🆕 {len(new_services)} new service(s):")
        for s in new_services:
            print(f"  + {s['name']}")
        send_to_lovable(new_services)
    elif not previous:
        print(f"\n🆕 First run — sending all {len(current)} services...")
        send_to_lovable(current)
    else:
        print("\n✓ No changes detected")
    if removed:
        print(f"\n🗑️  {len(removed)} service(s) removed:")
        for s in removed:
            print(f"  - {s['name']}")
    save_state(current)
    print("\n✅ Done")

if __name__ == "__main__":
    main()
