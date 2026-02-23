import json
import os
import re
import requests
from playwright.sync_api import sync_playwright

STATE_FILE = "teneo_offices_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

REGIONS = [
    ("americas", "https://www.teneo.com/office-region/americas/"),
    ("asia-pacific", "https://www.teneo.com/office-region/asia-pacific/"),
    ("europe", "https://www.teneo.com/office-region/europe/"),
    ("middle-east-africa", "https://www.teneo.com/office-region/middle-east-africa/"),
    ("caribbean-bermuda", "https://www.teneo.com/office-region/caribbean-bermuda/"),
]

SKIP = ["Teneo", "Services", "People", "Insights", "News", "Careers", "Global",
        "Offices", "Americas", "Asia-Pacific", "Europe", "Middle East",
        "Caribbean", "Cookie", "Consent", "Essential", "Preferences",
        "Marketing", "Show details", "Allow", "Skip to", "Contact Office",
        "Business Segments", "Strategy", "Financial Advisory", "Management",
        "Risk Advisory", "People Advisory", "All Practice", "Regulatory",
        "Terms", "Privacy", "Transparency", "Vendor", "Tax Strategy",
        "© 2026", "All rights"]

def scrape_offices():
    offices = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for region, url in REGIONS:
            print(f"  Scraping {region}...")
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            content = page.inner_text("body")
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            i = 0
            while i < len(lines):
                line = lines[i]
                if any(s.lower() in line.lower() for s in SKIP):
                    i += 1
                    continue
                # Looks like a city name - short, capitalized, no digits
                if (len(line) < 40 and line[0].isupper() and
                    not re.search(r'\d', line) and
                    not line.startswith("+") and
                    "," not in line or line in ["New York", "Washington, D.C.", "Hong Kong SAR",
                    "British Virgin Islands", "São Paulo", "Mexico City",
                    "San Francisco", "Los Angeles"]):
                    city = line
                    address_lines = []
                    j = i + 1
                    while j < len(lines) and j < i + 6:
                        next_line = lines[j]
                        if next_line.startswith("+") or "Contact Office" in next_line:
                            break
                        if any(s.lower() in next_line.lower() for s in SKIP):
                            break
                        if len(next_line) < 40 and next_line[0].isupper() and not re.search(r'\d', next_line):
                            break
                        address_lines.append(next_line)
                        j += 1
                    if address_lines:
                        offices.append({
                            "city": city,
                            "address": ", ".join(address_lines),
                            "region": region,
                            "office_type": "regional",
                            "competitor_id": "teneo"
                        })
                i += 1
            page.close()
        browser.close()
    # Deduplicate by city
    seen = set()
    unique = []
    for o in offices:
        if o["city"] not in seen:
            seen.add(o["city"])
            unique.append(o)
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
    r = requests.post(LOVABLE_URL, json=payload, headers=headers, timeout=30)
    print(f"  {r.status_code} {r.text}")
    return r.status_code in [200, 201]

def main():
    print("TENEO OFFICES MONITOR")
    previous = load_state()
    prev_cities = {o["city"] for o in previous}
    print("Scraping all regions...")
    current = scrape_offices()
    print(f"Found {len(current)} offices:")
    for o in current:
        print(f"  {o['city']} ({o['region']}) - {o['address'][:50]}")
    new_offices = [o for o in current if o["city"] not in prev_cities]
    removed = [o for o in previous if o["city"] not in {c["city"] for c in current}]
    if not previous:
        print(f"First run - sending all {len(current)} offices...")
        send_to_lovable(current)
    elif new_offices:
        print(f"{len(new_offices)} new offices found")
        send_to_lovable(new_offices)
    else:
        print("No changes detected")
    if removed:
        print(f"{len(removed)} removed:")
        for o in removed:
            print(f"  - {o['city']}")
    save_state(current)
    print("Done")

if __name__ == "__main__":
    main()
