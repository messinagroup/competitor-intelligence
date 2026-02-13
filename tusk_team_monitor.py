"""
Tusk Strategies Website Monitor - Sends to Lovable Dashboard
Install: pip3 install requests beautifulsoup4 lxml
Run: python3 tusk_team_monitor.py
"""

import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

class TuskMonitor:
    def __init__(self):
        self.base_url = 'https://tuskstrategies.com'
        self.pages_to_monitor = [
            'https://tuskstrategies.com/',
            'https://tuskstrategies.com/services/',
            'https://tuskstrategies.com/our-team/',
            'https://tuskstrategies.com/services/crypto-and-advanced-tech-practice/',
            'https://tuskstrategies.com/services/new-york-practice/',
        ]
        self.current_data = []
        self.previous_data = []
        self.changes = []
        self.lovable_url = os.environ.get('LOVABLE_FUNCTION_URL')
        self.lovable_key = os.environ.get('LOVABLE_API_KEY', '')
        
    def load_previous_data(self):
        try:
            if os.path.exists('data/tusk_previous.json'):
                with open('data/tusk_previous.json', 'r') as f:
                    self.previous_data = json.load(f)
                print(f"✅ Loaded previous data: {len(self.previous_data)} pages")
            else:
                print("ℹ️  No previous data found (first run)")
        except Exception as e:
            print(f"⚠️  Error loading previous data: {e}")

    def scrape_page(self, url):
        try:
            print(f"📄 Scraping: {url}")
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            title = soup.find('title')
            title = title.get_text().strip() if title else ''
            h1 = soup.find('h1')
            h1_text = h1.get_text().strip() if h1 else ''
            description = ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            main = soup.find('main') or soup.find('article') or soup.find('body')
            content = ' '.join(main.get_text().split()) if main else ''
            headings = [h.get_text().strip() for h in soup.find_all(['h2', 'h3']) if h.get_text().strip()]
            return {
                'url': url,
                'title': title,
                'h1': h1_text,
                'description': description,
                'content': content[:2000],
                'contentLength': len(content),
                'headings': headings[:10],
                'scrapedAt': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"   ✗ Error: {e}")
            return None

    def scrape_all(self):
        print('\n🔍 Scraping monitored pages...\n')
        for url in self.pages_to_monitor:
            data = self.scrape_page(url)
            if data:
                self.current_data.append(data)
        print(f"\n✅ Scraped {len(self.current_data)} pages")

    def detect_changes(self):
        print('\n📊 Detecting changes...\n')
        if not self.previous_data:
            print("🆕 First run - establishing baseline")
            self.changes = [{'type': 'new', 'page': page, 'message': 'Initial scrape'} for page in self.current_data]
            return
        prev_dict = {p['url']: p for p in self.previous_data}
        curr_dict = {p['url']: p for p in self.current_data}
        for url, current in curr_dict.items():
            if url not in prev_dict:
                self.changes.append({'type': 'new_page', 'url': url, 'title': current['title'], 'message': f"New page: {current['title']}"})
            else:
                previous = prev_dict[url]
                if current['title'] != previous['title']:
                    self.changes.append({'type': 'title_change', 'url': url, 'old': previous['title'], 'new': current['title']})
                prev_len = previous.get('contentLength', 0)
                curr_len = current.get('contentLength', 0)
                if prev_len > 0:
                    change_pct = abs(curr_len - prev_len) / prev_len * 100
                    if change_pct > 5:
                        self.changes.append({'type': 'content_change', 'url': url, 'title': current['title'], 'changePct': round(change_pct, 1)})
        if self.changes:
            print(f"🔔 Found {len(self.changes)} changes!")
        else:
            print("✓ No changes detected")

    def send_to_lovable(self):
        if not self.lovable_url:
            print("\n⚠️  LOVABLE_FUNCTION_URL not set")
            return
        if not self.changes:
            print("\n✓ No changes to send")
            return
        print(f'\n📤 Sending to Lovable...\n')
        try:
            payload = {'source': 'tusk_strategies_monitor', 'timestamp': datetime.now().isoformat(), 'changes': self.changes, 'data_type': 'website_updates'}
            headers = {'Content-Type': 'application/json'}
            if self.lovable_key:
                headers['Authorization'] = f'Bearer {self.lovable_key}'
            response = requests.post(self.lovable_url, json=payload, headers=headers, timeout=30)
            if response.status_code in [200, 201]:
                print("✅ Successfully updated Lovable!")
            else:
                print(f"⚠️  Failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")

    def save_current_data(self):
        os.makedirs('data', exist_ok=True)
        with open('data/tusk_previous.json', 'w') as f:
            json.dump(self.current_data, f, indent=2)
        print("\n✅ Saved data for next run")

    def run(self):
        print('╔════════════════════════════════════════╗')
        print('║   TUSK STRATEGIES MONITOR             ║')
        print('╚════════════════════════════════════════╝\n')
        self.load_previous_data()
        self.scrape_all()
        self.detect_changes()
        self.send_to_lovable()
        self.save_current_data()
        print('\n║   MONITORING COMPLETE                 ║\n')

if __name__ == '__main__':
    monitor = TuskMonitor()
    monitor.run()