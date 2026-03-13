import json, os, hashlib, requests, time
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from pathlib import Path

LISTING_URL  = "https://capstonedc.com/case-studies/"
COMPANY      = "Capstone"
STATE_FILE   = Path(__file__).parent / "state" / "capstone_case_studies_state.json"
SUPABASE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY      = os.environ.get("LOVABLE_API_KEY", "")
HEADERS      = {"User-Agent": "Mozilla/5.0"}

def scrape_featured_description(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Grab first paragraph after "Background" heading
        for h2 in soup.find_all("h2"):
            if "background" in h2.get_text(strip=True).lower():
                parts = []
                for sib in h2.next_siblings:
                    t = sib.get_text(" ", strip=True) if hasattr(sib, "get_text") else ""
                    if t:
                        parts.append(t)
                    if len(parts) >= 2:
                        break
                return " ".join(parts)[:500]
        # Fallback: first <p> in main content
        p = soup.find("article") or soup.find("main") or soup
        first_p = p.find("p")
        return first_p.get_text(" ", strip=True)[:500] if first_p else ""
    except Exception as e:
        print(f"    Warning: could not fetch {url}: {e}")
        return ""

def scrape_case_studies():
    resp = requests.get(LISTING_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    studies = []

    # ── Featured case studies (have individual /case-study/ pages) ──
    for a in soup.find_all("a", href=lambda h: h and "/case-study/" in h):
        title = a.get_text(strip=True)
        if not title:
            img = a.find("img")
            title = img.get("alt", "").strip() if img else ""
        if not title:
            continue
        url  = a["href"].strip()
        slug = url.rstrip("/").split("/")[-1]
        if any(s["id"] == slug for s in studies):
            continue
        print(f"    Fetching featured: {title[:60]}…")
        desc = scrape_featured_description(url)
        time.sleep(1)
        studies.append({
            "id":            slug,
            "title":         title,
            "description":   desc,
            "type":          "featured",
            "url":           url,
            "competitor_id": "capstone",
        })

    # ── Slider case studies (descriptions in modal HTML on same page) ──
    # Modals are h2 tags with "We added value by" or "We helped" nearby
    seen_ids = {s["id"] for s in studies}
    for h2 in soup.find_all("h2"):
        text = h2.get_text(strip=True)
        # Skip nav/section headers
        if not text or len(text) < 5 or text.lower() in ("case studies", "featured case studies", "more case studies", "contact us"):
            continue
        # Must be followed by policy-style bullets
        bullets = []
        for sib in h2.next_siblings:
            t = sib.get_text(" ", strip=True) if hasattr(sib, "get_text") else ""
            if any(k in t.lower() for k in ["predicting", "quantifying", "creating", "predict", "quantify"]):
                bullets.append(t)
            if len(bullets) >= 3:
                break
        if not bullets:
            continue
        slug = text.lower().replace(" ", "-").replace(",", "").replace("'", "")[:60]
        if slug in seen_ids:
            continue
        seen_ids.add(slug)
        studies.append({
            "id":            slug,
            "title":         text,
            "description":   " | ".join(bullets[:3])[:500],
            "type":          "slider",
            "url":           LISTING_URL,
            "competitor_id": "capstone",
        })

    return studies

def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

def save_state(studies):
    STATE_FILE.write_text(json.dumps({s["id"]: s for s in studies}, indent=2))

def study_hash(s):
    return hashlib.md5(f"{s['title']}|{s['type']}|{s['url']}".encode()).hexdigest()

def diff(old, new):
    events, now, new_by_id = [], datetime.now(timezone.utc).isoformat(), {s["id"]: s for s in new}
    for sid, study in new_by_id.items():
        if sid not in old:
            events.append({"change_type": "added", "detected_at": now, **study})
        elif study_hash(study) != study_hash(old[sid]):
            events.append({"change_type": "updated", "detected_at": now, "previous": old[sid], **study})
    for sid, study in old.items():
        if sid not in new_by_id:
            events.append({"change_type": "removed", "detected_at": now, **study})
    return events

def push(studies):
    today = datetime.now().strftime("%Y-%m-%d")
    payload = [{
        "title":          s["title"],
        "snippet":        s.get("description", "")[:300],
        "source_domain":  "capstonedc.com",
        "published_date": today,
        "url":            s["url"],
        "competitor_id":  "capstone",
    } for s in studies]
    for i in range(0, len(payload), 50):
        batch = payload[i:i+50]
        resp = requests.post(SUPABASE_URL,
            headers={"Content-Type": "application/json", "x-api-key": API_KEY},
            json=batch, timeout=30)
        print(f"  Batch {i//50+1}: {resp.status_code} {resp.text[:80]}")

def main():
    print(f"[{datetime.now().isoformat()}] Capstone case studies monitor starting…")
    studies = scrape_case_studies()
    print(f"  Found {len(studies)} case studies ({sum(1 for s in studies if s['type']=='featured')} featured, {sum(1 for s in studies if s['type']=='slider')} slider)")
    old_state = load_state()
    if not old_state:
        print("  First run — pushing all as baseline…")
        push(studies)
    else:
        changes = diff(old_state, studies)
        if changes:
            print(f"  {len(changes)} change(s):")
            for c in changes:
                print(f"    [{c['change_type'].upper()}] {c['title'][:70]}")
            push(changes)
        else:
            print("  No changes detected.")
    save_state(studies)
    print("  Done.")

if __name__ == "__main__":
    main()
