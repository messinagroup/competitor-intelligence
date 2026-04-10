#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
import requests

def load_previous_data(filepath='data/bpi_work_previous.json'):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_current_data(data, filepath='data/bpi_work_previous.json'):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def find_work_by_title(work_items, title):
    for work in work_items:
        if work.get('title') == title:
            return work
    return None

def compare_work(current, previous):
    if previous is None:
        return {'changed': True, 'first_run': True, 'current_count': current['work_count'],
                'previous_count': 0, 'change': current['work_count'],
                'new_work': [], 'removed_work': [], 'updated_work': []}
    current_titles = {work['title'] for work in current['work_items']}
    previous_titles = {work['title'] for work in previous['work_items']}
    new_work_titles = current_titles - previous_titles
    removed_work_titles = previous_titles - current_titles
    updated_work = []
    for title in current_titles & previous_titles:
        ci = find_work_by_title(current['work_items'], title)
        pi = find_work_by_title(previous['work_items'], title)
        if ci and pi:
            changes = []
            if ci.get('description') != pi.get('description'):
                changes.append('description')
            if set(ci.get('categories', [])) != set(pi.get('categories', [])):
                changes.append('categories')
            if ci.get('client') != pi.get('client'):
                changes.append('client')
            if changes:
                updated_work.append({'title': title, 'changes': changes, 'item': ci})
    new_work = [find_work_by_title(current['work_items'], t) for t in new_work_titles]
    removed_work = [find_work_by_title(previous['work_items'], t) for t in removed_work_titles]
    new_work = [w for w in new_work if w]
    removed_work = [w for w in removed_work if w]
    changed = (current['work_count'] != previous['work_count'] or
               len(new_work) > 0 or len(removed_work) > 0 or len(updated_work) > 0)
    return {'changed': changed, 'first_run': False,
            'current_count': current['work_count'], 'previous_count': previous['work_count'],
            'change': current['work_count'] - previous['work_count'],
            'new_work': new_work, 'removed_work': removed_work, 'updated_work': updated_work}

def send_to_lovable(data, lovable_url, api_key):
    try:
        lovable_url = lovable_url.strip()
        print(f"\n[DEBUG] Sending to: {lovable_url}")
        print(f"[DEBUG] Payload size: {len(data)} items")
        response = requests.post(
            lovable_url,
            headers={'Content-Type': 'application/json', 'x-api-key': api_key},
            json=data,
            timeout=30
        )
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text[:200]}")
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error sending to Lovable: {e}")
        return False

def main():
    print("=" * 70)
    print("BPI RECENT WORK MONITOR")
    print("=" * 70)
    if not os.path.exists('bpi_work_final.json'):
        print("❌ Error: bpi_work_final.json not found")
        sys.exit(1)
    with open('bpi_work_final.json', 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    print(f"Loaded current data: {current_data['work_count']} work items")
    previous_data = load_previous_data()
    if previous_data:
        print(f"Loaded previous data: {previous_data['work_count']} work items")
    else:
        print("No previous data found (first run)")
    comparison = compare_work(current_data, previous_data)
    if comparison['first_run']:
        print(f"FIRST RUN - Work items found: {comparison['current_count']}")
        should_update = True
    elif comparison['changed']:
        print(f"CHANGES DETECTED! {comparison['previous_count']} -> {comparison['current_count']}")
        should_update = True
    else:
        print(f"NO CHANGES - count: {comparison['current_count']}")
        should_update = False
    if should_update:
        lovable_url = os.environ.get('LOVABLE_FUNCTION_URL', '').strip()
        api_key = os.environ.get('LOVABLE_API_KEY', '')
        if lovable_url and api_key:
            payload = []
            for work in current_data['work_items']:
                client = work.get('client', '')
                if not client and ':' in work.get('title', ''):
                    client = work['title'].split(':', 1)[0].strip()
                industry = work.get('categories', [''])[0] if work.get('categories') else ''
                payload.append({
                    'title': work.get('title', ''),
                    'snippet': work.get('description', '') or work.get('subtitle', ''),
                    'source_domain': 'bpigroup.com',
                    'published_date': current_data['scraped_at'][:10],
                    'url': work.get('url', 'https://bpigroup.com/our-work/'),
                    'competitor_id': 'bpi',
                })
            print(f"Sending {len(payload)} work items...")
            if send_to_lovable(payload, lovable_url, api_key):
                print("Successfully updated dashboard!")
                save_current_data(current_data)
            else:
                print("Failed to update dashboard")
                sys.exit(1)
        else:
            print("Lovable credentials not found")
            save_current_data(current_data)
    else:
        print("Dashboard not updated (no changes)")
    print("MONITORING COMPLETE")

if __name__ == "__main__":
    main()
