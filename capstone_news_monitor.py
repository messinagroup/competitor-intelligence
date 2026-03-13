import json, os, hashlib, requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from pathlib import Path

BASE_URL     = "https://capstonedc.com"
NEWSROOM_URL = "https://capstonedc.com/newsroom/"
COMPANY      = "Capstone"
STATE_FILE   = Path(__file__).parent / "state" / "capstone_news_state.json"
SUPABASE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY      = os.environ.get("LOVABLE_API_KEY", "")
HEADERS      = {"User-Agent": "Mozilla/5.0"}

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def scrape_newsroom():
    items = []
    seen = set()

    # ── In the News (paginated, class=press-releases) ──
    page_url = NEWSROOM_URL
    while page_url:
        soup = fetch(page_url)
        blog = soup.find("div", class_="press-releases")
        if blog:
            for article in blog.find_all("article"):
                h2 = article.find("h2")
                a  = article.find("a", href=True)
                if not h2 or not a:
                    continue
                title = h2.get_text(strip=True)
                url   = a["href"].strip()
                date_tag = article.find("span", class_="published") or article.find("p", class_="post-meta")
                date  = date_tag.get_text(strip=True) if date_tag else ""
                uid   = hashlib.md5(url.encode()).hexdigest()[:12]
                if uid not in seen:
                    seen.add(uid)
                    items.append({
                        "id": f"news-{uid}", "section": "in_the_news",
                        "title": title, "snippet": f"Capstone in press | {date}",
                        "published_date": date, "url": url, "competitor_id": "capstone",
                    })
        older = soup.find("a", string=lambda t: t and "older" in t.lower())
        page_url = older["href"] if older else None

    soup = fetch(NEWSROOM_URL)
    newsroomblogs = soup.find_all("div", class_="newsroomblog")

    # ── Special Reports (newsroomblog[0]) ──
    if len(newsroomblogs) > 0:
        for article in newsroomblogs[0].find_all("article"):
            h2 = article.find("h2")
            a  = article.find("a", href=True)
            if not h2 or not a:
                continue
            title = h2.get_text(strip=True)
            url   = a["href"].strip()
            if not url.startswith("http"):
                url = BASE_URL + url
            uid = hashlib.md5(url.encode()).hexdigest()[:12]
            items.append({
                "id": f"report-{uid}", "section": "special_reports",
                "title": title, "snippet": "Capstone Special Report",
                "published_date": datetime.now().strftime("%Y-%m-%d"),
                "url": url, "competitor_id": "capstone",
            })

    # ── Press Releases (newsroomblog[1]) ──
    if len(newsroomblogs) > 1:
        for article in newsroomblogs[1].find_all("article"):
            h2 = article.find("h2")
            a  = article.find("a", href=True)
            if not h2 or not a:
                continue
            title = h2.get_text(strip=True)
            url   = a["href"].strip()
            if not url.startswith("http"):
                url = BASE_URL + url
            p = article.find("p")
            snippet = p.get_text(strip=True)[:300] if p else "Capstone Press Release"
            uid = hashlib.md5(url.encode()).hexdigest()[:12]
            items.append({
                "id": f"pr-{uid}", "section": "press_releases",
                "title": title, "snippet": snippet,
                "published_date": datetime.now().strftime("%Y-%m-%d"),
                "url": url, "competitor_id": "capstone",
            })

    # ── Recent Deals (all h2s after "Recent Deals" heading) ──
    deals_h = next((h for h in soup.find_all("h2") if "Recent Deals" in h.get_text(strip=True)), None)
    if deals_h:
        # Walk all h2s in the page after this point
        found = False
        for h2 in soup.find_all("h2"):
            if not found:
                if "Recent Deals" in h2.get_text(strip=True):
                    found = True
                continue
            title = h2.get_text(strip=True)
            if not title or title in ("Contact Us",):
                continue
            # Stop at modal/case study content
            if any(k in title for k in ["Pharmacy", "Infusion", "Generics", "Opioid", "Hospital", "Fertility", "Ambulatory", "Medicare", "Recruiting", "Semiconductor"]):
                break
            a   = h2.find("a")
            url = a["href"].strip() if a else NEWSROOM_URL + "#recent-deals"
            uid = hashlib.md5(title.encode()).hexdigest()[:12]
            items.append({
                "id": f"deal-{uid}", "section": "recent_deals",
                "title": title, "snippet": "Capstone advised deal",
                "published_date": datetime.now().strftime("%Y-%m-%d"),
                "url": url, "competitor_id": "capstone",
            })

    return items

def load_state():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

def save_state(items):
    STATE_FILE.write_text(json.dumps({i["id"]: i for i in items}, indent=2))

def item_hash(i):
    return hashlib.md5(f"{i['title']}|{i['section']}|{i['url']}".encode()).hexdigest()

def diff(old, new):
    events, now, new_by_id = [], datetime.now(timezone.utc).isoformat(), {i["id"]: i for i in new}
    for iid, item in new_by_id.items():
        if iid not in old:
            events.append({"change_type": "added", "detected_at": now, **item})
        elif item_hash(item) != item_hash(old[iid]):
            events.append({"change_type": "updated", "detected_at": now, "previous": old[iid], **item})
    for iid, item in old.items():
        if iid not in new_by_id:
            events.append({"change_type": "removed", "detected_at": now, **item})
    return events

def push(items):
    payload = [{
        "title":          i["title"],
        "snippet":        i.get("snippet", "")[:300],
        "source_domain":  "capstonedc.com",
        "published_date": i.get("published_date", datetime.now().strftime("%Y-%m-%d")),
        "url":            i["url"],
        "competitor_id":  "capstone",
    } for i in items]
    for i in range(0, len(payload), 50):
        batch = payload[i:i+50]
        resp = requests.post(SUPABASE_URL,
            headers={"Content-Type": "application/json", "x-api-key": API_KEY},
            json=batch, timeout=30)
        print(f"  Batch {i//50+1}: {resp.status_code} {resp.text[:80]}")

def main():
    print(f"[{datetime.now().isoformat()}] Capstone news monitor starting…")
    items = scrape_newsroom()
    by_section = {}
    for i in items:
        by_section[i["section"]] = by_section.get(i["section"], 0) + 1
    print(f"  Scraped {len(items)} items: {by_section}")
    old_state = load_state()
    if not old_state:
        print("  First run — pushing all as baseline…")
        push(items)
    else:
        changes = diff(old_state, items)
        if changes:
            print(f"  {len(changes)} change(s):")
            for c in changes:
                print(f"    [{c['change_type'].upper()}] [{c['section']}] {c['title'][:70]}")
            push(changes)
        else:
            print("  No changes detected.")
    save_state(items)
    print("  Done.")

if __name__ == "__main__":
    main()
