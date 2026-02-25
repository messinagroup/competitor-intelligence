import json
import os
import requests
from playwright.sync_api import sync_playwright

BASE_URL = "https://fgsglobal.com/insights/newsletters/ai-policy-newsletter"
STATE_FILE = "fgs_ai_newsletter_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

def scrape_newsletter_detail(page, url):
    page.goto(f"https://fgsglobal.com{url}", wait_until="networkidle")
    page.wait_for_timeout(1000)
    lines = [l.strip() for l in page.inner_text("body").split("\n") if l.strip()]
    description = ""
    capture = False
    for line in lines:
        if "At a Glance" in line:
            capture = True
            continue
        if capture and line and len(line) > 30:
            if any(x in line for x in ["Download", "Subscribe", "Share", "By ain", "What We Do", "2026 —"]):
                break
            description += line + " "
        if len(description) > 500:
            break
    return description.strip()[:800]

def scrape_newsletters():
    newsletters = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        links = page.query_selector_all("a")
        items = []
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.inner_text().strip()
            if "ai-policy-newsletter/" in href and text:
                title = text.split("\n")[0].strip()
                date = text.split("\n")[1].strip() if "\n" in text else ""
                if "|" in date:
                    date = date.split("|")[0].strip()
                items.append({"title": title, "date": date, "url": href})
        print(f"  Found {len(items)} newsletters, scraping descriptions...")
        for item in items:
            print(f"    {item['title']}...")
            description = scrape_newsletter_detail(page, item["url"])
            newsletters.append({
                "title": item["title"],
                "partner": "FGS Global AI Policy",
                "announcement_date": item["date"],
                "description": description,
                "url": f"https://fgsglobal.com{item['url']}",
                "competitor_id": "fgs"
            })
        browser.close()
    return newsletters

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
    print("FGS AI NEWSLETTER MONITOR")
    previous = load_state()
    prev_titles = {n["title"] for n in previous}
    print(f"Scraping {BASE_URL}...")
    current = scrape_newsletters()
    print(f"Found {len(current)} newsletters")
    new_items = [n for n in current if n["title"] not in prev_titles]
    if not previous:
        print(f"First run - sending all {len(current)} newsletters...")
        send_to_lovable(current)
    elif new_items:
        print(f"{len(new_items)} new newsletter(s):")
        for n in new_items:
            print(f"  + {n['title']}")
        send_to_lovable(new_items)
    else:
        print("No new newsletters")
    save_state(current)
    print("Done")

if __name__ == "__main__":
    main()
