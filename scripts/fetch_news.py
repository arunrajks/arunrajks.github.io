import urllib.request
import json
import xml.etree.ElementTree as ET
from googlenewsdecoder import new_decoderv1
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
import requests
import os

# Keywords that indicate the article is actually about cardamom business/farming/trade
REQUIRED_KEYWORDS = [
    'cardamom price', 'cardamom auction', 'cardamom market', 'cardamom trade',
    'cardamom farmer', 'cardamom farming', 'cardamom cultivation', 'cardamom export',
    'cardamom production', 'cardamom crop', 'cardamom spice', 'cardamom grower',
    'cardamom yield', 'cardamom harvest', 'cardamom plantation', 'spices board',
    'cardamom climate', 'cardamom rain', 'idukki cardamom', 'kerala cardamom',
    'small cardamom', 'large cardamom', 'cardamom import', 'cardamom demand',
    'cardamom supply', 'elaichi', 'elachi price', 'elakkai'
]

# Keywords that indicate the article is NOT relevant (false positives)
EXCLUDE_KEYWORDS = [
    'recipe', 'cuisine', 'cook', 'cocktail', 'drink', 'food', 'restaurant',
    'rapper', 'rap', 'royalties', 'music', 'mamdani', 'coffee blend',
    'spiced coffee', 'qaxwo', 'chai', 'latte', 'smoothie', 'bake', 'flavor'
]

def is_relevant(title, snippet):
    """Check if an article is genuinely about cardamom business/farming/trade."""
    text = (title + ' ' + (snippet or '')).lower()

    # Must match at least one required keyword
    has_required = any(kw in text for kw in REQUIRED_KEYWORDS)
    # Must not match any exclude keywords
    has_excluded = any(kw in text for kw in EXCLUDE_KEYWORDS)

    return has_required and not has_excluded

def is_within_one_month(pub_date_str):
    """Return True if the article was published within the last 30 days."""
    if not pub_date_str:
        return True
    try:
        from email.utils import parsedate_to_datetime
        pub_date = parsedate_to_datetime(pub_date_str)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        return pub_date >= cutoff
    except Exception:
        return True  # If we can't parse, include it

def fetch_and_parse():
    print("Fetching Google News RSS...")
    # Use multiple specific RSS queries to maximize relevant results
    queries = [
        "cardamom+(price+OR+auction+OR+market+OR+trade)&hl=en-IN&gl=IN&ceid=IN:en",
        "cardamom+(farming+OR+cultivation+OR+crop+OR+climate+OR+harvest)&hl=en-IN&gl=IN&ceid=IN:en",
        "cardamom+(export+OR+import+OR+agreement+OR+demand+OR+supply)&hl=en-IN&gl=IN&ceid=IN:en",
    ]

    all_items = []
    seen_titles = set()

    for query in queries:
        rss_url = f"https://news.google.com/rss/search?q={query}"
        try:
            req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=15).read()
            root = ET.fromstring(response)
            for item in root.findall('./channel/item'):
                title = item.find('title').text if item.find('title') is not None else ''
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_items.append(item)
        except Exception as e:
            print(f"Failed to fetch RSS for query {query}: {e}")

    articles = []

    for item in all_items:
        if len(articles) >= 15:
            break

        title = item.find('title').text if item.find('title') is not None else ''
        pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
        google_link = item.find('link').text if item.find('link') is not None else ''
        source = item.find('source').text if item.find('source') is not None else ''

        # Skip articles older than 30 days
        if not is_within_one_month(pubDate):
            print(f"Skipping old article: {title}")
            continue

        # Quick relevance check on just the title first
        if not is_relevant(title, ''):
            print(f"Skipping irrelevant article: {title}")
            continue

        # Decode real URL
        real_url = google_link
        try:
            decoded = new_decoderv1(google_link)
            if decoded.get('status'):
                real_url = decoded.get('decoded_url')
        except Exception as e:
            print(f"Failed to decode URL: {e}")

        # Scrape OG metadata
        image_url = None
        snippet = None
        try:
            res = requests.get(real_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            og_img = soup.find('meta', property='og:image')
            og_desc = soup.find('meta', property='og:description')
            if og_img:
                image_url = og_img.get('content')
            if og_desc:
                snippet = og_desc.get('content')
        except Exception as e:
            print(f"Failed to scrape OG metadata for {real_url}: {e}")

        # Final relevance check including snippet
        if not is_relevant(title, snippet):
            print(f"Skipping after full check: {title}")
            continue

        articles.append({
            "title": title,
            "url": real_url,
            "image": image_url,
            "description": snippet,
            "publishedAt": pubDate,
            "source": {"name": source}
        })

    output = {"articles": articles}
    os.makedirs('output', exist_ok=True)
    with open("output/latest_news.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Successfully generated {len(articles)} articles in output/latest_news.json!")

if __name__ == "__main__":
    fetch_and_parse()
