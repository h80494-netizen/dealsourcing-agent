import feedparser
import urllib.parse
from datetime import datetime
import time
import concurrent.futures
import requests
import random
from config import INDUSTRY_KEYWORDS_DICT, SIGNAL_KEYWORDS_DICT, PUBLIC_GOV_SOURCES

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

def _default_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0'
    ]
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
    }

def fetch_custom_rss(rss_url, source_name="CustomRSS", country="한국", source_type="private_media", ministry_name=None):
    """제공된 RSS URL에서 기사를 수집합니다."""
    articles = []
    try:
        resp = requests.get(rss_url, headers=_default_headers(), timeout=15)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.content)
        else:
            feed = feedparser.parse(rss_url)
    except Exception:
        feed = feedparser.parse(rss_url)

    for entry in feed.entries:
        try:
            pub_date = datetime(*entry.published_parsed[:6]) if 'published_parsed' in entry and entry.published_parsed else datetime.now()
        except Exception:
            pub_date = datetime.now()

        articles.append({
            'source_name': source_name,
            'source_type': source_type,
            'ministry_name': ministry_name,
            'title': entry.title,
            'link': entry.link,
            'summary': entry.get('summary', ''),
            'pub_date': pub_date,
            'country': country
        })
    return articles

def fetch_google_news_rss(keyword, country="한국", source_name=None, source_type="private_media", ministry_name=None):
    """Google News RSS를 통해 특정 키워드의 기사를 수집합니다."""
    encoded_keyword = urllib.parse.quote(keyword)
    params, _ = get_google_news_params(country)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&{params}"

    articles = []
    try:
        response = requests.get(url, headers=_default_headers(), timeout=15)
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            for entry in feed.entries:
                try:
                    pub_date = datetime(*entry.published_parsed[:6]) if 'published_parsed' in entry and entry.published_parsed else datetime.now()
                except Exception:
                    pub_date = datetime.now()

                articles.append({
                    'source_name': source_name or f'GoogleNews ({country})',
                    'source_type': source_type,
                    'ministry_name': ministry_name,
                    'title': entry.title,
                    'link': entry.link,
                    'summary': entry.get('summary', ''),
                    'pub_date': pub_date,
                    'country': country
                })
    except Exception as e:
        print(f"Error fetching Google News for {keyword} in {country}: {e}")

    return articles

def collect_public_gov_news(limit_per_ministry=20):
    """대한민국 정책브리핑(korea.kr) 및 주요 벤처 유관 부처(중기부·과기부·금융위·산업부·특허청) 공식 뉴스 수집"""
    gov_articles = []
    sources = PUBLIC_GOV_SOURCES or [
        {"ministry": "중소벤처기업부", "query": "site:korea.kr 중소벤처기업부 (벤처투자 OR 모태펀드 OR 스타트업 OR 팁스)"},
        {"ministry": "과학기술정보통신부", "query": "site:korea.kr 과학기술정보통신부 (AI OR 딥테크 OR R&D OR 창업)"},
        {"ministry": "금융위원회", "query": "site:korea.kr 금융위원회 (벤처 OR 모험자본 OR 코스닥 OR 혁신금융)"},
        {"ministry": "산업통상자원부", "query": "site:korea.kr 산업통상자원부 (반도체 OR 로봇 OR 바이오 OR 산업기술펀드)"},
    ]

    def _fetch_gov(src):
        ministry = src.get("ministry", "정부부처")
        query = src.get("query", f"site:korea.kr {ministry} 벤처")
        items = fetch_google_news_rss(
            keyword=query,
            country="한국",
            source_name=f"정책브리핑 ({ministry})",
            source_type="public_gov",
            ministry_name=ministry
        )
        return items[:limit_per_ministry]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for res in executor.map(_fetch_gov, sources):
            gov_articles.extend(res)

    return gov_articles

def collect_all_rss(domains=None, include_public_gov=True):
    all_articles = []

    # 1. Custom RSS 수집
    if domains:
        for d in domains:
            if getattr(d, 'rss_url', None) and getattr(d, 'is_active', True):
                try:
                    cat = getattr(d, 'category', '') or ''
                    is_gov = ('정부' in cat or '정책' in cat or '기관' in cat)
                    articles = fetch_custom_rss(
                        d.rss_url,
                        source_name=d.name or d.url,
                        country=d.country,
                        source_type='public_gov' if is_gov else 'private_media',
                        ministry_name=d.name if is_gov else None
                    )
                    all_articles.extend(articles)
                except Exception as e:
                    print(f"Error fetching RSS from {d.rss_url}: {e}")

    # 2. 공공기관/부처 공식 정책브리핑 수집
    if include_public_gov:
        try:
            gov_items = collect_public_gov_news(limit_per_ministry=15)
            all_articles.extend(gov_items)
        except Exception as e:
            print(f"Error fetching public gov news: {e}")

    # 3. 키워드 기반 글로벌 민간 뉴스 수집
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
        except Exception:
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_task, tasks))
        for res in results:
            all_articles.extend(res)

    return all_articles
