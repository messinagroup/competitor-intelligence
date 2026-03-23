import json
import os
import hashlib
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

JOBS_URL   = "https://flint-global.com/join-flint/"
STATE_FILE = "flint_jobs_state.json"
LOVABLE_URL = os.environ.get("LOVABLE_FUNCTION_URL", "")
API_KEY     = os.environ.get("LOVABLE_API_KEY", "")


def scrape_jobs():
    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
        page.goto(JOBS_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Find all job listings — each is a heading + location + Apply Now link
        # Structure: h4 (job title) → location text → "Apply Now" link to bamboohr
        seen = set()

        # Grab all Apply Now links — each one is a unique job
        apply_links = page.query_selector_all("a[href*='bamboohr.com/careers']")
        for link in apply_links:
            href = link.get_attribute("href") or ""
            link_text = link.inner_text().strip()

            # Skip non-job links (e.g. Associates "Learn more" link)
            if "Apply Now" not in link_text and "apply" not in link_text.lower():
                continue

            # Walk up to find the job card container
            # Title is in the nearest h4, location in nearby text
            title = ""
            location = ""
            department = ""

            # Look for h4 near this link
            card = link.evaluate_handle("el => el.closest('div, section, li, article')")
            if card:
                card_text = page.evaluate("el => el ? el.innerText : ''", card)
                lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                # Remove "Apply Now" line
                lines = [l for l in lines if "apply now" not in l.lower()]
                if lines:
                    title = lines[0]
                if len(lines) > 1:
                    location = lines[1]

            # Fall back: find nearest h4 on page
            if not title:
                h4 = page.query_selector(f"h4")
                if h4:
                    title = h4.inner_text().strip()

            if not title or title in seen:
                continue
            seen.add(title)

            # Find department from nearest h3
            uid = hashlib.md5(href.encode()).hexdigest()[:12]
            jobs.append({
                "id":             uid,
                "title":          title,
                "location":       location,
                "url":            href,
                "snippet":        f"Flint Global job opening | {location}",
                "published_date": datetime.now().strftime("%Y-%m-%d"),
                "source_domain":  "flint-global.com",
                "competitor_id":  "flint",
            })

        # Parse full page text for job title/location/apply url
        lines = [l.strip() for l in page.inner_text("body").split("\n") if l.strip()]
        dept = ""
        LOCATIONS = {"London", "Brussels", "Washington", "Singapore",
                     "New York", "Remote", "Paris", "Berlin", "Dublin"}
        for i, line in enumerate(lines):
            if line in ("Operations", "Advisory", "Research", "Communications",
                        "Technology", "Associates", "Consulting", "Finance"):
                dept = line
                continue
            if line.lower() == "apply now":
                # Scan backwards for location then title
                location = ""
                title = ""
                for back in range(1, 6):
                    if i - back < 0:
                        break
                    candidate = lines[i - back]
                    if not location and candidate in LOCATIONS:
                        location = candidate
                    elif location and candidate and len(candidate) > 3:
                        title = candidate
                        break
                # Fall back: get href from all bamboohr links
                hrefs = [a.get_attribute("href") for a in page.query_selector_all("a[href*='bamboohr']")]
                href = hrefs[len(jobs)] if len(jobs) < len(hrefs) else JOBS_URL
                uid = hashlib.md5((title or line).encode()).hexdigest()[:12]
                if title and title not in seen:
                    seen.add(title)
                    jobs.append({
                        "id":             uid,
                        "title":          title,
                        "location":       location,
                        "department":     dept,
                        "url":            href,
                        "snippet":        f"Flint Global | {dept} | {location}",
                        "published_date": datetime.now().strftime("%Y-%m-%d"),
                        "source_domain":  "flint-global.com",
                        "competitor_id":  "flint",
                    })
        browser.close()
    jobs = [j for j in jobs if j.get("title") and len(j["title"]) > 3]
    jobs = [j for j in jobs if j.get("title") and len(j["title"]) > 3]
    jobs = [j for j in jobs if j.get("title") and len(j["title"]) > 3]
    return jobs


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}


def save_state(jobs):
    with open(STATE_FILE, "w") as f:
        json.dump({j["id"]: j for j in jobs}, f, indent=2)


def job_hash(j):
    return hashlib.md5(f"{j['title']}|{j['location']}|{j['url']}".encode()).hexdigest()


def diff(old, new):
    events = []
    now = datetime.utcnow().isoformat()
    new_by_id = {j["id"]: j for j in new}
    for jid, job in new_by_id.items():
        if jid not in old:
            events.append({"change_type": "added", "detected_at": now, **job})
        elif job_hash(job) != job_hash(old[jid]):
            events.append({"change_type": "updated", "detected_at": now, **job})
    for jid, job in old.items():
        if jid not in new_by_id:
            events.append({"change_type": "removed", "detected_at": now, **job})
    return events


def send_to_lovable(payload):
    payload = [p for p in payload if p.get("title") and len(p["title"]) > 3 and p["title"] not in ("London","Brussels","Washington","New York","Singapore","Remote","Paris","Berlin","Dublin")]
    if not payload:
        print("  Nothing to push.")
        return
    if not LOVABLE_URL:
        print("  Skipping — LOVABLE_FUNCTION_URL not set.")
        return
    records = [{"title": p["title"], "url": p.get("url",""), "location": p.get("location",""), "department": p.get("department",""), "competitor_id": "flint", "source": "bamboohr"} for p in payload]
    wrapped = {"data_type": "jobs", "data": records}
    headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
    r = requests.post(LOVABLE_URL, json=wrapped, headers=headers, timeout=30)
    print(f"  {r.status_code} {r.text[:100]}")


def main():
    print(f"[{datetime.now().isoformat()}] Flint jobs monitor starting…")
    jobs = scrape_jobs()
    print(f"  Found {len(jobs)} job(s):")
    for j in jobs:
        print(f"    {j['title']} — {j['location']} — {j['url']}")
    old_state = load_state()
    if not old_state:
        print("  First run — pushing all as baseline…")
        send_to_lovable(jobs)
    else:
        changes = diff(old_state, jobs)
        if changes:
            print(f"  {len(changes)} change(s):")
            for c in changes:
                print(f"    [{c['change_type'].upper()}] {c['title']} — {c['location']}")
            send_to_lovable(changes)
        else:
            print("  No changes detected.")
    save_state(jobs)
    print("  Done.")


if __name__ == "__main__":
    main()