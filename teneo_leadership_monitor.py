import json
import os
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.teneo.com/people/search-people/"
STATE_FILE = "teneo_leadership_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

OFFICES = [
    ("Boston", "boston"), ("Calgary", "calgary"), ("Chicago", "chicago"),
    ("Los Angeles", "los-angeles"), ("Mexico City", "mexico-city"),
    ("Montreal", "montreal"), ("New York", "new-york"),
    ("San Francisco", "san-francisco"), ("Sao Paulo", "sao-paulo"),
    ("Toronto", "toronto"), ("Washington DC", "washington-d-c"),
    ("Beijing", "beijing"), ("Brisbane", "brisbane"), ("Hong Kong", "hong-kong"),
    ("Melbourne", "melbourne"), ("Shanghai", "shangai"), ("Singapore", "singapore"),
    ("Sydney", "sydney"), ("Tokyo", "tokyo"), ("Amsterdam", "amsterdam"),
    ("Berlin", "berlin"), ("Birmingham", "birmingham"), ("Bristol", "bristol"),
    ("Brussels", "brussels"), ("Cardiff", "cardiff"), ("Copenhagen", "copenhagen"),
    ("Dublin", "dublin"), ("Edinburgh", "edinburgh"), ("Frankfurt", "frankfurt"),
    ("Glasgow", "glasgow"), ("Guernsey", "guernsey"), ("Jersey", "jersey"),
    ("Leeds", "leeds"), ("London", "london"), ("Madrid", "madrid"),
    ("Manchester", "manchester"), ("Newcastle", "newcastle"), ("Paris", "paris"),
    ("Abu Dhabi", "abu-dhabi"), ("Doha", "doha"), ("Dubai", "dubai"),
    ("Riyadh", "riyadh"), ("Bermuda", "bermuda"),
    ("British Virgin Islands", "british-virgin-islands"),
    ("Cayman Islands", "cayman-islands")
]

SKIP = ["Teneo", "Services", "People", "Insights", "News", "Careers", "Global",
        "Overview", "People Directory", "Global Executive", "Global Management",
        "Senior Advisors", "Business Segments", "Financial Advisory",
        "Management Consulting", "People Advisory", "Risk Advisory",
        "Strategy & Communications", "Practice Areas", "Office Location",
        "All People", "Cookie", "Consent", "Essential", "Preferences",
        "Marketing", "Show details", "Allow", "Skip to", "Next", "Previous",
        "First", "Last", "Terms", "Privacy", "© 2026"]

TITLES = ["President", "Managing Director", "Senior Managing Director", "Director",
          "Vice President", "Senior Vice President", "Associate", "Manager",
          "Consultant", "Partner", "Chief", "Co-Founder", "Chairman", "Officer",
          "Head", "Principal", "Advisor", "Founder", "Executive"]

def scrape_people():
    people = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for city, slug in OFFICES:
            print(f"    Scraping {city}...")
            page_num = 1
            while True:
                if page_num == 1:
                    url = f"{BASE_URL}?office={slug}"
                else:
                    url = f"{BASE_URL}page/{page_num}/?office={slug}"
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(800)
                lines = [l.strip() for l in page.inner_text("body").split("\n") if l.strip()]
                found_any = False
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if any(s.lower() == line.lower() for s in SKIP):
                        i += 1
                        continue
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        if any(t.lower() in next_line.lower() for t in TITLES):
                            found_any = True
                            people.append({
                                "name": line,
                                "title": next_line,
                                "location": city,
                                "competitor_id": "teneo",
                                "url": f"https://www.teneo.com/people/{line.lower().replace(' ', '-')}/"
                            })
                            i += 2
                            continue
                    i += 1
                next_link = page.query_selector("a[aria-label='Next page']")
                if next_link and found_any:
                    page_num += 1
                else:
                    break
        browser.close()
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
    for i in range(0, len(payload), 50):
        batch = payload[i:i+50]
        r = requests.post(LOVABLE_URL, json=batch, headers=headers, timeout=30)
        print(f"  Batch {i//50 + 1}: {r.status_code} {r.text[:80]}")
    return True

def main():
    print("TENEO LEADERSHIP MONITOR")
    previous = load_state()
    prev_names = {p["name"] for p in previous}
    print("Scraping people by office location...")
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
