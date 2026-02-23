import json
from tusk_wins_scraper import scrape_wins

wins = scrape_wins()
for i, w in enumerate(wins, 1):
    print(f"\n{'='*60}")
    print(f"#{i}")
    print(f"TITLE: {w.get('title')}")
    print(f"DESC:  {w.get('description')}")
    print(f"LINK:  {w.get('link')}")
    print(f"IMG:   {w.get('image_url')}")
