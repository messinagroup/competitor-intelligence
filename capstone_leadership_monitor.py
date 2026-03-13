import json, os, hashlib, requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from pathlib import Path

URL          = "https://capstonedc.com/about/team/"
COMPANY      = "Capstone"
LOCATION     = "Washington, DC"
STATE_FILE   = Path(__file__).parent / "state" / "capstone_leadership_state.json"
SUPABASE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY = os.environ.get("LOVABLE_API_KEY", "")
HEADERS      = {"User-Agent": "Mozilla/5.0"}
SECTION_MAP  = {"leadership": "Leadership", "senior advisers": "Senior Advisers", "team": "Team"}

def scrape_team():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    members = []
    current_section = "Team"
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)
        if text.lower() in SECTION_MAP:
            current_section = SECTION_MAP[text.lower()]
            continue
        anchor = h2.find("a", href=lambda h: h and "/team-member/" in h)
        if not anchor:
            anchor = h2.find_parent("a", href=lambda h: h and "/team-member/" in h)
        if not anchor:
            continue
        slug  = anchor["href"].strip().rstrip("/").split("/")[-1]
        title = ""
        for sib in h2.next_siblings:
            t = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
            if t:
                title = t
                break
        img   = (h2.find_parent() or h2).find("img")
        photo = img["src"].strip() if img and img.get("src") else ""
        members.append({"id": slug, "name": text, "title": title, "section": current_section,
                        "location": LOCATION, "profile": anchor["href"].strip(),
                        "photo": photo, "competitor_id": "capstone"})
    return members

def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

def save_state(members):
    STATE_FILE.write_text(json.dumps({m["id"]: m for m in members}, indent=2))

def member_hash(m):
    return hashlib.md5(f"{m['name']}|{m['title']}|{m['section']}|{m['photo']}".encode()).hexdigest()

def diff(old, new):
    events, now, new_by_id = [], datetime.now(timezone.utc).isoformat(), {m["id"]: m for m in new}
    for mid, member in new_by_id.items():
        if mid not in old:
            events.append({"change_type": "added", "detected_at": now, "source_url": URL, **member})
        elif member_hash(member) != member_hash(old[mid]):
            events.append({"change_type": "updated", "detected_at": now, "source_url": URL, "previous": old[mid], **member})
    for mid, member in old.items():
        if mid not in new_by_id:
            events.append({"change_type": "removed", "detected_at": now, "source_url": URL, **member})
    return events

def push(payload):
    resp = requests.post(SUPABASE_URL,
        headers={"Content-Type": "application/json", "x-api-key": API_KEY},
        json=payload["data"], timeout=30)
    resp.raise_for_status()
    print(f"  ✓ Pushed → {resp.status_code}")

def main():
    print(f"[{datetime.now().isoformat()}] Capstone leadership monitor starting…")
    members   = scrape_team()
    print(f"  Scraped {len(members)} members")
    old_state = load_state()
    if not old_state:
        print("  First run — pushing full snapshot…")
        push({"type": "leadership_snapshot", "competitor_id": "capstone",
              "data": members, "scraped_at": datetime.now(timezone.utc).isoformat()})
    else:
        changes = diff(old_state, members)
        if changes:
            print(f"  {len(changes)} change(s) detected")
            for c in changes:
                print(f"    [{c['change_type'].upper()}] {c['name']} — {c.get('title','')}")
            push({"type": "leadership", "competitor_id": "capstone", "data": changes})
        else:
            print("  No changes detected.")
    save_state(members)
    print("  Done.")

if __name__ == "__main__":
    main()
