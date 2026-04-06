
#!/usr/bin/env python3
"""
BPI Locations Monitor
Compares current locations to previous data and updates dashboard if changed
"""

import json
import os
import sys
from datetime import datetime
import requests

def load_previous_data(filepath='data/bpi_locations_previous.json'):
    """Load previous scrape data"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_current_data(data, filepath='data/bpi_locations_previous.json'):
    """Save current data for next comparison"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def compare_locations(current, previous):
    """Compare current and previous location data"""
    
    if previous is None:
        return {
            'changed': True,
            'first_run': True,
            'current_count': current['location_count'],
            'previous_count': 0,
            'change': current['location_count'],
            'new_locations': [],
            'closed_locations': []
        }
    
    current_cities = {loc['city'] for loc in current['locations']}
    previous_cities = {loc['city'] for loc in previous['locations']}
    
    new_locations = current_cities - previous_cities
    closed_locations = previous_cities - current_cities
    
    changed = (
        current['location_count'] != previous['location_count'] or
        len(new_locations) > 0 or
        len(closed_locations) > 0
    )
    
    return {
        'changed': changed,
        'first_run': False,
        'current_count': current['location_count'],
        'previous_count': previous['location_count'],
        'change': current['location_count'] - previous['location_count'],
        'new_locations': list(new_locations),
        'closed_locations': list(closed_locations)
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
    print("📍 BPI LOCATIONS MONITOR")
    print("=" * 70)
    
    # Load current scrape data
    if not os.path.exists('bpi_locations_final.json'):
        print("❌ Error: bpi_locations_final.json not found")
        print("   Run bpi_locations_scraper.py first!")
        sys.exit(1)
    
    with open('bpi_locations_final.json', 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    
    print(f"\n✅ Loaded current data: {current_data['location_count']} locations")
    
    # Load previous data
    previous_data = load_previous_data()
    
    if previous_data:
        print(f"✅ Loaded previous data: {previous_data['location_count']} locations")
    else:
        print("ℹ️  No previous data found (first run)")
    
    # Compare
    comparison = compare_locations(current_data, previous_data)
    
    print("\n" + "=" * 70)
    print("📈 COMPARISON RESULTS")
    print("=" * 70)
    
    if comparison['first_run']:
        print("\n🆕 FIRST RUN - Establishing baseline")
        print(f"   Locations found: {comparison['current_count']}")
        should_update = True
    elif comparison['changed']:
        print("\n✅ CHANGES DETECTED!")
        print(f"   Previous count: {comparison['previous_count']}")
        print(f"   Current count:  {comparison['current_count']}")
        print(f"   Net change:     {comparison['change']:+d}")
        
        if comparison['new_locations']:
            print(f"\n🏢 NEW OFFICES ({len(comparison['new_locations'])}):")
            for city in comparison['new_locations']:
                print(f"   + {city}")
        
        if comparison['closed_locations']:
            print(f"\n🚪 CLOSED OFFICES ({len(comparison['closed_locations'])}):")
            for city in comparison['closed_locations']:
                print(f"   - {city}")
        
        should_update = True
    else:
        print("\nℹ️  NO CHANGES DETECTED")
        print(f"   Location count: {comparison['current_count']}")
        should_update = False
    
    # Send to Lovable if changed
    if should_update:
        lovable_url = os.environ.get('LOVABLE_FUNCTION_URL')
        api_key = os.environ.get('LOVABLE_API_KEY')
        
        if lovable_url and api_key:
            print("\n" + "=" * 70)
            print("📤 SENDING TO LOVABLE DASHBOARD")
            print("=" * 70)
            
            # Format payload as array of locations with metadata
            payload = []
            for location in current_data['locations']:
                location_with_meta = {
                    **location,
                    'company': 'Bully Pulpit International',
                    'competitor_id': 'bpi',
                    'scraped_at': current_data['scraped_at']
                }
                payload.append(location_with_meta)
            
            print(f"Sending {len(payload)} locations to Lovable...")
