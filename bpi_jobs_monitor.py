#!/usr/bin/env python3
"""
BPI Jobs Monitor
Compares current job postings to previous data and updates dashboard if changed
"""

import json
import os
import sys
from datetime import datetime
import requests

def load_previous_data(filepath='data/bpi_jobs_previous.json'):
    """Load previous scrape data"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_current_data(data, filepath='data/bpi_jobs_previous.json'):
    """Save current data for next comparison"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def compare_jobs(current, previous):
    """Compare current and previous job posting data"""
    
    if previous is None:
        return {
            'changed': True,
            'first_run': True,
            'current_count': current['job_count'],
            'previous_count': 0,
            'change': current['job_count'],
            'new_jobs': [],
            'closed_jobs': []
        }
    
    # Create sets of job titles for comparison
    current_titles = {job['title'] for job in current['jobs']}
    previous_titles = {job['title'] for job in previous['jobs']}
    
    new_jobs = current_titles - previous_titles
    closed_jobs = previous_titles - current_titles
    
    changed = (
        current['job_count'] != previous['job_count'] or
        len(new_jobs) > 0 or
        len(closed_jobs) > 0
    )
    
    return {
        'changed': changed,
        'first_run': False,
        'current_count': current['job_count'],
        'previous_count': previous['job_count'],
        'change': current['job_count'] - previous['job_count'],
        'new_jobs': list(new_jobs),
        'closed_jobs': list(closed_jobs)
    }

def send_to_lovable(data, lovable_url, api_key):
    """Send data to Lovable dashboard via edge function"""
    
    try:
        response = requests.post(
            f"{lovable_url}/functions/v1/import",
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key
            },
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error sending to Lovable: {e}")
        return False

def main():
    print("=" * 70)
    print("💼 BPI JOBS MONITOR")
    print("=" * 70)
    
    # Load current scrape data
    if not os.path.exists('bpi_jobs_final.json'):
        print("❌ Error: bpi_jobs_final.json not found")
        print("   Run bpi_jobs_scraper.py first!")
        sys.exit(1)
    
    with open('bpi_jobs_final.json', 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    
    print(f"\n✅ Loaded current data: {current_data['job_count']} job postings")
    
    # Load previous data
    previous_data = load_previous_data()
    
    if previous_data:
        print(f"✅ Loaded previous data: {previous_data['job_count']} job postings")
    else:
        print("ℹ️  No previous data found (first run)")
    
    # Compare
    comparison = compare_jobs(current_data, previous_data)
    
    print("\n" + "=" * 70)
    print("📈 COMPARISON RESULTS")
    print("=" * 70)
    
    if comparison['first_run']:
        print("\n🆕 FIRST RUN - Establishing baseline")
        print(f"   Job postings found: {comparison['current_count']}")
        should_update = True
    elif comparison['changed']:
        print("\n✅ CHANGES DETECTED!")
        print(f"   Previous count: {comparison['previous_count']}")
        print(f"   Current count:  {comparison['current_count']}")
        print(f"   Net change:     {comparison['change']:+d}")
        
        if comparison['new_jobs']:
            print(f"\n🆕 NEW JOB POSTINGS ({len(comparison['new_jobs'])}):")
            for job_title in comparison['new_jobs']:
                print(f"   + {job_title}")
        
        if comparison['closed_jobs']:
            print(f"\n🚪 CLOSED JOB POSTINGS ({len(comparison['closed_jobs'])}):")
            for job_title in comparison['closed_jobs']:
                print(f"   - {job_title}")
        
        should_update = True
    else:
        print("\nℹ️  NO CHANGES DETECTED")
        print(f"   Job postings: {comparison['current_count']}")
        should_update = False
    
    # Send to Lovable if changed
    if should_update:
        lovable_url = os.environ.get('LOVABLE_FUNCTION_URL')
        api_key = os.environ.get('LOVABLE_API_KEY')
        
        if lovable_url and api_key:
            print("\n" + "=" * 70)
            print("📤 SENDING TO LOVABLE DASHBOARD")
            print("=" * 70)
            
            # Format payload as array of jobs with metadata
            payload = []
            for job in current_data['jobs']:
                job_with_meta = {
                    **job,
                    'company': 'Bully Pulpit International',
                    'competitor_id': 'bpi',
                    'scraped_at': current_data['scraped_at'],
                    'status': 'open'
                }
                payload.append(job_with_meta)
            
            print(f"Sending {len(payload)} job postings to Lovable...")
            
            if send_to_lovable(payload, lovable_url, api_key):
                print("\n✅ Successfully updated Lovable dashboard!")
                # Save current as previous for next run
                save_current_data(current_data)
                print("✅ Saved current data for next comparison")
            else:
                print("\n❌ Failed to update dashboard")
                sys.exit(1)
        else:
            print("\n⚠️  Lovable credentials not found in environment")
            print("   Set LOVABLE_FUNCTION_URL and LOVABLE_API_KEY")
            # Still save the data even if we can't send
            save_current_data(current_data)
    else:
        print("\n" + "=" * 70)
        print("ℹ️  Dashboard not updated (no changes)")
        print("=" * 70)
    
    print("\n" + "=" * 70)
    print("✅ MONITORING COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
