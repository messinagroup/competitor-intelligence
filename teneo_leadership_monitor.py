import json
import os
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.teneo.com/people/search-people/"
STATE_FILE = "teneo_leadership_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

SKIP = ["Teneo", "Services", "People", "Insights", "News", "Careers", "Global",
        "Overview", "People Directory", "Global Executive", "Global Management",
        "Senior Advisors", "Business Segments", "Financial Advisory",
        "Management Consulting", "People Advisory", "Risk Advisory",
        "Strategy & Communications", "Practice Areas", "Office Location",
        "All People", "Cookie", "Consent", "Essential", "Preferences",
        "Marketing", "Show details", "Allow", "Skip to", "Board Search",
        "Brand Strategy", "Business Restructuring", "Business Transformation",
        "CEO & C-Suite", "Capital Advisory", "Corporate Affairs", "Corporate Governance",
        "Corporate Insolvency", "Creative", "Crisis Management", "Digital & Social",
        "Employee Engagement", "Energy & Infrastructure", "Enterprise Resilience",
        "Executive Communications", "Executive Search", "Financial Communications",
        "Financial Modeling", "Forensic", "Fund Services", "Geopolitical",
        "Government & Public", "Initial Public", "Litigation", "Macro and Consumer",
        "Merger & Acquisition", "Organizational Performance", "People Strategy",
        "Performance Optimization", "Public Safety", "Purpose, Positioning",
        "Regulatory & Risk", "Reputation Advertising", "Resilience & Intelligence",
        "Restructuring Communications", "Risk Intelligence", "Shareholder Activism",
        "Stakeholder Research", "Strategic Bid", "Strategy Implementation",
        "Sustainability & Governance", "Target Operating", "Teneo Performance",
        "Transaction Support", "Value Creation", "Next", "Previous", "Load more",
        "© 2026", "Terms", "Privacy", "Regulatory Information"]

TITLES = ["President", "Managing Director", "Senior Managing Director", "Director",
          "Vice President", "Senior Vice President", "Associate", "Manager",
          "Consultant", "Partner", "Chief", "Co-Founder", "Chairman", "Officer",
          "Head", "Principal", "Advisor", "Founder", "Executive"]

def scrape_people():
    people = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for page_num in range(1, 31):
            url = BASE_URL if page_num == 1 else f"https://www.teneo.com/people/search-people/page/{page_num}/"
            page.goto(url, wait_until="networkidle")
            print(f"    Scraping page {page_num}/30...")
            page.wait_for_timeout(1000)
            lines = [l.strip() for l in page.inner_text("body").split("\n") if l.strip()]
            i = 0
            while i < len(lines):
                line = lines[i]
                if any(s.lower() == line.lower() for s in SKIP):
                    i += 1
                    continue
                # Check if next line looks like a title
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if any(t.lower() in next_line.lower() for t in TITLES):
                        people.append({
                            "name": line,
                            "title": next_line,
                            
                            "competitor_id": "teneo",
                            "url": f"https://www.teneo.com/people/{line.lower().replace(' ', '-')}/"
                        })
                        i += 2
                        continue
                i += 1

        browser.close()
    # Deduplicate
    seen = set()
    unique = []
    for p in people:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique.append(p)
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
    # Send in batches of 50
    for i in range(0, len(payload), 50):
        batch = payload[i:i+50]
        r = requests.post(LOVABLE_URL, json=batch, headers=headers, timeout=30)
        print(f"  Batch {i//50 + 1}: {r.status_code} {r.text[:80]}")
    return True

def main():
    print("TENEO LEADERSHIP MONITOR")
    previous = load_state()
    prev_names = {p["name"] for p in previous}
    print("Scraping people directory...")
    current = scrape_people()
    print(f"Found {len(current)} people")
    new_people = [p for p in current if p["name"] not in prev_names]
    removed = [p for p in previous if p["name"] not in {c["name"] for c in current}]
    if not previous:
        print(f"First run - sending all {len(current)} people...")
        send_to_lovable(current)
    elif new_people:
        print(f"{len(new_people)} new people found")
        send_to_lovable(new_people)
    else:
        print("No changes detected")
    if removed:
        print(f"{len(removed)} removed")
    save_state(current)
    print("Done")

if __name__ == "__main__":
    main()
