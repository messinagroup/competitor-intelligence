
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

print("=" * 70)
print("💼 BPI JOBS SCRAPER")
print("=" * 70)

urls = {
    'North America': 'https://bpigroup.com/careers-na/',
    'International': 'https://bpigroup.com/careers-europe/'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

all_jobs = []

for region, url in urls.items():
    print(f"\n📥 Downloading {region} careers: {url}\n")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Page downloaded for {region}!\n")
        
        # Save raw HTML for debugging
        filename = f'jobs_page_{region.lower().replace(" ", "_")}.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        
        jobs_found = []
        
        # Workable job board structure
        # Look for whr-items list containing whr-item elements
        job_items = soup.find_all('li', class_='whr-item')
        
        print(f"Found {len(job_items)} job items using Workable structure")
        
        for item in job_items:
            job = {'region': region}
            
            # Get job title from whr-title
            title_elem = item.find('h3', class_='whr-title')
            if title_elem:
                link = title_elem.find('a')
                if link:
                    job['title'] = link.get_text(strip=True)
                    job['url'] = link.get('href', '')
            
            # Get location from whr-location
            location_elem = item.find('li', class_='whr-location')
            if location_elem:
                job['location'] = location_elem.get_text(strip=True)
            
            # Get department if available (whr-dept)
            dept_elem = item.find('li', class_='whr-dept')
            if dept_elem:
                job['department'] = dept_elem.get_text(strip=True)
            
            # Get job type if available
            type_elem = item.find('li', class_='whr-type')
            if type_elem:
                job['job_type'] = type_elem.get_text(strip=True)
            
            if job.get('title'):
                jobs_found.append(job)
        
        # If no jobs found with Workable structure, try alternative methods
        if len(jobs_found) == 0:
            print("⚠️  No jobs found with Workable structure, trying alternatives...")
            
            # Try looking for any links with job-related URLs
            links = soup.find_all('a', href=lambda x: x and 'workable.com' in str(x))
            for link in links:
                text = link.get_text(strip=True)
                if text and len(text) > 5:
                    job = {
                        'title': text,
                        'region': region,
                        'url': link['href']
                    }
                    jobs_found.append(job)
        
        print(f"\n📋 {region}:")
        for i, job in enumerate(jobs_found, 1):
            print(f"   {i}. {job['title']}")
            if 'location' in job:
                print(f"      📍 {job['location']}")
            if 'department' in job:
                print(f"      🏢 {job['department']}")
        print()
        
        all_jobs.extend(jobs_found)
        
    except Exception as e:
        print(f"❌ Error scraping {region}: {e}")
        import traceback
        traceback.print_exc()

# Count by region before deduplication
total_scraped = len(all_jobs)
na_jobs = [j for j in all_jobs if j['region'] == 'North America']
intl_jobs = [j for j in all_jobs if j['region'] == 'International']

# Deduplicate by title only (same jobs appear on both pages)
seen_titles = set()
unique_jobs = []
for job in all_jobs:
    title = job.get('title')
    if title and title not in seen_titles:
        seen_titles.add(title)
        # Mark if job appears on both pages
        same_job_count = sum(1 for j in all_jobs if j.get('title') == title)
        if same_job_count > 1:
            job['appears_on'] = 'Both career pages'
        else:
            job['appears_on'] = f'{job["region"]} page only'
        unique_jobs.append(job)

all_jobs = unique_jobs

print("=" * 70)
print(f"\n✅ RESULTS:\n")

print(f"   📊 Total listings scraped: {total_scraped}")
print(f"   ✨ Unique positions: {len(all_jobs)}")
print(f"   🔄 Duplicates removed: {total_scraped - len(all_jobs)}")

# Format for monitor compatibility
output_data = {
    "company": "Bully Pulpit International",
    "competitor_id": "bpi",
    "scraped_at": datetime.utcnow().isoformat(),
    "job_count": len(all_jobs),  # Unique jobs only
    "total_scraped": total_scraped,  # Total before dedup
    "jobs": all_jobs
}

with open('bpi_jobs_final.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)

import csv
if all_jobs:
    keys = ['title', 'region', 'location', 'department', 'job_type', 'url', 'appears_on']
    with open('bpi_jobs_final.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_jobs)

print("\n💾 FILES CREATED:")
print("   • bpi_jobs_final.json")
print("   • bpi_jobs_final.csv")
print("=" * 70)

print("\n📋 COMPLETE JOB LISTINGS:\n")
for i, job in enumerate(sorted(all_jobs, key=lambda x: x['title']), 1):
    print(f"{i}. {job['title']}")
    if 'location' in job:
        print(f"   Location: {job['location']}")
    if 'department' in job:
        print(f"   Department: {job['department']}")
    if 'job_type' in job:
        print(f"   Type: {job['job_type']}")
    if 'appears_on' in job:
        print(f"   📄 {job['appears_on']}")
    if 'url' in job:
        print(f"   Apply: {job['url']}")
    print()

print("=" * 70)
print(f"✅ SUCCESS! {len(all_jobs)} unique job postings extracted")
print("=" * 70)
