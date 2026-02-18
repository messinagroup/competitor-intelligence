import requests
import json
import hashlib
import os
from datetime import datetime
from tusk_wins_scraper import scrape_wins

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://hhgtzjyjkcnwkawcgfbv.supabase.co/functions/v1/import")
API_KEY = os.environ.get("API_KEY", "bpi_test_key_12345")
STATE_FILE = "tusk_wins_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def hash_win(win):
    val = f"{win.get('title','')}{win.get('description','')}"
    return hashlib.md5(val.encode()).hexdigest()

def detect_changes(wins, prev_state):
    new_state = {hash_win(w): w for w in wins}
    added = [new_state[h] for h in set(new_state) - set(prev_state)]
    removed = [prev_state[h] for h in set(prev_state) - set(new_state)]
    return added, removed, new_state

def send_to_dashboard(wins, added, removed):
    formatted = [
        {
            "title": w.get("title"),
            "client": "Tusk Strategies",
            "industry": "Public Affairs",
            "description": w.get("description"),
            "competitor_id": "tusk"
        }
        for w in wins
    ]
    try:
        r = requests.post(SUPABASE_URL, json=formatted, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "x-api-key": API_KEY
        }, timeout=15)
        print(f"Response: {r.status_code} — {r.text[:200]}")
        return r.status_code == 200
    except Exception as e:
        print(f"Upload failed: {e}")
        return False

def main():
    print("=== Tusk Wins Monitor ===")
    wins = scrape_wins()
    if not wins:
        print("No wins found.")
        return
    prev_state = load_state()
    added, removed, new_state = detect_changes(wins, prev_state)
    if added:
        print(f"NEW ({len(added)}): {[w['title'] for w in added]}")
    if removed:
        print(f"REMOVED ({len(removed)}): {[w['title'] for w in removed]}")
    if not added and not removed:
        print("No changes detected")
    if send_to_dashboard(wins, added, removed):
        save_state(new_state)
        print("Done ✓")
    else:
        print("Upload failed")

if __name__ == "__main__":
    main()
