import feedparser
import urllib.parse
from datetime import datetime
import time
from config import INDUSTRY_KEYWORDS_DICT, SIGNAL_KEYWORDS_DICT

def get_google_news_params(country):
    if country == "미국":
        return "hl=en-US&gl=US&ceid=US:en", "en"
    elif country == "일본":
        return "hl=ja&gl=JP&ceid=JP:ja", "ja"
    elif country == "중국":
        return "hl=zh-CN&gl=CN&ceid=CN:zh-Hans", "zh"
    elif country == "독일":
        return "hl=de&gl=DE&ceid=DE:de", "de"
    elif country == "프랑스":
        return "hl=fr&gl=FR&ceid=FR:fr", "fr"
    elif country == "유럽":
        return "hl=en-GB&gl=GB&ceid=GB:en", "en"
    return "hl=ko&gl=KR&ceid=KR:ko", "ko"

def fetch_custom_rss(rss_url, source_name="CustomRSS", country="한국"):
    """제공된 RSS URL에서 기사를 수집합니다."""
    feed = feedparser.parse(rss_url)
    articles = []
    
    for entry in feed.entries:
        try:
            pub_date = datetime(*entry.published_parsed[:6]) if 'published_parsed' in entry else datetime.now()
        except:
            pub_date = datetime.now()
            
        articles.append({
            'source_name': source_name,
            'title': entry.title,
            'link': entry.link,
            'summary': entry.get('summary', ''),
            'pub_date': pub_date,
            'country': country
        })
    return articles

def fetch_google_news_rss(keyword, country="한국"):
    """Google News RSS를 통해 특정 키워드의 기사를 수집합니다."""
    import requests
    import random
    encoded_keyword = urllib.parse.quote(keyword)
    params, _ = get_google_news_params(country)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&{params}"
    
    # 봇 차단 우회를 위해 다양한 User-Agent 사용
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
                    'source_name': f'GoogleNews ({country})',
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary', ''),
                    'pub_date': pub_date,
                    'country': country
                })
    except Exception as e:
        print(f"Error fetching Google News for {keyword} in {country}: {e}")
        
    return articles

import concurrent.futures

def collect_all_rss(domains=None):
    all_articles = []
    
    # 1. Custom RSS 수집
    if domains:
        for d in domains:
            if getattr(d, 'rss_url', None) and getattr(d, 'is_active', True):
                try:
                    articles = fetch_custom_rss(d.rss_url, source_name=d.name or d.url, country=d.country)
                    all_articles.extend(articles)
                except Exception as e:
                    print(f"Error fetching RSS from {d.rss_url}: {e}")
                
    # 2. 키워드 기반 글로벌 뉴스 수집
    countries = ["한국", "미국", "일본", "중국", "유럽", "독일", "프랑스"]
    
    tasks = []
    for country in countries:
        _, lang = get_google_news_params(country)
        lang_signals = SIGNAL_KEYWORDS_DICT.get(lang, [])[:3]
        lang_industries = INDUSTRY_KEYWORDS_DICT.get(lang, [])[:2]
        search_kws = lang_signals + lang_industries
        for kw in search_kws:
            tasks.append((kw, country))
            
    def fetch_task(args):
        kw, country = args
        try:
            return fetch_google_news_rss(kw, country)
        except:
            return []
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_task, tasks))
        for res in results:
            all_articles.extend(res)
            
    return all_articles
