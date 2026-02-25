import json
import os
import requests
from playwright.sync_api import sync_playwright

PEOPLE_URL = "https://fgsglobal.com/people"
STATE_FILE = "fgs_leadership_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

SKIP = ["What We Do", "Insights", "About Us", "People", "Join Us", "Contact Us",
        "English", "Global", "Load More", "View All Offices", "FGS Global",
        "Privacy", "Imprint", "Code of Conduct", "Preferences", "Decline",
        "Accept", "Skip to main content", "Find a person", "Clear Selection",
        "Showing all positions"]

TITLES = ["Partner", "Managing Director", "Director", "Senior Advisor", "Advisor",
          "Chief", "Head", "Global", "Co-Head", "Co-Global"]

def scrape_people():
    people = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(PEOPLE_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        # Keep clicking Load More until it disappears
        while True:
            try:
                load_more = page.query_selector("text=Load More")
                if not load_more:
                    break
                load_more.click()
                page.wait_for_timeout(1500)
                print("    Loaded more...")
            except:
                break
        lines = [l.strip() for l in page.inner_text("body").split("\n") if l.strip()]
        i = 0
        while i < len(lines):
            line = lines[i]
            if any(s.lower() == line.lower() for s in SKIP):
                i += 1
                continue
            # Check if next line has a title and location
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if any(t.lower() in next_line.lower() for t in TITLES) and "," in next_line:
                    # Split title and location by last comma
                    parts = next_line.rsplit(",", 1)
                    title = parts[0].strip()
                    location = parts[1].strip() if len(parts) > 1 else ""
                    people.append({
                        "name": line,
                        "title": title,
                        "location": location,
                        "competitor_id": "fgs",
                        "url": f"https://fgsglobal.com/people"
                    })
                    i += 2
                    continue
            i += 1
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
        print(f"  Batch {i//50+1}: {r.status_code} {r.text[:80]}")
    return True

def main():
    print("FGS GLOBAL LEADERSHIP MONITOR")
    previous = load_state()
    prev_names = {p["name"] for p in previous}
    print(f"Scraping {PEOPLE_URL}...")
    current = scrape_people()
    print(f"Found {len(current)} people:")
    for p in current[:10]:
        print(f"  {p['name']} - {p['title']} - {p['location']}")
    if len(current) > 10:
        print(f"  ... and {len(current)-10} more")
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
