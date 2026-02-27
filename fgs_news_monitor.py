import json
import os
import requests
from playwright.sync_api import sync_playwright

NEWS_URL = "https://fgsglobal.com/insights"
STATE_FILE = "fgs_news_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

SKIP = ["What We Do", "Insights", "About Us", "People", "Join Us", "Contact Us",
        "Unlock your perspective", "IQ Suite", "Radar", "Future Proof Communication",
        "Newsletters", "Podcasts", "Showing all", "Clear Filters", "Load More",
        "View All Offices", "2026 —", "Privacy", "Imprint", "Code of Conduct",
        "English"]

def scrape_news():
    articles = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(NEWS_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        links = page.query_selector_all("a")
        for link in links:
            href = link.get_attribute("href") or ""
            title = link.inner_text().strip().split("\n")[0].strip()
            if not title or len(title) < 15 or "|" in title:
                continue
            if any(s.lower() in title.lower() for s in SKIP):
                continue
            if "/insights/" in href and href != "/insights":
                articles.append({
                    "title": title,
                    "url": f"https://fgsglobal.com{href}" if href.startswith("/") else href,
                    "source_domain": "fgsglobal.com",
                    "published_date": from_page,
                    "competitor_id": "fgs"
                })
        browser.close()
    seen = set()
    unique = []
    for a in articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)
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
    print(f"  {r.status_code} {r.text[:100]}")
    return r.status_code in [200, 201]

def main():
    print("FGS NEWS MONITOR")
    previous = load_state()
    prev_titles = {a["title"] for a in previous}
    print(f"Scraping {NEWS_URL}...")
    current = scrape_news()
    print(f"Found {len(current)} articles:")
    for a in current:
        print(f"  • {a['title'][:60]}")
    new_articles = [a for a in current if a["title"] not in prev_titles]
    if not previous:
        print(f"First run - sending all {len(current)} articles...")
        send_to_lovable(current)
    elif new_articles:
        print(f"{len(new_articles)} new articles:")
        for a in new_articles:
            print(f"  + {a['title'][:60]}")
        send_to_lovable(new_articles)
    else:
        print("No new articles")
    save_state(current)
    print("Done")

if __name__ == "__main__":
    main()
