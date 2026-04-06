#!/usr/bin/env python3
"""
BPI Recent Work Monitor (Enhanced)
Tracks new case studies and projects added to the Recent Work page
Now with rich data comparison (descriptions, categories, etc.)
"""

import json
import os
import sys
from datetime import datetime
import requests

def load_previous_data(filepath='data/bpi_work_previous.json'):
    """Load previous scrape data"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_current_data(data, filepath='data/bpi_work_previous.json'):
    """Save current data for next comparison"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def find_work_by_title(work_items, title):
    """Find a work item by title"""
    for work in work_items:
        if work.get('title') == title:
            return work
    return None

def compare_work(current, previous):
    """Compare current and previous work items with detailed change detection"""
    
    if previous is None:
        return {
            'changed': True,
            'first_run': True,
            'current_count': current['work_count'],
            'previous_count': 0,
            'change': current['work_count'],
            'new_work': [],
            'removed_work': [],
            'updated_work': []
        }
    
    # Create sets of work titles
    current_titles = {work['title'] for work in current['work_items']}
    previous_titles = {work['title'] for work in previous['work_items']}
    
    new_work_titles = current_titles - previous_titles
    removed_work_titles = previous_titles - current_titles
    
    # Check for updates to existing work (same title, different content)
    updated_work = []
    common_titles = current_titles & previous_titles
    
    for title in common_titles:
        current_item = find_work_by_title(current['work_items'], title)
        previous_item = find_work_by_title(previous['work_items'], title)
        
        if current_item and previous_item:
            changes = []
            
            # Check for description changes
            if current_item.get('description') != previous_item.get('description'):
                changes.append('description')
            
            # Check for category changes
            curr_cats = set(current_item.get('categories', []))
            prev_cats = set(previous_item.get('categories', []))
            if curr_cats != prev_cats:
                changes.append('categories')
            
            # Check for client changes (unlikely but possible)
            if current_item.get('client') != previous_item.get('client'):
                changes.append('client')
            
            if changes:
                updated_work.append({
                    'title': title,
                    'changes': changes,
                    'item': current_item
                })
    
    # Get full work items for new/removed work
    new_work = []
    for title in new_work_titles:
        item = find_work_by_title(current['work_items'], title)
        if item:
            new_work.append(item)
    
    removed_work = []
    for title in removed_work_titles:
        item = find_work_by_title(previous['work_items'], title)
        if item:
            removed_work.append(item)
    
    changed = (
        current['work_count'] != previous['work_count'] or
        len(new_work) > 0 or
        len(removed_work) > 0 or
        len(updated_work) > 0
    )
    
    return {
        'changed': changed,
        'first_run': False,
        'current_count': current['work_count'],
        'previous_count': previous['work_count'],
        'change': current['work_count'] - previous['work_count'],
        'new_work': new_work,
        'removed_work': removed_work,
        'updated_work': updated_work
    }

def send_to_lovable(data, lovable_url, api_key):
    """Send data to Lovable dashboard via edge function"""
    
    try:
        # Construct full URL
        import_url = f"{lovable_url}/functions/v1/import"
        
        print(f"\n[DEBUG] Sending to: {import_url}")
        print(f"[DEBUG] Payload size: {len(data)} items")
        print(f"[DEBUG] First item sample: {json.dumps(data[0] if data else {}, indent=2)[:300]}...")
        
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
    print("💼 BPI RECENT WORK MONITOR (Enhanced)")
    print("=" * 70)
    
    # Load current scrape data
    if not os.path.exists('bpi_work_final.json'):
        print("❌ Error: bpi_work_final.json not found")
        print("   Run bpi_recentwork_scrapper.py first!")
        sys.exit(1)
    
    with open('bpi_work_final.json', 'r', encoding='utf-8') as f:
        current_data = json.load(f)
    
    print(f"\n✅ Loaded current data: {current_data['work_count']} work items")
    
    # Load previous data
    previous_data = load_previous_data()
    
    if previous_data:
        print(f"✅ Loaded previous data: {previous_data['work_count']} work items")
    else:
        print("ℹ️  No previous data found (first run)")
    
    # Compare
    comparison = compare_work(current_data, previous_data)
    
    print("\n" + "=" * 70)
    print("📈 COMPARISON RESULTS")
    print("=" * 70)
    
    if comparison['first_run']:
        print("\n🆕 FIRST RUN - Establishing baseline")
        print(f"   Work items found: {comparison['current_count']}")
        
        # Show sample of work items
        print("\n📊 Sample work items:")
        for work in current_data['work_items'][:5]:
            print(f"   • {work['title']}")
            if work.get('client'):
                print(f"     Client: {work['client']}")
            if work.get('categories'):
                print(f"     Categories: {', '.join(work['categories'])}")
        
        if current_data['work_count'] > 5:
            print(f"   ... and {current_data['work_count'] - 5} more")
        
        should_update = True
        
    elif comparison['changed']:
        print("\n✅ CHANGES DETECTED!")
        print(f"   Previous count: {comparison['previous_count']}")
        print(f"   Current count:  {comparison['current_count']}")
        print(f"   Net change:     {comparison['change']:+d}")
        
        if comparison['new_work']:
            print(f"\n🎨 NEW WORK ADDED ({len(comparison['new_work'])}):")
            for work in comparison['new_work']:
                print(f"   + {work['title']}")
                if work.get('client'):
                    print(f"     Client: {work['client']}")
                if work.get('categories'):
                    print(f"     Categories: {', '.join(work['categories'])}")
                if work.get('description'):
                    preview = work['description'][:100] + '...' if len(work['description']) > 100 else work['description']
                    print(f"     {preview}")
                print()
        
        if comparison['removed_work']:
            print(f"🗑️  WORK REMOVED ({len(comparison['removed_work'])}):")
            for work in comparison['removed_work']:
                print(f"   - {work['title']}")
                if work.get('client'):
                    print(f"     Client: {work['client']}")
                print()
        
        if comparison['updated_work']:
            print(f"✏️  WORK UPDATED ({len(comparison['updated_work'])}):")
            for update in comparison['updated_work']:
                print(f"   ~ {update['title']}")
                print(f"     Changed: {', '.join(update['changes'])}")
                print()
        
        should_update = True
        
    else:
        print("\nℹ️  NO CHANGES DETECTED")
        print(f"   Work items: {comparison['current_count']}")
        should_update = False
    
    # Send to Lovable if changed
    if should_update:
        lovable_url = os.environ.get('LOVABLE_FUNCTION_URL')
        api_key = os.environ.get('LOVABLE_API_KEY')
        
        if lovable_url and api_key:
            print("\n" + "=" * 70)
            print("📤 SENDING TO LOVABLE DASHBOARD")
            print("=" * 70)
            
            # Format payload for Lovable client_work import
            payload = []
            for work in current_data['work_items']:
                # Ensure client field exists and is not empty
                client = work.get('client', '')
                if not client and work.get('title'):
                    # Fallback: extract client from title (before colon)
                    if ':' in work['title']:
                        client = work['title'].split(':', 1)[0].strip()
                
                # Use first category as industry if available
                industry = ''
                if work.get('categories') and len(work['categories']) > 0:
                    industry = work['categories'][0]
                
                work_with_meta = {
                    'title': work.get('title', ''),
                    'client': client,
                    'industry': industry,
                    'description': work.get('description', ''),
                    'url': work.get('url', ''),
                    'categories': work.get('categories', []),
                    'subtitle': work.get('subtitle', ''),
                    'has_image': work.get('has_image', False),
                    'image_url': work.get('image_url', ''),
                    'company': 'Bully Pulpit International',
                    'competitor_id': 'bpi',
                    'scraped_date': current_data['scraped_at'],  # Changed from scraped_at to scraped_date
                    'is_new': work['title'] in [w['title'] for w in comparison.get('new_work', [])],
                    'is_updated': work['title'] in [u['title'] for u in comparison.get('updated_work', [])]
                }
                payload.append(work_with_meta)
            
            print(f"Sending {len(payload)} work items to Lovable...")
            if comparison.get('new_work'):
                print(f"  → Including {len(comparison['new_work'])} new items")
            if comparison.get('updated_work'):
                print(f"  → Including {len(comparison['updated_work'])} updated items")
            
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
