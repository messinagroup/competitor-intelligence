import json, os, hashlib, requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from pathlib import Path

URL          = "https://boards.greenhouse.io/capstonedc"
COMPANY      = "Capstone"
STATE_FILE   = Path(__file__).parent / "state" / "capstone_careers_state.json"
SUPABASE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY      = os.environ.get("LOVABLE_API_KEY", "")
HEADERS      = {"User-Agent": "Mozilla/5.0"}

def scrape_jobs():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []
    current_dept = "General"
    for tag in soup.find_all(["h3", "a"]):
        if tag.name == "h3":
            current_dept = tag.get_text(strip=True)
        elif tag.name == "a" and tag.get("href", "").startswith("https://job-boards.greenhouse.io/capstonedc/jobs/"):
            full_text = tag.get_text(strip=True)
            title = full_text.replace("New", "").strip()
            url   = tag["href"].strip()
            job_id = url.rstrip("/").split("/")[-1]
            location = ""
            loc_tag = tag.find_next_sibling()
            if loc_tag:
                location = loc_tag.get_text(strip=True)
            if not location:
                parts = title.rsplit("  ", 1)
                if len(parts) == 2:
                    title, location = parts[0].strip(), parts[1].strip()
            jobs.append({
                "id":          job_id,
                "title":       title,
                "department":  current_dept,
                "location":    location or "Washington, DC",
                "url":         url,
                "competitor_id": "capstone",
            })
    return jobs

def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

def save_state(jobs):
    STATE_FILE.write_text(json.dumps({j["id"]: j for j in jobs}, indent=2))

def job_hash(j):
    return hashlib.md5(f"{j['title']}|{j['department']}|{j['location']}".encode()).hexdigest()

def diff(old, new):
    events, now, new_by_id = [], datetime.now(timezone.utc).isoformat(), {j["id"]: j for j in new}
    for jid, job in new_by_id.items():
        if jid not in old:
            events.append({"change_type": "added", "detected_at": now, **job})
        elif job_hash(job) != job_hash(old[jid]):
            events.append({"change_type": "updated", "detected_at": now, "previous": old[jid], **job})
    for jid, job in old.items():
        if jid not in new_by_id:
            events.append({"change_type": "removed", "detected_at": now, **job})
    return events

def push(jobs):
    today = datetime.now().strftime("%Y-%m-%d")
    payload = [{
        "title":         j["title"],
        "snippet":       f"{j['department']} | {j['location']}",
        "source_domain": "boards.greenhouse.io",
        "published_date": today,
        "url":           j["url"],
        "competitor_id": "capstone",
    } for j in jobs]
    for i in range(0, len(payload), 50):
        batch = payload[i:i+50]
        resp = requests.post(SUPABASE_URL,
            headers={"Content-Type": "application/json", "x-api-key": API_KEY},
            json=batch, timeout=30)
        print(f"  Batch {i//50+1}: {resp.status_code} {resp.text[:80]}")

def main():
    print(f"[{datetime.now().isoformat()}] Capstone careers monitor starting…")
    jobs = scrape_jobs()
    print(f"  Found {len(jobs)} open roles")
    old_state = load_state()
    if not old_state:
        print("  First run — pushing all jobs as baseline…")
        push(jobs)
    else:
        changes = diff(old_state, jobs)
        if changes:
            print(f"  {len(changes)} change(s):")
            for c in changes:
                print(f"    [{c['change_type'].upper()}] {c['title']} — {c.get('location','')}")
            push(changes)
        else:
            print("  No changes detected.")
    save_state(jobs)
    print("  Done.")

if __name__ == "__main__":
    main()
