import json
import os
import hashlib
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

PEOPLE_URL  = "https://flint-global.com/people/"
STATE_FILE  = "flint_leadership_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY     = os.environ.get("LOVABLE_API_KEY", "")


def scrape_people():
    people = []
    seen   = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
        page.goto(PEOPLE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # All bio links use /team-members/slug/
        cards = page.query_selector_all("a[href*='/team-members/']")
        for card in cards:
            href = card.get_attribute("href") or ""
            if not href:
                continue

            # Name from h3 inside card, title from next sibling text
            name_el = card.query_selector("h3")
            name = name_el.inner_text().strip() if name_el else card.inner_text().strip().split("\n")[0].strip()

            # Title is text after the heading inside the card
            title = ""
            lines = [l.strip() for l in card.inner_text().split("\n") if l.strip()]
            if len(lines) > 1:
                title = lines[-1]  # last line is usually the title

            if not name or name in seen:
                continue
            seen.add(name)

            uid = hashlib.md5(href.encode()).hexdigest()[:12]
            people.append({
                "id":            uid,
                "name":          name,
                "title":         title,
                "url":           href,
                "competitor_id": "flint",
            })

        browser.close()
    return people


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}


def save_state(people):
    with open(STATE_FILE, "w") as f:
        json.dump({p["id"]: p for p in people}, f, indent=2)


def person_hash(p):
    return hashlib.md5(f"{p['name']}|{p['title']}|{p['url']}".encode()).hexdigest()


def diff(old, new):
    events    = []
    now       = datetime.utcnow().isoformat()
    new_by_id = {p["id"]: p for p in new}
    for pid, person in new_by_id.items():
        if pid not in old:
            events.append({"change_type": "added", "detected_at": now, **person})
        elif person_hash(person) != person_hash(old[pid]):
            events.append({"change_type": "updated", "detected_at": now, **person})
    for pid, person in old.items():
        if pid not in new_by_id:
            events.append({"change_type": "removed", "detected_at": now, **person})
    return events


def send_to_lovable(people):
    if not LOVABLE_URL:
        print("  Skipping — LOVABLE_FUNCTION_URL not set.")
        return
    records = [{"name": p["name"], "title": p["title"], "url": p["url"], "competitor_id": "flint"} for p in people]
    headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
    for i in range(0, len(records), 50):
        batch = records[i:i+50]
        wrapped = {"data_type": "leadership", "data": batch}
        r = requests.post(LOVABLE_URL, json=wrapped, headers=headers, timeout=60)
        print(f"  Batch {i//50+1}: {r.status_code} {r.text[:80]}")


def main():
    print(f"[{datetime.now().isoformat()}] Flint leadership monitor starting…")
    people    = scrape_people()
    print(f"  Scraped {len(people)} people")
    for p in people[:5]:
        print(f"    {p['name']} — {p['title']} — {p['url']}")
    old_state = load_state()
    if not old_state:
        print("  First run — pushing full snapshot…")
        send_to_lovable(people)
    else:
        changes = diff(old_state, people)
        if changes:
            print(f"  {len(changes)} change(s):")
            for c in changes:
                print(f"    [{c['change_type'].upper()}] {c['name']}")
            send_to_lovable(changes)
        else:
            print("  No changes detected.")
    save_state(people)
    print("  Done.")


if __name__ == "__main__":
    main()