#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime
import requests

def load_previous_data(filepath='data/bpi_previous.json'):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_current_data(data, filepath='data/bpi_previous.json'):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def compare_leadership(current, previous):
    if previous is None:
        return {'changed': True, 'first_run': True, 'current_count': current['headcount'], 'previous_count': 0, 'change': current['headcount'], 'new_leaders': [], 'departed_leaders': []}
    current_names = {l['name'] for l in current['leaders']}
    previous_names = {l['name'] for l in previous['leaders']}
    new_leaders = current_names - previous_names
    departed_leaders = previous_names - current_names
    changed = (current['headcount'] != previous['headcount'] or len(new_leaders) > 0 or len(departed_leaders) > 0)
    return {'changed': changed, 'first_run': False, 'current_count': current['headcount'], 'previous_count': previous['headcount'], 'change': current['headcount'] - previous['headcount'], 'new_leaders': list(new_leaders), 'departed_leaders': list(departed_leaders)}

def send_to_lovable(items, scraped_at, lovable_url, api_key, batch_size=25):
    total_sent = 0
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  Sending batch {batch_num} ({len(batch)} leaders)...")
        payload = {"competitor_id": "bpi", "data_type": "leadership", "scraped_date": scraped_at, "items": batch}
        try:
            resp = requests.post(f"{lovable_url}/functions/v1/import", headers={"Content-Type": "application/json", "x-api-key": api_key}, json=payload, timeout=60)
            resp.raise_for_status()
            total_sent += len(batch)
            print(f"  Batch {batch_num} sent: {resp.text}")
        except Exception as e:
            print(f"  Batch {batch_num} failed: {e}")
        time.sleep(1)
    return total_sent

def main():
    print("=" * 70)
    print("BPI LEADERSHIP MONITOR")
    print("=" * 70)
    if not os.path.exists('bpi_leaders_final.json'):
        print("Error: bpi_leaders_final.json not found")
        sys.exit(1)
    with open('bpi_leaders_final.json', 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    print(f"Loaded current data: {current_data['headcount']} leaders")
    previous_data = load_previous_data()
    if previous_data:
        print(f"Loaded previous data: {previous_data['headcount']} leaders")
    else:
        print("No previous data found (first run)")
    comparison = compare_leadership(current_data, previous_data)
    if comparison['first_run']:
        print(f"FIRST RUN - Leaders found: {comparison['current_count']}")
        should_update = True
    elif comparison['changed']:
        print(f"CHANGES DETECTED! {comparison['previous_count']} -> {comparison['current_count']} ({comparison['change']:+d})")
        for name in comparison['new_leaders']:
            print(f"  + {name}")
        for name in comparison['departed_leaders']:
            print(f"  - {name}")
        should_update = True
    else:
        print(f"NO CHANGES - count: {comparison['current_count']}")
        should_update = False
    if should_update:
        lovable_url = os.environ.get('LOVABLE_FUNCTION_URL')
        api_key = os.environ.get('LOVABLE_API_KEY')
        if lovable_url and api_key:
            items = [{"name": l.get('name',''), "title": l.get('title',''), "region": l.get('region','Unknown'), "scraped_at": current_data['scraped_at']} for l in current_data['leaders']]
            print(f"Sending {len(items)} leaders in batches of 25...")
            total = send_to_lovable(items, current_data['scraped_at'], lovable_url, api_key)
            if total > 0:
                print(f"Successfully sent {total} leaders!")
                save_current_data(current_data)
            else:
                print("Failed to send any batches")
                sys.exit(1)
        else:
            print("Lovable credentials not found")
            save_current_data(current_data)
    else:
        print("Dashboard not updated (no changes)")
    print("MONITORING COMPLETE")

if __name__ == "__main__":
    main()
