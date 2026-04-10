#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime
import requests

def load_previous_data(filepath='data/bpi_jobs_previous.json'):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_current_data(data, filepath='data/bpi_jobs_previous.json'):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def compare_jobs(current, previous):
    if previous is None:
        return {'changed': True, 'first_run': True, 'current_count': current['job_count'],
                'previous_count': 0, 'change': current['job_count'],
                'new_jobs': [], 'closed_jobs': []}
    current_titles = {job['title'] for job in current['jobs']}
    previous_titles = {job['title'] for job in previous['jobs']}
    new_jobs = current_titles - previous_titles
    closed_jobs = previous_titles - current_titles
    changed = (current['job_count'] != previous['job_count'] or
               len(new_jobs) > 0 or len(closed_jobs) > 0)
    return {'changed': changed, 'first_run': False,
            'current_count': current['job_count'], 'previous_count': previous['job_count'],
            'change': current['job_count'] - previous['job_count'],
            'new_jobs': list(new_jobs), 'closed_jobs': list(closed_jobs)}

def send_to_lovable(data, lovable_url, api_key):
    try:
        lovable_url = lovable_url.strip()
        response = requests.post(
            lovable_url,
            headers={'Content-Type': 'application/json', 'x-api-key': api_key},
            json=data,
            timeout=30
        )
        print(f"  {response.status_code} {response.text[:100]}")
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 70)
    print("BPI JOBS MONITOR")
    print("=" * 70)
    if not os.path.exists('bpi_jobs_final.json'):
        print("❌ Error: bpi_jobs_final.json not found")
        sys.exit(1)
    with open('bpi_jobs_final.json', 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    print(f"Loaded current data: {current_data['job_count']} job postings")
    previous_data = load_previous_data()
    if previous_data:
        print(f"Loaded previous data: {previous_data['job_count']} job postings")
    else:
        print("No previous data found (first run)")
    comparison = compare_jobs(current_data, previous_data)
    if comparison['first_run']:
        print(f"FIRST RUN - Job postings found: {comparison['current_count']}")
        should_update = True
    elif comparison['changed']:
        print(f"CHANGES DETECTED! {comparison['previous_count']} -> {comparison['current_count']}")
        for t in comparison['new_jobs']:
            print(f"  + {t}")
        for t in comparison['closed_jobs']:
            print(f"  - {t}")
        should_update = True
    else:
        print(f"NO CHANGES - count: {comparison['current_count']}")
        should_update = False
    if should_update:
        lovable_url = os.environ.get('LOVABLE_FUNCTION_URL', '').strip()
        api_key = os.environ.get('LOVABLE_API_KEY', '')
        if lovable_url and api_key:
            payload = [{
                'title': job.get('title', ''),
                'snippet': job.get('department', '') or job.get('location', ''),
                'source_domain': 'bpigroup.com',
                'published_date': current_data['scraped_at'][:10],
                'url': job.get('url', 'https://bpigroup.com/careers/'),
                'competitor_id': 'bpi',
            } for job in current_data['jobs']]
            print(f"Sending {len(payload)} job postings...")
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
