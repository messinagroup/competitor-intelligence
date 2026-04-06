
import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

print("=" * 70)
print("💼 BPI DEEP WORK SCRAPER (Enhanced)")
print("=" * 70)

# Configuration
BASE_URL = "https://bpigroup.com"
WORK_PAGE_URL = f"{BASE_URL}/recent-work/"
DELAY_BETWEEN_REQUESTS = 1.5  # Be respectful to the server

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

def fetch_page(url):
    """Fetch a page with error handling"""
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"   ❌ Error fetching {url}: {e}")
        return None

def extract_case_study_urls(soup):
    """Extract all case study URLs from the main work page"""
    urls = []
    
    # Look for links to case studies
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link['href']
        
        # Filter for case study URLs
        if '/case-study/' in href:
            full_url = urljoin(BASE_URL, href)
            if full_url not in urls:
                urls.append(full_url)
    
    return urls

def parse_title(title_text):
    """Parse 'Client: Description' format into separate fields"""
    if ':' in title_text:
        parts = title_text.split(':', 1)
        return {
            'client': parts[0].strip(),
            'subtitle': parts[1].strip()
        }
    return {
        'client': '',
        'subtitle': title_text.strip()
    }

def scrape_case_study_detail(url):
    """Deep scrape an individual case study page"""
    print(f"   📄 Scraping: {url}")
    
    soup = fetch_page(url)
    if not soup:
        return None
    
    work = {'url': url}
    
    # Extract title
    title_elem = soup.find(['h1', 'h2'], class_=lambda x: x and any(
        term in str(x).lower() for term in ['title', 'heading', 'hero']
    ))
    
    if not title_elem:
        # Fallback: just find the first h1
        title_elem = soup.find('h1')
    
    if title_elem:
        title_text = title_elem.get_text(strip=True)
        work['title'] = title_text
        
        # Parse client and subtitle from title
        parsed = parse_title(title_text)
        work['client'] = parsed['client']
        work['subtitle'] = parsed['subtitle']
    
    # Extract main description/summary
    # Look for the main content area
    description = None
    
    # Try multiple strategies for finding description
    desc_selectors = [
        ('div', {'class': lambda x: x and 'description' in str(x).lower()}),
        ('div', {'class': lambda x: x and 'summary' in str(x).lower()}),
        ('div', {'class': lambda x: x and 'intro' in str(x).lower()}),
        ('div', {'class': lambda x: x and 'content' in str(x).lower()}),
        ('p', {'class': lambda x: x and 'lead' in str(x).lower()}),
        ('p', {'class': lambda x: x and 'intro' in str(x).lower()}),
    ]
    
    for tag, attrs in desc_selectors:
        elem = soup.find(tag, attrs)
        if elem:
            description = elem.get_text(strip=True)
            if len(description) > 50:
                break
    
    # Fallback: get the first substantial paragraph (skip cookie notices)
    if not description or len(description) < 50:
        paragraphs = soup.find_all('p')
        skip_terms = ['cookie', 'consent', 'privacy policy', 'terms of service', 'gdpr']
        for p in paragraphs:
            text = p.get_text(strip=True)
            # Skip cookie notices and other boilerplate
            if len(text) > 50 and not text.startswith('©'):
                if not any(term in text.lower() for term in skip_terms):
                    description = text
                    break
    
    if description:
        # Limit description length
        work['description'] = description[:500] + '...' if len(description) > 500 else description
    
    # Extract categories/tags
    tags = []
    tag_elements = soup.find_all(['span', 'a', 'div'], class_=lambda x: x and any(
        term in str(x).lower() for term in ['tag', 'category', 'topic']
    ))
    
    for tag_elem in tag_elements:
        tag_text = tag_elem.get_text(strip=True)
        if tag_text and len(tag_text) < 50 and tag_text not in tags:
            tags.append(tag_text)
    
    if tags:
        work['categories'] = tags[:5]  # Limit to 5 tags
    
    # Extract images
    img = soup.find('img', src=True)
    if img:
        img_src = img.get('src', '')
        if img_src:
            work['has_image'] = True
            work['image_url'] = urljoin(BASE_URL, img_src)
    
    # Extract any challenge/solution/results sections
    sections = {}
    section_keywords = ['challenge', 'solution', 'approach', 'result', 'impact', 'outcome']
    
    for keyword in section_keywords:
        section_elem = soup.find(['div', 'section'], class_=lambda x: x and keyword in str(x).lower())
        if not section_elem:
            # Try finding by heading
            heading = soup.find(['h2', 'h3', 'h4'], string=lambda x: x and keyword in str(x).lower())
            if heading:
                # Get the next sibling content
                next_elem = heading.find_next(['p', 'div'])
                if next_elem:
                    section_text = next_elem.get_text(strip=True)
                    if len(section_text) > 30:
                        sections[keyword] = section_text[:300]
    
    if sections:
        work['sections'] = sections
    
    # Add metadata
    work['scraped_at'] = datetime.now(timezone.utc).isoformat()
    
    return work

def main():
    # Step 1: Get all case study URLs from main page
    print(f"\n📥 Fetching main work page: {WORK_PAGE_URL}\n")
    
    soup = fetch_page(WORK_PAGE_URL)
    if not soup:
        print("❌ Failed to fetch main page")
        return
    
    # Save main page HTML for debugging
    with open('work_page.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    
    case_study_urls = extract_case_study_urls(soup)
    
    print(f"✅ Found {len(case_study_urls)} case study URLs\n")
    print("=" * 70)
    print("🔍 DEEP SCRAPING EACH CASE STUDY...")
    print("=" * 70)
    
    # Step 2: Deep scrape each case study
    work_items = []
    
    for i, url in enumerate(case_study_urls, 1):
        print(f"\n[{i}/{len(case_study_urls)}]")
        
        work = scrape_case_study_detail(url)
        if work and work.get('title'):
            work_items.append(work)
            print(f"   ✅ {work['title']}")
        else:
            print(f"   ⚠️  Could not extract details")
        
        # Be respectful - don't hammer the server
        if i < len(case_study_urls):
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    print("\n" + "=" * 70)
    print(f"✅ SUCCESSFULLY SCRAPED {len(work_items)} CASE STUDIES")
    print("=" * 70)
    
    # Display summary
    print("\n📊 SUMMARY:\n")
    for i, work in enumerate(work_items, 1):
        print(f"{i}. {work.get('title', 'No title')}")
        if work.get('client'):
            print(f"   Client: {work['client']}")
        if work.get('categories'):
            print(f"   Categories: {', '.join(work['categories'])}")
        if work.get('description'):
            preview = work['description'][:100] + '...' if len(work['description']) > 100 else work['description']
            print(f"   {preview}")
        print()
    
    # Save data
    output_data = {
        "company": "Bully Pulpit International",
        "competitor_id": "bpi",
        "page": "Recent Work",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "work_count": len(work_items),
        "work_items": work_items
    }
    
    with open('bpi_work_final.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Save CSV
    import csv
    if work_items:
        # Flatten nested data for CSV
        csv_items = []
        for work in work_items:
            csv_item = {
                'title': work.get('title', ''),
                'client': work.get('client', ''),
                'subtitle': work.get('subtitle', ''),
                'description': work.get('description', ''),
                'categories': ', '.join(work.get('categories', [])),
                'url': work.get('url', ''),
                'has_image': work.get('has_image', False),
                'image_url': work.get('image_url', '')
            }
            csv_items.append(csv_item)
        
        with open('bpi_work_final.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=csv_items[0].keys())
            writer.writeheader()
            writer.writerows(csv_items)
    
    print("💾 FILES CREATED:")
    print("   • bpi_work_final.json (detailed data)")
    print("   • bpi_work_final.csv (flattened data)")
    print("   • work_page.html (debug)")
    print("=" * 70)
    
    print("\n" + "=" * 70)
    print(f"✅ DEEP SCRAPE COMPLETE! {len(work_items)} case studies")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
