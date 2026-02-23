import json
import os
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

NEWS_URL = "https://tuskstrategies.com/news/"
STATE_FILE = "tusk_news_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

SKIP = ["Work with Us", "Culture", "Services", "Wins", "Our Team",
        "Privacy", "Skip to", "Menu", "Close", "Allow", "Latest"]

def scrape_news():
    articles = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(NEWS_URL, wait_until="networkidle")
        links = page.query_selector_all("a")
        for link in links:
            title = link.inner_text().strip()
            href = link.get_attribute("href") or ""
            if not title or len(title) < 15:
                continue
            if any(s.lower() in title.lower() for s in SKIP):
                continue
            if not href or href == "#":
                continue
            articles.append({
                "title": title,
                "url": href,
                "source_domain": "tuskstrategies.com",
                "published_date": datetime.now().strftime("%Y-%m-%d"),
                "competitor_id": "tusk"
            })
        browser.close()
    # Deduplicate
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

def save_state(articles):
    with open(STATE_FILE, "w") as f:
        json.dump(articles, f, indent=2)

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
    print("📰 TUSK STRATEGIES NEWS MONITOR")
    print("=" * 50)
    previous = load_state()
    prev_titles = {a["title"] for a in previous}
    print(f"\n🔍 Scraping {NEWS_URL}...")
    current = scrape_news()
    print(f"✅ Found {len(current)} articles:")
    for a in current:
        print(f"  • {a['title']}")
    new_articles = [a for a in current if a["title"] not in prev_titles]
    if new_articles:
        print(f"\n🆕 {len(new_articles)} new article(s):")
        for a in new_articles:
            print(f"  + {a['title']}")
        send_to_lovable(new_articles)
    elif not previous:
        print(f"\n🆕 First run — sending all {len(current)} articles...")
        send_to_lovable(current)
    else:
        print("\n✓ No new articles detected")
    save_state(current)
    print("\n✅ Done")

if __name__ == "__main__":
    main()
