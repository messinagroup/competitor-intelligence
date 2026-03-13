#!/usr/bin/env python3
"""
BPI Google Alerts Monitor
Tracks Google Alerts for "Bully Pulpit International" and sends to dashboard
"""

import json
import os
import sys
from datetime import datetime
import requests

def load_previous_data(filepath='data/bpi_alerts_previous.json'):
    """Load previous alert data"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_current_data(data, filepath='data/bpi_alerts_previous.json'):
    """Save current data for next comparison"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def find_alert_by_url(alerts, url):
    """Find an alert by URL"""
    for alert in alerts:
        if alert.get('url') == url:
            return alert
    return None

def compare_alerts(current, previous):
    """Compare current and previous alerts"""
    
    if previous is None:
        return {
            'changed': True,
            'first_run': True,
            'current_count': current['alert_count'],
            'previous_count': 0,
            'change': current['alert_count'],
            'new_alerts': [],
            'removed_alerts': []
        }
    
    # Create sets of alert URLs (more reliable than titles)
    current_urls = {alert['url'] for alert in current['alerts'] if alert.get('url')}
    previous_urls = {alert['url'] for alert in previous['alerts'] if alert.get('url')}
    
    new_alert_urls = current_urls - previous_urls
    removed_alert_urls = previous_urls - current_urls
    
    # Get full items
    new_alerts = []
    for url in new_alert_urls:
        item = find_alert_by_url(current['alerts'], url)
        if item:
            new_alerts.append(item)
    
    removed_alerts = []
    for url in removed_alert_urls:
        item = find_alert_by_url(previous['alerts'], url)
        if item:
            removed_alerts.append(item)
    
    changed = (
        current['alert_count'] != previous['alert_count'] or
        len(new_alerts) > 0 or
        len(removed_alerts) > 0
    )
    
    return {
        'changed': changed,
        'first_run': False,
        'current_count': current['alert_count'],
        'previous_count': previous['alert_count'],
        'change': current['alert_count'] - previous['alert_count'],
        'new_alerts': new_alerts,
        'removed_alerts': removed_alerts
    }

def send_to_lovable(data, lovable_url, api_key):
    """Send data to Lovable dashboard via edge function"""
    
    try:
        import_url = f"{lovable_url}/functions/v1/import"
        
        print(f"\n[DEBUG] Sending to: {import_url}")
        print(f"[DEBUG] Payload size: {len(data)} items")
        if data:
            print(f"[DEBUG] First item sample: {json.dumps(data[0], indent=2)[:300]}...")
        
        response = requests.post(
            import_url,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key
            },
            json=data,
            timeout=30
        )
        
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text[:500]}")
        
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error sending to Lovable: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 70)
    print("🔔 BPI GOOGLE ALERTS MONITOR")
    print("=" * 70)
    
    # Load current alert data
    if not os.path.exists('bpi_alerts_final.json'):
        print("❌ Error: bpi_alerts_final.json not found")
        print("   Run bpi_alerts_scrapper.py first!")
        sys.exit(1)
    
    with open('bpi_alerts_final.json', 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    
    print(f"\n✅ Loaded current data: {current_data['alert_count']} alerts")
    
    # Load previous data
    previous_data = load_previous_data()
    
    if previous_data:
        print(f"✅ Loaded previous data: {previous_data['alert_count']} alerts")
    else:
        print("ℹ️  No previous data found (first run)")
    
    # Compare
    comparison = compare_alerts(current_data, previous_data)
    
    print("\n" + "=" * 70)
    print("📈 COMPARISON RESULTS")
    print("=" * 70)
    
    if comparison['first_run']:
        print("\n🆕 FIRST RUN - Establishing baseline")
        print(f"   Alerts found: {comparison['current_count']}")
        
        # Show sample
        print("\n📊 Sample alerts:")
        for alert in current_data['alerts'][:3]:
            print(f"   • {alert['title']}")
            if alert.get('published_date'):
                print(f"     📅 {alert['published_date']}")
            if alert.get('source_domain'):
                print(f"     🌐 {alert['source_domain']}")
        
        if current_data['alert_count'] > 3:
            print(f"   ... and {current_data['alert_count'] - 3} more")
        
        should_update = True
        
    elif comparison['changed']:
        print("\n✅ CHANGES DETECTED!")
        print(f"   Previous count: {comparison['previous_count']}")
        print(f"   Current count:  {comparison['current_count']}")
        print(f"   Net change:     {comparison['change']:+d}")
        
        if comparison['new_alerts']:
            print(f"\n🔔 NEW ALERTS ({len(comparison['new_alerts'])}):")
            for alert in comparison['new_alerts']:
                print(f"   + {alert['title']}")
                if alert.get('published_date'):
                    print(f"     📅 {alert['published_date']}")
                if alert.get('source_domain'):
                    print(f"     🌐 {alert['source_domain']}")
                if alert.get('snippet'):
                    print(f"     {alert['snippet'][:100]}...")
                print()
        
        if comparison['removed_alerts']:
            print(f"\n🗑️  ALERTS REMOVED ({len(comparison['removed_alerts'])}):")
            for alert in comparison['removed_alerts']:
                print(f"   - {alert['title']}")
                print()
        
        should_update = True
        
    else:
        print("\nℹ️  NO CHANGES DETECTED")
        print(f"   Alerts: {comparison['current_count']}")
        should_update = False
    
    # Send to Lovable if changed
    if should_update:
        lovable_url = os.environ.get('LOVABLE_FUNCTION_URL')
        api_key = os.environ.get('LOVABLE_API_KEY')
        
        if lovable_url and api_key:
            print("\n" + "=" * 70)
            print("📤 SENDING TO LOVABLE DASHBOARD")
            print("=" * 70)
            
            # Format payload for Lovable import
            payload = []
            for alert in current_data['alerts']:
                alert_with_meta = {
                    'title': alert.get('title', ''),
                    'published_date': alert.get('published_date', ''),
                    'source_domain': alert.get('source_domain', ''),
                    'snippet': alert.get('snippet', ''),
                    'url': alert.get('url', ''),
                    'search_term': alert.get('search_term', ''),
                    'alert_type': alert.get('alert_type', ''),
                    'company': 'Bully Pulpit International',
                    'competitor_id': 'bpi',
                    'scraped_date': current_data['scraped_at'],
                    'is_new': alert['url'] in [a['url'] for a in comparison.get('new_alerts', [])]
                }
                payload.append(alert_with_meta)
            
            print(f"Sending {len(payload)} alerts to Lovable...")
            if comparison.get('new_alerts'):
                print(f"  → Including {len(comparison['new_alerts'])} new alerts")
            
            if not payload:
                print("\n⚠️  No alerts to send — skipping dashboard update")
                save_current_data(current_data)
            elif send_to_lovable(payload, lovable_url, api_key):
                print("\n✅ Successfully updated Lovable dashboard!")
                save_current_data(current_data)
                print("✅ Saved current data for next comparison")
            else:
                print("\n❌ Failed to update dashboard")
                sys.exit(1)
        else:
            print("\n⚠️  Lovable credentials not found in environment")
            print("   Set LOVABLE_FUNCTION_URL and LOVABLE_API_KEY")
            save_current_data(current_data)
            print("✅ Saved current data for next comparison")
    else:
        print("\n" + "=" * 70)
        print("ℹ️  Dashboard not updated (no changes)")
        print("=" * 70)
    
    print("\n" + "=" * 70)
    print("✅ MONITORING COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()