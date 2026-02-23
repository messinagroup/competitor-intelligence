import requests

SUPABASE_URL = "https://hhgtzjyjkcnwkawcgfbv.supabase.co/functions/v1/import"
API_KEY = "bpi_test_key_12345"

wins = [
    {"title": "The Fight for Consumer-Friendly Earned Wage Access (EWA) Regulation", "industry": "Finance & Fintech", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Retail Reimagined: A Tech-Driven Narrative Shift", "industry": "Retail & Technology", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Turning the Page on the \"Old Delaware Way\"", "industry": "Government & Politics", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Overcoming Political Roadblocks For A Cultural Institution", "industry": "Arts & Culture", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Winning the biggest BitLicense in recent history and helping the new economy work at full speed", "industry": "Crypto & Fintech", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Lights, Camera, Legislation: Expanding the Film and TV Tax Credit", "industry": "Entertainment & Media", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Enacting First-Mover AI Legislation", "industry": "Technology & AI", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Creating a viral moment to advance gun control policy", "industry": "Policy & Advocacy", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Creating a transportation revolution", "industry": "Transportation", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Passing fantasy sports legislation in 16 states", "industry": "Gaming & Sports", "url": "https://tuskstrategies.com/wins/"},
    {"title": "Creative and Paid Media", "industry": "Media & Communications", "url": "https://tuskstrategies.com/wins/"},
]

for w in wins:
    w["client"] = "Tusk Strategies"
    w["competitor_id"] = "tusk"

r = requests.post(SUPABASE_URL, json=wins, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "x-api-key": API_KEY
}, timeout=15)
print(f"{r.status_code} — {r.text}")
