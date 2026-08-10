import urllib.parse
from datetime import datetime
import time
import requests
import feedparser
import random

def fetch_naver_news_html(keyword):
    """네이버 뉴스를 검색합니다. (Google News RSS의 site:naver.com 필터 활용하여 우회)"""
    encoded_keyword = urllib.parse.quote(keyword + " site:naver.com")
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
    ]
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'application/rss+xml, application/xml, text/xml'
    }
    
    articles = []
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            for entry in feed.entries:
                try:
                    pub_date = datetime(*entry.published_parsed[:6]) if 'published_parsed' in entry else datetime.now()
                except:
                    pub_date = datetime.now()
                    
                articles.append({
                    'source_name': 'NaverNewsWeb',
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary', ''),
                    'pub_date': pub_date
                })
    except Exception as e:
        print(f"Error fetching Naver news via Google RSS for {keyword}: {e}")
        
    return articles

def collect_naver_news(keywords):
    all_articles = []
    for kw in keywords[:5]:
        articles = fetch_naver_news_html(kw)
        all_articles.extend(articles)
        time.sleep(1)
    return all_articles
