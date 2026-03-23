import json, os, hashlib, re, requests
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


def parse_display_date(raw):
    """'Mar 13, 2026' → '2026-03-13'. Returns '' on failure."""
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%B %d, %Y", "%b. %d, %Y",
                "%Y-%m-%d", "%B %Y", "%b %Y"):
        try:
            return datetime.strptime(raw.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def fetch_article_date(url):
    """Try to pull a real publication date from an individual article page."""
    try:
        soup = fetch(url)
        # 1. meta tags (most reliable)
        for prop in ("article:published_time", "datePublished", "date"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                d = parse_display_date(tag["content"][:10])
                if d:
                    return d
        # 2. <time> element
        t = soup.find("time")
        if t:
            d = parse_display_date(t.get("datetime", "") or t.get_text(strip=True))
            if d:
                return d
        # 3. prnewswire date line e.g. "March 2, 2026 /PRNewswire/"
        text = soup.get_text(" ", strip=True)
        m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}", text)
        if m:
            d = parse_display_date(m.group(0))
            if d:
                return d
    except Exception:
        pass
    return ""


def date_from_image_url(img_url):
    """Extract YYYY-MM-01 from .../uploads/2025/03/Foo.jpg"""
    m = re.search(r"/uploads/(\d{4})/(\d{2})/", img_url or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-01"
    return datetime.now().strftime("%Y-%m-%d")


def scrape_newsroom():
    items = []
    seen  = set()
    soup  = fetch(NEWSROOM_URL)

    # ── In the News ──────────────────────────────────────────────────────────
    # Structure: <h2><a href="REAL_URL">Title</a></h2>  then  <p>Mon DD, YYYY</p>
    # Section starts after "Capstone In the News" h2 and ends at "Capstone Special Reports"
    in_news_header = soup.find("h2", string=re.compile(r"Capstone In the News", re.I))
    if in_news_header:
        for el in in_news_header.find_all_next():
            if el.name == "h2" and re.search(r"Capstone Special Reports", el.get_text(), re.I):
                break
            if el.name != "h2" or not el.find("a"):
                continue
            a     = el.find("a")
            title = a.get_text(strip=True)
            url   = a.get("href", "").replace("#new_tab", "").strip()
            # Date is in the very next <p> sibling
            date_raw = ""
            nxt = el.find_next_sibling()
            if nxt and nxt.name == "p":
                txt = nxt.get_text(strip=True)
                if re.match(r"[A-Za-z]+ \d+, \d{4}", txt):
                    date_raw = txt
            date_iso = parse_display_date(date_raw) or datetime.now().strftime("%Y-%m-%d")
            uid = hashlib.md5(url.encode()).hexdigest()[:12]
            if uid not in seen:
                seen.add(uid)
                items.append({
                    "id": f"news-{uid}", "section": "in_the_news",
                    "title": title,
                    "snippet": f"Capstone in press | {date_raw}",
                    "published_date": date_iso,
                    "url": url,
                    "competitor_id": "capstone",
                })

    # Paginated older "In the News" entries
    page_url = NEWSROOM_URL
    while True:
        pg = fetch(page_url)
        older = pg.find("a", string=re.compile(r"older", re.I))
        if not older:
            break
        page_url = older["href"]
        pg_header = pg.find("h2", string=re.compile(r"Capstone In the News", re.I))
        if not pg_header:
            break
        for el in pg_header.find_all_next():
            if el.name == "h2" and re.search(r"Capstone Special Reports", el.get_text(), re.I):
                break
            if el.name != "h2" or not el.find("a"):
                continue
            a     = el.find("a")
            title = a.get_text(strip=True)
            url   = a.get("href", "").replace("#new_tab", "").strip()
            date_raw = ""
            nxt = el.find_next_sibling()
            if nxt and nxt.name == "p":
                txt = nxt.get_text(strip=True)
                if re.match(r"[A-Za-z]+ \d+, \d{4}", txt):
                    date_raw = txt
            date_iso = parse_display_date(date_raw) or datetime.now().strftime("%Y-%m-%d")
            uid = hashlib.md5(url.encode()).hexdigest()[:12]
            if uid not in seen:
                seen.add(uid)
                items.append({
                    "id": f"news-{uid}", "section": "in_the_news",
                    "title": title,
                    "snippet": f"Capstone in press | {date_raw}",
                    "published_date": date_iso,
                    "url": url,
                    "competitor_id": "capstone",
                })

    # Re-fetch base page for remaining sections
    soup = fetch(NEWSROOM_URL)

    # ── Special Reports ───────────────────────────────────────────────────────
    reports_header = soup.find("h2", string=re.compile(r"Capstone Special Reports", re.I))
    if reports_header:
        for el in reports_header.find_all_next():
            if el.name == "h2" and re.search(r"Capstone Press Releases", el.get_text(), re.I):
                break
            if el.name != "h2" or not el.find("a"):
                continue
            a     = el.find("a")
            title = a.get_text(strip=True)
            url   = a.get("href", "").replace("#new_tab", "").strip()
            if not url.startswith("http"):
                url = BASE_URL + url
            uid = hashlib.md5(url.encode()).hexdigest()[:12]
            if uid not in seen:
                seen.add(uid)
                date_iso = fetch_article_date(url) or datetime.now().strftime("%Y-%m-%d")
                print(f"    [report] {title[:60]} → {date_iso}")
                items.append({
                    "id": f"report-{uid}", "section": "special_reports",
                    "title": title, "snippet": "Capstone Special Report",
                    "published_date": date_iso,
                    "url": url, "competitor_id": "capstone",
                })

    # ── Press Releases ────────────────────────────────────────────────────────
    pr_header = soup.find("h2", string=re.compile(r"Capstone Press Releases", re.I))
    if pr_header:
        for el in pr_header.find_all_next():
            if el.name == "h2" and re.search(r"Recent Deals", el.get_text(), re.I):
                break
            if el.name != "h2" or not el.find("a"):
                continue
            a     = el.find("a")
            title = a.get_text(strip=True)
            url   = a.get("href", "").replace("#new_tab", "").strip()
            if not url.startswith("http"):
                url = BASE_URL + url
            snippet = "Capstone Press Release"
            nxt = el.find_next_sibling("p")
            if nxt:
                snippet = nxt.get_text(strip=True)[:300]
            uid = hashlib.md5(url.encode()).hexdigest()[:12]
            if uid not in seen:
                seen.add(uid)
                date_iso = fetch_article_date(url) or datetime.now().strftime("%Y-%m-%d")
                print(f"    [pr] {title[:60]} → {date_iso}")
                items.append({
                    "id": f"pr-{uid}", "section": "press_releases",
                    "title": title, "snippet": snippet,
                    "published_date": date_iso,
                    "url": url, "competitor_id": "capstone",
                })

    # ── Recent Deals ──────────────────────────────────────────────────────────
    # FIX 1: Deals have NO article pages. The <a> wraps an <img> and href = image file.
    # FIX 2: Date comes from the WP upload path (YYYY/MM), NOT today's date.
    deals_header = soup.find("h2", string=re.compile(r"Recent Deals", re.I))
    if deals_header:
        for a_tag in deals_header.find_all_next("a"):
            img = a_tag.find("img")
            if not img:
                continue
            img_url = a_tag.get("href", "")
            if "wp-content/uploads" not in img_url:
                continue
            # Title from img alt, or the nearest following h2
            title = img.get("alt", "").strip()
            if not title:
                h2 = a_tag.find_next("h2")
                title = h2.get_text(strip=True) if h2 else "Unknown Deal"
            if not title:
                continue
            date_iso = date_from_image_url(img_url)
            uid = hashlib.md5(title.encode()).hexdigest()[:12]
            if uid not in seen:
                seen.add(uid)
                items.append({
                    "id": f"deal-{uid}", "section": "recent_deals",
                    "title": title,
                    "snippet": "Capstone advised deal",
                    "published_date": date_iso,        # e.g. "2025-03-01"
                    "url": img_url,                    # image URL — no article page exists
                    "competitor_id": "capstone",
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
    if not SUPABASE_URL:
        print("  Skipping push — LOVABLE_FUNCTION_URL not set.")
        return
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