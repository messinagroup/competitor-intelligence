import json
import os
import requests
from playwright.sync_api import sync_playwright

SERVICES_URL = "https://fgsglobal.com/what-we-do"
STATE_FILE = "fgs_services_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

KNOWN_SERVICES = [
    "Crisis & Issues Management", "Crisis Preparedness and Prevention",
    "Compliance and Litigation", "Cybersecurity and Data Privacy",
    "Restructuring and Transformation", "Global Public Affairs",
    "Antitrust and Competition", "Geopolitical Strategy",
    "FDI & Investment Screening",
    "Government, Congressional & Parliamentary Investigations",
    "Legislative, Regulatory & Advocacy Strategy", "Political Due Diligence",
    "Government Representation", "Strategy & Reputation",
    "Board and Executive Communications", "Corporate Strategy & Positioning",
    "Corporate Transformation & Reorganization",
    "Employee Engagement & Workplace Issues", "Future-Proof Communications",
    "Post-Merger Integration",
    "Purpose and Social Impact: Diversity, Equity and Inclusion",
    "Purpose and Social Impact: Environmental, Social and Governance",
    "Transaction & Financial Communications", "Activism Defense",
    "Equity Advisory and Investor Relations", "Capital Markets",
    "Mergers and Acquisitions", "Private Capital",
    "Board & Governance Services", "Board Advisory", "Governance Services",
    "Digital, Data & Creative", "Strategy & Advisory", "Research & Insights",
    "Brand & Creative", "Campaigns & Paid Media", "Product & Tech",
    "Measurement & Monitoring", "Social & Owned Media", "Experiences",
    "Presentation & Media Coaching", "Climate, Energy & Sustainability",
    "Education", "Entertainment & Media", "Financial Services",
    "Food & Agriculture", "Health", "Industrials", "Infrastructure",
    "Mining", "Real Estate", "Retail & Consumer Goods", "Social Impact",
    "Sports", "Tech", "Transportation"
]

def scrape_services():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(SERVICES_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        content = page.inner_text("body")
        browser.close()
    found = []
    for svc in KNOWN_SERVICES:
        if svc in content:
            found.append({
                "name": svc,
                "description": "",
                "competitor_id": "fgs",
                "url": SERVICES_URL
            })
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
        print("LOVABLE_FUNCTION_URL not set")
        return False
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    r = requests.post(LOVABLE_URL, json=payload, headers=headers, timeout=30)
    print(f"  {r.status_code} {r.text[:100]}")
    return r.status_code in [200, 201]

def main():
    print("FGS SERVICES MONITOR")
    previous = load_state()
    prev_names = {s["name"] for s in previous}
    print(f"Scraping {SERVICES_URL}...")
    current = scrape_services()
    print(f"Found {len(current)} services")
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
