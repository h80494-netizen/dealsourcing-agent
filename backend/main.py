from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn
import os
import sys
import yaml
import datetime
import asyncio

import google.generativeai as genai
from dotenv import load_dotenv

# 상위 폴더 경로 추가하여 모듈 임포트 가능하도록 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import init_db, get_session
from database.models import DealArticle, ResearchDomain, SearchKeyword
from main_pipeline import run_pipeline
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from newspaper import Article
from processor.analyzer import analyze_text, extract_and_clean_text
from processor.report_generator import generate_daily_report

app = FastAPI(title="VC Deal Sourcing API")

class DomainCreate(BaseModel):
    url: str
    country: str
    category: str
    name: Optional[str] = None
    rss_url: Optional[str] = None
    purpose: Optional[str] = None

class KeywordCreate(BaseModel):
    keyword: str
    type: str
    category: str

class UrlBriefingRequest(BaseModel):
    urls: List[str]
    grade_option: str

async def fetch_url_content(url: str) -> str:
    import asyncio
    # newspaper3k를 사용하여 본문 텍스트 추출 (mcp-server-fetch 대신 내장 라이브러리 사용)
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, extract_and_clean_text, url)
    if text and len(text.strip()) > 0:
        return text
    return "내용이 없습니다."

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
# Create frontend dir if not exists (for now)
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/static", NoCacheStaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

@app.get("/api/articles")
def get_articles(
    country: List[str] = Query([]),
    deal_stage: List[str] = Query([]),
    news_grade: List[str] = Query([]),
    promising_industry: List[str] = Query([]),
    sort_by: str = Query("latest"), # "latest" or "importance"
    date_filter: str = Query(None) # e.g. "yesterday"
):
    engine = init_db()
    session = get_session(engine)
    
    query = session.query(DealArticle)

    if date_filter == "yesterday":
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(DealArticle.created_at >= start_of_yesterday)
    elif date_filter == "today":
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(DealArticle.created_at >= today)
    elif date_filter == "1week":
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        start_of_week_ago = week_ago.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(DealArticle.created_at >= start_of_week_ago)
    elif date_filter == "1month":
        month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        start_of_month_ago = month_ago.replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(DealArticle.created_at >= start_of_month_ago)
        
    if country and len(country) > 0 and country[0] != "":
        query = query.filter(DealArticle.country.in_(country))
    if deal_stage and len(deal_stage) > 0 and deal_stage[0] != "":
        query = query.filter(DealArticle.deal_stage.in_(deal_stage))
    if news_grade and len(news_grade) > 0 and news_grade[0] != "":
        query = query.filter(DealArticle.news_grade.in_(news_grade))
    if promising_industry and len(promising_industry) > 0 and promising_industry[0] != "":
        from sqlalchemy import or_
        conditions = [DealArticle.promising_industry.like(f"%{ind}%") for ind in promising_industry if ind]
        if conditions:
            query = query.filter(or_(*conditions))
        
    if sort_by == "importance":
        query = query.order_by(desc(DealArticle.impact_score), desc(DealArticle.created_at))
    else:
        query = query.order_by(desc(DealArticle.created_at))
        
    results = query.limit(200).all()
    session.close()
    
    data = []
    for r in results:
        data.append({
            "id": r.id,
            "source_name": r.source_name,
            "title": r.title,
            "link": r.link,
            "pub_date": r.pub_date,
            "summary": r.summary,
            "matched_industry": r.matched_industry,
            "matched_signal": r.matched_signal,
            "matched_financial": r.matched_financial,
            "country": r.country,
            "deal_stage": r.deal_stage,
            "impact_score": r.impact_score,
            "news_grade": r.news_grade,
            "promising_industry": r.promising_industry,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None
        })
    return {"status": "success", "count": len(data), "data": data}

crawl_result = {}
is_crawling = False

def run_pipeline_task():
    global is_crawling, crawl_result
    if is_crawling: return
    is_crawling = True
    try:
        crawl_result = run_pipeline()
    finally:
        is_crawling = False

@app.post("/api/crawl_now")
def crawl_now(background_tasks: BackgroundTasks):
    global is_crawling, crawl_result
    if is_crawling:
        return {"status": "error", "message": "이미 수집 중입니다. 잠시만 기다려 주세요."}
    crawl_result = {}
    background_tasks.add_task(run_pipeline_task)
    return {"status": "success", "message": "실시간 데이터 수집 및 업데이트가 백그라운드에서 시작되었습니다."}

@app.get("/api/crawl_status")
def get_crawl_status():
    global is_crawling, crawl_result
    return {"status": "success", "is_crawling": is_crawling, "result": crawl_result}

@app.get("/api/domains")
def get_domains():
    engine = init_db()
    session = get_session(engine)
    results = session.query(ResearchDomain).all()
    session.close()
    
    data = [{"id": r.id, "name": r.name, "url": r.url, "rss_url": r.rss_url, "purpose": r.purpose, "country": r.country, "category": r.category, "is_active": r.is_active, "is_builtin": False} for r in results]
    
    builtin_domains = [
        {"id": "builtin_naver", "name": "Naver News", "url": "https://news.naver.com", "rss_url": None, "purpose": "한국 벤처/스타트업/경제 뉴스", "country": "한국", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_kr", "name": "Google News (KR)", "url": "https://news.google.com/?hl=ko&gl=KR", "rss_url": "https://news.google.com/rss", "purpose": "한국 IT/스타트업", "country": "한국", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_us", "name": "Google News (US)", "url": "https://news.google.com/?hl=en-US&gl=US", "rss_url": "https://news.google.com/rss", "purpose": "미국 IT/스타트업", "country": "미국", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_jp", "name": "Google News (JP)", "url": "https://news.google.com/?hl=ja&gl=JP", "rss_url": "https://news.google.com/rss", "purpose": "일본 IT/스타트업", "country": "일본", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_cn", "name": "Google News (CN)", "url": "https://news.google.com/?hl=zh-CN&gl=CN", "rss_url": "https://news.google.com/rss", "purpose": "중국 IT/스타트업", "country": "중국", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_eu", "name": "Google News (EU)", "url": "https://news.google.com/?hl=en-GB&gl=GB", "rss_url": "https://news.google.com/rss", "purpose": "유럽 IT/스타트업", "country": "유럽", "category": "news", "is_active": True, "is_builtin": True}
    ]
    data.extend(builtin_domains)
    return {"status": "success", "data": data}

@app.post("/api/domains")
def create_domain(domain: DomainCreate):
    engine = init_db()
    session = get_session(engine)
    
    # Check for duplicate url
    existing = session.query(ResearchDomain).filter_by(url=domain.url).first()
    if existing:
        session.close()
        return {"status": "error", "message": "이미 존재하는 도메인입니다."}
        
    new_domain = ResearchDomain(name=domain.name, url=domain.url, rss_url=domain.rss_url, purpose=domain.purpose, country=domain.country, category=domain.category)
    try:
        session.add(new_domain)
        session.commit()
    except Exception as e:
        session.rollback()
        session.close()
        return {"status": "error", "message": str(e)}
    session.close()
    return {"status": "success", "message": "Domain added"}

@app.delete("/api/domains/{domain_id}")
def delete_domain(domain_id: int):
    engine = init_db()
    session = get_session(engine)
    domain = session.query(ResearchDomain).filter_by(id=domain_id).first()
    if domain:
        session.delete(domain)
        session.commit()
    session.close()
    return {"status": "success"}

@app.get("/api/keywords")
def get_keywords():
    engine = init_db()
    session = get_session(engine)
    results = session.query(SearchKeyword).all()
    session.close()
    
    data = [{"id": r.id, "keyword": r.keyword, "type": r.type, "category": r.category, "is_active": r.is_active, "is_builtin": False} for r in results]
    
    # Read config.yaml
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        for cat, langs in config.get("keywords", {}).items():
            for kw in langs.get("ko", []):
                # Check if it already exists in DB to avoid double listing
                if not any(d["keyword"] == kw for d in data):
                    data.append({
                        "id": f"builtin_{cat}_{kw}", 
                        "keyword": kw, 
                        "type": "기존 (내장)", 
                        "category": cat, 
                        "is_active": True, 
                        "is_builtin": True
                    })
    except Exception as e:
        print("YAML Load Error:", e)
        
    return {"status": "success", "data": data}

@app.post("/api/keywords")
def create_keyword(kw: KeywordCreate):
    engine = init_db()
    session = get_session(engine)
    
    # Check for duplicate keyword
    existing = session.query(SearchKeyword).filter_by(keyword=kw.keyword).first()
    if existing:
        session.close()
        return {"status": "error", "message": "이미 존재하는 키워드입니다."}
        
    new_kw = SearchKeyword(keyword=kw.keyword, type=kw.type, category=kw.category)
    try:
        session.add(new_kw)
        session.commit()
    except Exception as e:
        session.rollback()
        session.close()
        return {"status": "error", "message": str(e)}
    session.close()
    return {"status": "success", "message": "Keyword added"}

@app.delete("/api/keywords/{keyword_id}")
def delete_keyword(keyword_id: str):
    engine = init_db()
    session = get_session(engine)
    
    if keyword_id.startswith('builtin_'):
        session.close()
        return {"status": "error", "message": "내장 키워드는 삭제할 수 없습니다."}
        
    try:
        kw = session.query(SearchKeyword).filter_by(id=int(keyword_id)).first()
        if kw:
            session.delete(kw)
            session.commit()
    except ValueError:
        pass
    session.close()
    return {"status": "success"}

@app.delete("/api/keywords/name/{keyword_name}")
def delete_keyword_by_name(keyword_name: str):
    engine = init_db()
    session = get_session(engine)
    kw = session.query(SearchKeyword).filter_by(keyword=keyword_name).first()
    if kw:
        session.delete(kw)
        session.commit()
    session.close()
    return {"status": "success"}

@app.get("/api/report")
def generate_report():
    try:
        report_text = generate_daily_report()
        
        if not report_text:
            return {"status": "success", "report": "최근 24시간 내 수집된 기사가 없어 리포트를 생성할 수 없습니다. 데이터를 먼저 수집해주세요."}
            
        return {"status": "success", "report": report_text}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

class AnalyzeUrlRequest(BaseModel):
    url: str

@app.post("/api/analyze_url")
def analyze_custom_url(req: AnalyzeUrlRequest):
    engine = init_db()
    session = get_session(engine)
    
    try:
        article = Article(req.url, language='ko')
        article.download()
        article.parse()
        title = article.title
        
        from datetime import datetime
        result = analyze_text(title, "", req.url, pub_date=datetime.now())
        if not result:
            session.close()
            return {"status": "error", "message": "유효한 벤처/스타트업/경제 키워드가 매칭되지 않았습니다."}
            
        new_article = DealArticle(
            source_name="Manual",
            title=title,
            link=req.url,
            pub_date=datetime.datetime.now(),
            summary=result.get('compressed_summary', '')[:200],
            matched_industry=result.get('matched_industry'),
            matched_signal=result.get('matched_signal'),
            matched_financial=result.get('matched_financial'),
            country=result.get('country'),
            deal_stage=result.get('deal_stage'),
            impact_score=result.get('impact_score'),
            news_grade=result.get('news_grade'),
            promising_industry=result.get('promising_industry'),
            compressed_summary=result.get('compressed_summary')
        )
        session.add(new_article)
        session.commit()
        session.close()
        
        return {"status": "success", "message": "URL 수동 분석 및 저장 완료", "data": result}
    except Exception as e:
        session.close()
        return {"status": "error", "message": str(e)}

@app.post("/api/generate_url_briefing")
async def generate_url_briefing(req: UrlBriefingRequest):
    if not req.urls:
        return {"status": "error", "message": "URL을 1개 이상 입력해주세요."}
    
    # .env 로드
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(dotenv_path=env_path)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"status": "error", "message": "API 키가 설정되지 않았습니다 (.env 파일 확인)."}

    engine = init_db()
    session = get_session(engine)
    
    # 1. DB에서 URL에 해당하는 기사 정보 한 번에 가져오기
    db_articles = session.query(DealArticle).filter(DealArticle.link.in_(req.urls)).all()
    url_to_summary = {article.link: article.compressed_summary or article.summary for article in db_articles}
    session.close()

    # 2. URL 콘텐츠 확보 (DB 활용 및 동시성 비동기 스크래핑)
    async def get_content(url):
        if url in url_to_summary and url_to_summary[url]:
            return url_to_summary[url]
        try:
            # DB에 없는 경우에만 스크래핑 (타임아웃 방지)
            text = await fetch_url_content(url)
            return text
        except Exception as e:
            return f"수집 실패: {e}"

    sem = asyncio.Semaphore(10) # 최대 10개 동시 크롤링
    async def safe_get_content(url):
        async with sem:
            return await get_content(url)
            
    urls_to_process = [url.strip() for url in req.urls if url.strip()]
    tasks = [safe_get_content(url) for url in urls_to_process]
    results = await asyncio.gather(*tasks)

    articles_content = ""
    for idx, (url, text) in enumerate(zip(urls_to_process, results)):
        if len(text) > 2000:
            text = text[:2000] + "... (중략)"
        articles_content += f"\n\n[기사 {idx+1}] URL: {url}\n내용: {text}\n"

    # 3. 등급 조건 (이제 프론트엔드에서 필터링해서 넘어오므로 모든 기사를 활용)
    grade_instruction = "제공된 기사들의 핵심 내용을 분석하고 가장 중요도가 높은 이슈들을 선별하여 설명해주세요."

    # 4. Gemini 호출 (마크다운 포맷) - NotebookLM 에뮬레이션 프롬프트
    prompt = f"""
당신은 최고의 벤처캐피탈(VC) 시니어 애널리스트이자, 방대한 자료를 한눈에 이해하기 쉽게 엮어내는 AI 리서치 어시스턴트(NotebookLM)입니다.
아래 제공된 여러 개의 뉴스 기사(URL 및 본문)를 바탕으로, 투자 심사역들이 단 3분 만에 글로벌 트렌드를 파악할 수 있는 **최상급 프레젠테이션 슬라이드**를 작성해주세요.

[분석할 기사 원문 데이터]
{articles_content}

[작성 지시사항]
1. {grade_instruction}
2. **NotebookLM 스타일의 종합적 시각화**: 기사들을 단순 나열하지 말고, **공통된 테마, 국가별 동향, 투자 산업별 핵심 인사이트**를 도출하여 스토리텔링 형식의 슬라이드로 구성하세요.
3. **엄격한 인용(Citation)**: 정보의 신뢰성을 위해 각 슬라이드의 핵심 팩트나 수치 뒤에는 반드시 `[출처: URL 또는 기사번호]` 형태로 인용을 명시하세요.
4. **마크다운 슬라이드 포맷 준수 (Reveal.js 렌더링용)**:
   - 각 슬라이드는 반드시 `---` (수평선 3개)로 구분해야 합니다.
   - 텍스트는 너무 길지 않게 **핵심 키워드 위주의 불릿 포인트(`-`)**로 정리하세요 (한 슬라이드당 4~5줄 이내 권장).
   - 필요하다면 마크다운 테이블(표)을 활용하여 비교 분석 자료를 시각화하세요.
   - 각 슬라이드의 큰 제목은 `#` 또는 `##`을 사용하세요.
   - 가독성을 극대화하기 위해 중요한 키워드나 기업명, 금액은 **굵게(Bold)** 처리하세요.
5. **출처 명시**: 슬라이드의 마지막 부분(또는 각 핵심 팩트 옆)에 반드시 해당 기사의 원래 출처(URL 등)를 눈에 띄게 적어주세요.

[슬라이드 구성 예시 (반드시 이 흐름을 따를 필요는 없으나 참고할 것)]
# 📊 [오늘의 브리핑 제목]
- 주요 인사이트 1줄 요약
---
## 🌐 글로벌 메가 트렌드
- 트렌드 설명 및 핵심 팩트 [출처: URL]
- 관련된 주요 기업의 행보 [출처: URL]
---
## 🇺🇸 지역별 포커스: 미국 / 북미
- (내용)
---
## 🇰🇷 지역별 포커스: 한국 및 아시아
- (내용)
---
## 💡 종합 투자 인사이트 및 결론
- (VC 심사역을 위한 액션 플랜 또는 결론)
---
## 🔗 참조 출처 모음
- [기사제목] - URL
"""
    try:
        genai.configure(api_key=api_key)
        # 다량의 기사 요약 시 무료 티어 토큰 한도(Rate Limit) 초과를 방지하기 위해 2.5-flash 모델 사용
        model = genai.GenerativeModel('gemini-3.5-flash')
        response = model.generate_content(prompt)
        return {"status": "success", "report": response.text.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
