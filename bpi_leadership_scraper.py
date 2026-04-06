import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

print("=" * 70)
print("🎯 BPI LEADERSHIP SCRAPER v3 - FIXED!")
print("=" * 70)

url = "https://bpigroup.com/leadership/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

print(f"\n📥 Downloading: {url}\n")

try:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    print("✅ Page downloaded!\n")
    print("=" * 70)
    print("🔍 EXTRACTING LEADERS...\n")
    
    leaders = []
    
    cards = soup.find_all('div', class_='card card-2')
    
    print(f"Found {len(cards)} leader cards\n")
    
    for card in cards:
        leader = {}
        
        img = card.find('img', alt=True)
        if img:
            leader['name'] = img['alt']
            leader['image'] = img.get('src', '')
        
        subtitle = card.find('div', class_='card-subtitle')
        if subtitle:
            leader['title'] = subtitle.get_text(strip=True)
        
        card_content = card.find('div', class_='card-content')
        if card_content:
            all_text = card_content.get_text(separator='|', strip=True)
            parts = [p.strip() for p in all_text.split('|') if p.strip()]
            
            for part in parts:
                if any(loc in part for loc in ['Washington', 'Chicago', 'New York', 'London', 'DC', 'IL', 'NY']):
                    leader['location'] = part
                    break
        
        link = card.find('a', href=True)
        if link:
            leader['profile_url'] = link['href']
        
        if leader.get('name'):
            leaders.append(leader)
            
            print(f"👤 {leader['name']}")
            if 'title' in leader:
                print(f"   Title: {leader['title']}")
            if 'location' in leader:
                print(f"   Location: {leader['location']}")
            if 'profile_url' in leader:
                print(f"   Profile: {leader['profile_url']}")
            print()
    
    print("=" * 70)
    print(f"\n✅ FOUND {len(leaders)} LEADERS!\n")
    
    # Deduplicate leaders by name
    print("🔄 Deduplicating...")
    seen = set()
    unique_leaders = []
    for leader in leaders:
        name = leader.get('name')
        if name and name not in seen:
            seen.add(name)
            unique_leaders.append(leader)
        else:
            print(f"   ⚠️  Skipping duplicate: {name}")
    
    leaders = unique_leaders
    print(f"✅ After deduplication: {len(leaders)} unique leaders\n")
    
    # Format for monitor compatibility
    output_data = {
        "company": "Bully Pulpit International",
        "company_id": "bpi",
        "scraped_at": datetime.utcnow().isoformat(),
        "headcount": len(leaders),
        "leaders": leaders
    }
    
    with open('bpi_leaders_final.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    import csv
    if leaders:
        keys = ['name', 'title', 'location', 'profile_url', 'image']
        with open('bpi_leaders_final.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(leaders)
    
    print("💾 FILES CREATED:")
    print("   • bpi_leaders_final.json")
    print("   • bpi_leaders_final.csv")
    print("=" * 70)
    
    print("\n📋 COMPLETE LIST:\n")
    for i, leader in enumerate(leaders, 1):
        print(f"{i}. {leader['name']}")
        if 'title' in leader:
            print(f"   └─ {leader['title']}")
        if 'location' in leader:
            print(f"   └─ {leader['location']}")
        print()
    
    print("=" * 70)
    print(f"✅ SUCCESS! {len(leaders)} unique leaders extracted")
    print("=" * 70)
    
    if len(leaders) < 10:
        print("\n⚠️  NOTE: Only found a few leaders. The page likely loads")
        print("   more leaders dynamically when you click 'View more'.")
        print("   This requires JavaScript/Selenium to get all leaders.")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
