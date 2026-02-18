import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

WINS_URL = "https://tuskstrategies.com/wins/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def scrape_wins():
    print(f"Fetching {WINS_URL}")
    resp = requests.get(WINS_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.find_all("article")
    if not cards:
        print("No articles found. Raw sample:")
        print(soup.get_text(separator="\n", strip=True)[:3000])
        return []
    wins = []
    for card in cards:
        win = {}
        for tag in ["h2","h3","h4","h5"]:
            el = card.select_one(tag)
            if el and el.get_text(strip=True):
                win["title"] = el.get_text(strip=True)
                break
        if not win.get("title"):
            continue
        p = card.select_one("p")
        win["description"] = p.get_text(strip=True) if p else None
        a = card.select_one("a[href]")
        win["link"] = a["href"] if a else None
        win["scraped_at"] = datetime.utcnow().isoformat()
        wins.append(win)
    print(f"Extracted {len(wins)} wins")
    return wins

if __name__ == "__main__":
    wins = scrape_wins()
    for i,w in enumerate(wins,1):
        print(f"{i}. {w.get('title','')[:60]}")
