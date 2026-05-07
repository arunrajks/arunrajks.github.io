import urllib.request
import json
import xml.etree.ElementTree as ET
from googlenewsdecoder import new_decoderv1
from bs4 import BeautifulSoup
import requests
import os

def fetch_and_parse():
    print("Fetching Google News RSS...")
    rss_url = "https://news.google.com/rss/search?q=cardamom+(price+OR+market+OR+auction+OR+climate)&hl=en-IN&gl=IN&ceid=IN:en"
    
    req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req).read()
    root = ET.fromstring(response)
    
    articles = []
    
    for item in root.findall('./channel/item')[:20]:
        title = item.find('title').text if item.find('title') is not None else ''
        pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ''
        google_link = item.find('link').text if item.find('link') is not None else ''
        source = item.find('source').text if item.find('source') is not None else ''
        
        real_url = google_link
        try:
            decoded = new_decoderv1(google_link)
            if decoded.get('status'):
                real_url = decoded.get('decoded_url')
        except Exception as e:
            print(f"Failed to decode URL: {e}")
            
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
            
        articles.append({
            "title": title,
            "url": real_url,
            "image": image_url,
            "description": snippet,
            "publishedAt": pubDate,
            "source": {"name": source}
        })
        
    output = {
        "articles": articles
    }
    
    os.makedirs('output', exist_ok=True)
    with open("output/latest_news.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Successfully generated output/latest_news.json!")

if __name__ == "__main__":
    fetch_and_parse()
