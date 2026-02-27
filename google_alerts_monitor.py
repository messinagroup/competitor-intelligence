import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re

STATE_FILE = "google_alerts_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")

FEEDS = [
    {
        "name": "Teneo",
        "competitor_id": "teneo",
        "url": "https://www.google.com/alerts/feeds/11374616852366129905/12523797253698245031",
        "filter_out": ["teneo online school", "teneo ai ab", "5jg", "online school"]
    },
    {
        "name": "Tusk Strategies",
        "competitor_id": "tusk",
        "url": "https://www.google.com/alerts/feeds/11374616852366129905/6627976990936379591",
        "filter_out": []
    },
    {
        "name": "FGS Global",
        "competitor_id": "fgs",
        "url": "https://www.google.com/alerts/feeds/11374616852366129905/15812016646041442858",
        "filter_out": []
    }
]

NS = {"atom": "http://www.w3.org/2005/Atom"}

def clean_html(text):
    return re.sub(r'<[^>]+>', '', text).strip()

def extract_real_url(google_url):
    match = re.search(r'url=([^&]+)', google_url)
    if match:
        from urllib.parse import unquote
        return unquote(match.group(1))
    return google_url

def fetch_feed(feed):
    alerts = []
    try:
        r = requests.get(feed["url"], timeout=15)
        root = ET.fromstring(r.content)
        entries = root.findall("atom:entry", NS)
        for entry in entries:
            title = clean_html(entry.findtext("atom:title", "", NS))
            link_el = entry.find("atom:link", NS)
            url = extract_real_url(link_el.get("href", "")) if link_el is not None else ""
            content = clean_html(entry.findtext("atom:content", "", NS))
            published = entry.findtext("atom:published", "", NS)[:10]
            # Filter out irrelevant mentions
            combined = (title + content).lower()
            if any(f.lower() in combined for f in feed["filter_out"]):
                continue
            alerts.append({
                "title": title,
                "snippet": content[:300],
                "url": url,
                "source_domain": re.sub(r'https?://(www\.)?', '', url).split('/')[0],
                "published_date": published,
                "competitor_id": feed["competitor_id"]
            })
    except Exception as e:
        print(f"  Error fetching {feed['name']}: {e}")
    return alerts

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

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
    print("GOOGLE ALERTS MONITOR")
    state = load_state()
    all_new = []
    for feed in FEEDS:
        print(f"\nFetching {feed['name']} alerts...")
        alerts = fetch_feed(feed)
        print(f"  Found {len(alerts)} alerts")
        prev_urls = set(state.get(feed["competitor_id"], []))
        new_alerts = [a for a in alerts if a["url"] not in prev_urls]
        if new_alerts:
            print(f"  {len(new_alerts)} new alerts!")
            for a in new_alerts:
                print(f"    + {a['title'][:60]}")
            all_new.extend(new_alerts)
        else:
            print("  No new alerts")
        state[feed["competitor_id"]] = list(prev_urls | {a["url"] for a in alerts})
    if all_new:
        print(f"\nSending {len(all_new)} new alerts to Lovable...")
        send_to_lovable(all_new)
    else:
        print("\nNo new alerts to send")
    save_state(state)
    print("Done")

if __name__ == "__main__":
    main()
