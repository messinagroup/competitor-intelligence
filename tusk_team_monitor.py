"""
Tusk Strategies Team Monitor
Scrapes individual bio pages for each team member.
"""

import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

BASE_URL   = "https://tuskstrategies.com"
TEAM_URL   = "https://tuskstrategies.com/our-team/"
STATE_FILE = Path("state/tusk_team_state.json")
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY     = os.environ.get("LOVABLE_API_KEY", "")
HEADERS     = {"User-Agent": "Mozilla/5.0"}


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def scrape_team():
    soup    = fetch(TEAM_URL)
    members = []
    seen    = set()

    # Tusk team cards — find all links pointing to /our-team/* bio pages
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/people/" not in href:
            continue
        if not href.startswith("http"):
            href = BASE_URL + href
        if href in seen:
            continue
        seen.add(href)

        # Name: from the link text or a heading inside
        name = ""
        h_tag = a.find(["h2", "h3", "h4"])
        if h_tag:
            name = h_tag.get_text(strip=True)
        if not name:
            name = a.get_text(strip=True).split("\n")[0].strip()
        if not name:
            continue

        # Title: next <p> or sibling text inside the card
        title = ""
        p_tag = a.find("p")
        if p_tag:
            title = p_tag.get_text(strip=True)

        uid = hashlib.md5(href.encode()).hexdigest()[:12]
        members.append({
            "id":            uid,
            "name":          name,
            "title":         title,
            "location":      "New York, NY",
            "competitor_id": "tusk",
            "url":           href,  # real individual bio page
        })

    return members


def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(members):
    STATE_FILE.write_text(json.dumps({m["id"]: m for m in members}, indent=2))


def member_hash(m):
    return hashlib.md5(f"{m['name']}|{m['title']}|{m['url']}".encode()).hexdigest()


def diff(old, new):
    events, now = [], datetime.utcnow().isoformat()
    new_by_id = {m["id"]: m for m in new}
    for mid, member in new_by_id.items():
        if mid not in old:
            events.append({"change_type": "added", "detected_at": now, **member})
        elif member_hash(member) != member_hash(old[mid]):
            events.append({"change_type": "updated", "detected_at": now, "previous": old[mid], **member})
    for mid, member in old.items():
        if mid not in new_by_id:
            events.append({"change_type": "removed", "detected_at": now, **member})
    return events


def push(members):
    if not LOVABLE_URL:
        print("  Skipping push — LOVABLE_FUNCTION_URL not set.")
        return
    today   = datetime.now().strftime("%Y-%m-%d")
    records = [{"name": m["name"], "title": m["title"], "url": m["url"], "location": m.get("location",""), "competitor_id": "tusk"} for m in members]
    wrapped = {"data_type": "leadership", "data": records}
    headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
    r = requests.post(LOVABLE_URL, json=wrapped, headers=headers, timeout=30)
    print(f"  {r.status_code} {r.text[:100]}")


def main():
    print(f"[{datetime.now().isoformat()}] Tusk team monitor starting…")
    members   = scrape_team()
    print(f"  Scraped {len(members)} members")
    for m in members[:5]:
        print(f"    {m['name']} — {m['url']}")
    old_state = load_state()
    if not old_state:
        print("  First run — pushing full snapshot…")
        push(members)
    else:
        changes = diff(old_state, members)
        if changes:
            print(f"  {len(changes)} change(s) detected")
            for c in changes:
                print(f"    [{c['change_type'].upper()}] {c['name']}")
            push(changes)
        else:
            print("  No changes detected.")
    save_state(members)
    print("  Done.")


if __name__ == "__main__":
    main()