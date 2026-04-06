
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

print("=" * 70)
print("🌍 BPI LOCATIONS SCRAPER")
print("=" * 70)

url = "https://bpigroup.com/where-we-are/"

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
    print("🔍 EXTRACTING LOCATIONS...\n")
    
    # Save raw HTML for debugging
    with open('locations_page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    
    locations = []
    
    # Known cities from BPI's offices
    cities = {
        'Chicago': {'region': 'North America', 'type': 'BPI Office'},
        'Los Angeles': {'region': 'North America', 'type': 'BPI Office'},
        'New York City': {'region': 'North America', 'type': 'BPI Office'},
        'San Francisco': {'region': 'North America', 'type': 'BPI Office'},
        'Washington': {'region': 'North America', 'type': 'BPI Office'},
        'Brussels': {'region': 'Europe', 'type': 'BPI Office'},
        'Berlin': {'region': 'Europe', 'type': 'BPI Office'},
        'Oslo': {'region': 'Europe', 'type': 'BPI Office'},
        'Zurich': {'region': 'Europe', 'type': 'BPI Office'},
        'Switzerland': {'region': 'Europe', 'type': 'BPI Office'},
        'London': {'region': 'Europe', 'type': 'BPI Office'},
        'Berkhamsted': {'region': 'Europe', 'type': 'BPI Office'},
        'Melbourne': {'region': 'Asia Pacific', 'type': 'Partner Office'},
        'Sydney': {'region': 'Asia Pacific', 'type': 'Partner Office'},
        'Canberra': {'region': 'Asia Pacific', 'type': 'Partner Office'},
        'Perth': {'region': 'Asia Pacific', 'type': 'Partner Office'}
    }
    
    # Get all text content and split into lines
    all_text = soup.get_text(separator='\n')
    lines = [line.strip() for line in all_text.split('\n') if line.strip()]
    
    # Process line by line looking for cities followed by addresses
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line is a city name
        city_found = None
        for city_name in cities.keys():
            if city_name.lower() in line.lower() and len(line) < 50:
                # Make sure it's not a section header
                if line.lower() not in ['north america', 'europe', 'asia pacific', 'our international presence']:
                    city_found = city_name
                    break
        
        if city_found:
            location = {
                'city': city_found,
                'region': cities[city_found]['region'],
                'office_type': cities[city_found]['type']
            }
            
            # Look ahead for address (next 1-3 lines)
            address_parts = []
            for j in range(i+1, min(i+4, len(lines))):
                next_line = lines[j]
                
                # Stop if we hit another city or section
                if any(city.lower() in next_line.lower() for city in cities.keys()):
                    break
                
                # Check if this looks like an address (has numbers, state codes, or postal codes)
                if (any(char.isdigit() for char in next_line) or 
                    re.search(r'\b[A-Z]{2}\b|\d{5}|\b[A-Z]\d[A-Z]', next_line)):
                    address_parts.append(next_line)
            
            if address_parts:
                location['address'] = ', '.join(address_parts)
            
            # Check if it's a partner office (look for "Alliance Partner" nearby)
            for j in range(max(0, i-2), min(i+3, len(lines))):
                if 'alliance partner' in lines[j].lower() or 'mandala partners' in lines[j].lower():
                    location['partner_name'] = 'Mandala Partners'
                    break
            
            locations.append(location)
            
            print(f"📍 {location['city']}")
            print(f"   Region: {location['region']}")
            print(f"   Type: {location['office_type']}")
            if 'address' in location:
                print(f"   Address: {location['address']}")
            if 'partner_name' in location:
                print(f"   Partner: {location['partner_name']}")
            print()
        
        i += 1
    
    # Deduplicate by city
    seen_cities = set()
    unique_locations = []
    for loc in locations:
        city = loc.get('city')
        if city and city not in seen_cities:
            seen_cities.add(city)
            unique_locations.append(loc)
    
    locations = unique_locations
    
    print("=" * 70)
    print(f"\n✅ FOUND {len(locations)} LOCATIONS!\n")
    
    # Count by type
    bpi_offices = [loc for loc in locations if loc['office_type'] == 'BPI Office']
    partner_offices = [loc for loc in locations if loc['office_type'] == 'Partner Office']
    
    print(f"   🏢 BPI Offices: {len(bpi_offices)}")
    print(f"   🤝 Partner Offices: {len(partner_offices)}")
    
    # Format for monitor compatibility
    output_data = {
        "company": "Bully Pulpit International",
        "competitor_id": "bpi",
        "scraped_at": datetime.utcnow().isoformat(),
        "location_count": len(locations),
        "bpi_office_count": len(bpi_offices),
        "partner_office_count": len(partner_offices),
        "locations": locations
    }
    
    with open('bpi_locations_final.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    import csv
    if locations:
        keys = ['city', 'region', 'office_type', 'address', 'partner_name']
        with open('bpi_locations_final.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(locations)
    
    print("\n💾 FILES CREATED:")
    print("   • bpi_locations_final.json")
    print("   • bpi_locations_final.csv")
    print("   • locations_page.html (debug)")
    print("=" * 70)
    
    print("\n📋 SUMMARY:")
    print(f"   Total Locations: {len(locations)}")
    
    print("\n   By Region:")
    regions = {}
    for loc in locations:
        region = loc['region']
        regions[region] = regions.get(region, 0) + 1
    for region, count in sorted(regions.items()):
        print(f"   • {region}: {count} offices")
    
    print("\n   Cities:")
    for loc in sorted(locations, key=lambda x: x['region']):
        print(f"   • {loc['city']} ({loc['office_type']})")
    
    print("\n" + "=" * 70)
    print(f"✅ SUCCESS! {len(locations)} locations extracted")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
