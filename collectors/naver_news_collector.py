import requests
from bs4 import BeautifulSoup
import urllib.parse
from datetime import datetime
import time

def fetch_naver_news_html(keyword):
    """네이버 뉴스 검색 결과를 HTML 스크래핑으로 수집합니다."""
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://search.naver.com/search.naver?where=news&query={encoded_keyword}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # 네이버 뉴스 검색 결과 구조 파싱 (2024년 기준 썸네일/제목 구조)
    news_items = soup.select('.news_wrap.api_ani_send')
    
    for item in news_items:
        title_elem = item.select_one('.news_tit')
        desc_elem = item.select_one('.api_txt_lines.dsc_txt_wrap')
        
        if title_elem:
            title = title_elem.get('title') or title_elem.text
            link = title_elem.get('href')
            summary = desc_elem.text if desc_elem else ''
            
            articles.append({
                'source_name': 'NaverNewsWeb',
                'title': title,
                'link': link,
                'summary': summary,
                'pub_date': datetime.now() # 정확한 시간 추출은 복잡하므로 현재 시간 처리
            })
    return articles

def collect_naver_news(keywords):
    all_articles = []
    for kw in keywords[:5]:
        articles = fetch_naver_news_html(kw)
        all_articles.extend(articles)
        time.sleep(0.5)
    return all_articles
