import requests

SUPABASE_URL = "https://hhgtzjyjkcnwkawcgfbv.supabase.co/functions/v1/import"
API_KEY = "bpi_test_key_12345"

tests = [
    {"name": "Test Win", "title": "Public Affairs", "description": "Test", "url": "https://tuskstrategies.com", "region": None},
    {"name": "Test Win", "title": "Public Affairs", "description": "Test", "url": "https://tuskstrategies.com"},
    {"name": "Test Win", "title": "Public Affairs", "description": "Test"},
    {"title": "Test Win", "url": "https://tuskstrategies.com", "location": "New York"},
]

for i, payload in enumerate(tests):
    r = requests.post(SUPABASE_URL, json=[payload], headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}", "x-api-key": API_KEY}, timeout=15)
    print(f"Test {i+1} fields={list(payload.keys())} → {r.status_code} — {r.text[:120]}")
