import json
import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

NEWS_URL = "https://fgsglobal.com/insights"
STATE_FILE = "fgs_news_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "").strip()
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

        # Click Load More to get all articles
        for _ in range(10):
            try:
                load_more = page.query_selector("text=Load More")
                if not load_more:
                    break
                load_more.click()
                page.wait_for_timeout(1500)
                print("    Loaded more...")
            except:
                break

        links = page.query_selector_all("a")
        today = datetime.now().strftime("%Y-%m-%d")

        for link in links:
            href = link.get_attribute("href") or ""
            if "/insights/" not in href or href.rstrip("/") == "/insights":
                continue

            # Get full card text to extract date
            full_text = link.inner_text().strip()
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            if not lines:
                continue

            title = lines[0]
            if not title or len(title) < 15 or "|" in title:
                continue
            if any(s.lower() in title.lower() for s in SKIP):
                continue

            # Try to extract date from card text
            published_date = today
            for line in lines:
                # Look for date patterns like "March 25, 2026" or "Apr 1, 2026"
                for fmt in ["%B %d, %Y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"]:
                    try:
                        dt = datetime.strptime(line.strip(), fmt)
                        published_date = dt.strftime("%Y-%m-%d")
                        break
                    except:
                        continue

            url = f"https://fgsglobal.com{href}" if href.startswith("/") else href
            articles.append({
                "title": title,
                "url": url,
                "source_domain": "fgsglobal.com",
                "published_date": published_date,
                "competitor_id": "fgs"
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
        print(f"  Batch {i//50+1}: {r.status_code} {r.text[:100]}")
    return True


def main():
    print("FGS NEWS MONITOR")
    previous = load_state()
    prev_urls = {a["url"] for a in previous}
    print(f"Scraping {NEWS_URL}...")
    current = scrape_news()
    print(f"Found {len(current)} articles")
    new_articles = [a for a in current if a["url"] not in prev_urls]
    if not previous:
        print(f"First run - sending all {len(current)} articles...")
        send_to_lovable(current)
    elif new_articles:
        print(f"{len(new_articles)} new articles:")
        for a in new_articles:
            print(f"  + {a['title'][:60]} ({a['published_date']})")
        send_to_lovable(new_articles)
    else:
        print("No new articles")
    save_state(current)
    print("Done")


if __name__ == "__main__":
    main()
