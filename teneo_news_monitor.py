import json
import os
import re
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

NEWS_URL = "https://www.teneo.com/news/"
STATE_FILE = "teneo_news_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "").strip()
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

def scrape_news():
    articles = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        try:
            page.goto(NEWS_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Warning: {e}")
        page.wait_for_timeout(3000)
        links = page.query_selector_all("a")
        for link in links:
            href = link.get_attribute("href") or ""
            title_raw = link.inner_text().strip()
            if not href or "/news/" not in href or href.rstrip("/") == NEWS_URL.rstrip("/"):
                continue
            if not href.startswith("http"):
                href = "https://www.teneo.com" + href
            if not title_raw or len(title_raw) < 15:
                continue
            lines = [l.strip() for l in title_raw.split("\n") if l.strip()]
            category = ""
            title = ""
            snippet = ""
            date_str = datetime.now().strftime("%Y-%m-%d")
            source = "teneo.com"
            if lines:
                if lines[0] in ["Press Release", "Media Coverage"]:
                    category = lines[0]
                    title = lines[1] if len(lines) > 1 else ""
                    snippet = " ".join(lines[2:-1]) if len(lines) > 3 else ""
                    last = lines[-1] if lines else ""
                else:
                    title = lines[0]
                    snippet = " ".join(lines[1:-1]) if len(lines) > 2 else ""
                    last = lines[-1] if lines else ""
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
    for i in range(0, len(payload), 50):
        batch = payload[i:i+50]
        r = requests.post(LOVABLE_URL, json=batch, headers=headers, timeout=30)
        print(f"  Batch {i//50+1}: {r.status_code} {r.text[:80]}")
    return True

def main():
    print("TENEO NEWS MONITOR")
    previous = load_state()
    prev_urls = {a["url"] for a in previous}
    print(f"Scraping {NEWS_URL}...")
    current = scrape_news()
    print(f"Found {len(current)} articles:")
    for a in current[:10]:
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
