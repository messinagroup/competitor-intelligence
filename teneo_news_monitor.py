import json
import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

NEWS_URL = "https://www.teneo.com/news/"
STATE_FILE = "teneo_news_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

def scrape_news():
    articles = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(NEWS_URL, wait_until="networkidle")
        links = page.query_selector_all("a")
        for link in links:
            href = link.get_attribute("href") or ""
            title_raw = link.inner_text().strip()
            if not href or "/news/" not in href or href == NEWS_URL:
                continue
            if not title_raw or len(title_raw) < 15:
                continue
            # Split title from date/location
            lines = [l.strip() for l in title_raw.split("\n") if l.strip()]
            # First line may be category (Press Release, Media Coverage)
            category = ""
            title = ""
            snippet = ""
            date_str = datetime.now().strftime("%Y-%m-%d")
            source = "teneo.com"
            if len(lines) >= 1:
                if lines[0] in ["Press Release", "Media Coverage"]:
                    category = lines[0]
                    title = lines[1] if len(lines) > 1 else ""
                    snippet = " ".join(lines[2:-1]) if len(lines) > 3 else ""
                    last = lines[-1] if lines else ""
                else:
                    title = lines[0]
                    snippet = " ".join(lines[1:-1]) if len(lines) > 2 else ""
                    last = lines[-1] if lines else ""
                # Extract date and source from last line
                # Format: "February 23, 2026 Bloomberg"
                import re
                date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,\s+\d{4}', last)
                if date_match:
                    try:
                        date_str = datetime.strptime(date_match.group(), "%B %d, %Y").strftime("%Y-%m-%d")
                        source = last.replace(date_match.group(), "").strip() or "teneo.com"
                    except:
                        pass
            if title:
                articles.append({
                    "title": title,
                    "snippet": snippet[:300] if snippet else category,
                    "source_domain": source if source else "teneo.com",
                    "published_date": date_str,
                    "url": href,
                    "competitor_id": "teneo"
                })
        browser.close()
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
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
        print("LOVABLE_FUNCTION_URL not set")
        return False
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    r = requests.post(LOVABLE_URL, json=payload, headers=headers, timeout=30)
    print(f"  {r.status_code} {r.text}")
    return r.status_code in [200, 201]

def main():
    print("TENEO NEWS MONITOR")
    previous = load_state()
    prev_urls = {a["url"] for a in previous}
    print(f"Scraping {NEWS_URL}...")
    current = scrape_news()
    print(f"Found {len(current)} articles:")
    for a in current:
        print(f"  {a['published_date']} - {a['title'][:60]}")
    new_articles = [a for a in current if a["url"] not in prev_urls]
    if not previous:
        print(f"First run - sending all {len(current)} articles...")
        send_to_lovable(current)
    elif new_articles:
        print(f"{len(new_articles)} new articles found")
        send_to_lovable(new_articles)
    else:
        print("No new articles")
    save_state(current)
    print("Done")

if __name__ == "__main__":
    main()
