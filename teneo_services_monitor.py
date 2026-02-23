import json
import os
import requests
from playwright.sync_api import sync_playwright

SERVICES_URL = "https://www.teneo.com/services/"
STATE_FILE = "teneo_services_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

REAL_SERVICES = [
    "Board Search & Effectiveness","Brand Strategy & Corporate Positioning",
    "Business Restructuring","Business Transformation","CEO & C-Suite Strategic Counsel",
    "Capital Advisory","Corporate Affairs Function Transformation","Corporate Governance Advisory",
    "Corporate Insolvency & Bankruptcy","Creative","Crisis Management & Preparedness",
    "Digital & Social Media Advisory","Employee Engagement & Change Management",
    "Energy & Infrastructure","Enterprise Resilience & Security Solutions",
    "Executive Communications Coaching & Media Training","Executive Search",
    "Financial Communications & Investor Relations Services","Financial Modeling",
    "Forensic","Fund Services","Geopolitical Risk","Government & Public Affairs",
    "Initial Public Offering Advisory","Litigation & Enforcement Action",
    "Litigation Communications","Macro and Consumer Economics and Demand Forecasting",
    "Merger & Acquisition Advisory","Organizational Performance","People Strategy",
    "Performance Optimization","Public Safety","Purpose, Positioning & Narrative",
    "Regulatory & Risk Advisory Services","Reputation Advertising & Campaigning",
    "Resilience & Intelligence","Restructuring Communications","Risk Intelligence",
    "Shareholder Activism Defense","Stakeholder Research & Analytics",
    "Strategic Bid Support","Strategy Implementation",
    "Sustainability & Governance Advisory Offering","Target Operating Model Design",
    "Transaction Support","Value Creation"
]

def scrape_services():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SERVICES_URL, wait_until="networkidle")
        content = page.inner_text("body")
        browser.close()
    found = []
    for svc in REAL_SERVICES:
        if svc in content:
            found.append({"name": svc, "description": f"Teneo {svc} practice", "competitor_id": "teneo", "url": SERVICES_URL})
    return found

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
    print("🛠️  TENEO SERVICES MONITOR")
    print("=" * 50)
    previous = load_state()
    prev_names = {s["name"] for s in previous}
    print(f"\n🔍 Scraping {SERVICES_URL}...")
    current = scrape_services()
    print(f"✅ Found {len(current)} services")
    new_services = [s for s in current if s["name"] not in prev_names]
    removed = [s for s in previous if s["name"] not in {c["name"] for c in current}]
    if new_services:
        print(f"\n🆕 {len(new_services)} new service(s)")
        send_to_lovable(new_services)
    elif not previous:
        print(f"\n🆕 First run — sending all {len(current)} services...")
        send_to_lovable(current)
    else:
        print("\n✓ No changes detected")
    if removed:
        print(f"\n🗑️  {len(removed)} removed:")
        for s in removed:
            print(f"  - {s['name']}")
    save_state(current)
    print("\n✅ Done")

if __name__ == "__main__":
    main()
