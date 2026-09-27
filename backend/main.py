from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
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

class ApiKeyRequest(BaseModel):
    api_key: str

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
    date_filter: str = Query(None), # e.g. "yesterday"
    page: int = Query(1),
    page_size: int = Query(20)
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
        
    total_count = query.count()
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()
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
    import math
    return {
        "status": "success",
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total_count / page_size),
        "data": data
    }

@app.get("/api/statistics")
def get_statistics():
    engine = init_db()
    session = get_session(engine)
    
    import datetime
    now = datetime.datetime.now()
    
    # 시간 기준 설정
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - datetime.timedelta(days=1)
    yesterday_end = today_start
    week_start = today_start - datetime.timedelta(days=7)
    month_start = today_start - datetime.timedelta(days=30)
    
    periods = {
        "today": (today_start, None),
        "yesterday": (yesterday_start, yesterday_end),
        "1week": (week_start, None),
        "1month": (month_start, None)
    }
    
    stats_data = {}
    
    for period_name, (start_time, end_time) in periods.items():
        query = session.query(DealArticle)
        if end_time:
            query = query.filter(DealArticle.created_at >= start_time, DealArticle.created_at < end_time)
        else:
            query = query.filter(DealArticle.created_at >= start_time)
            
        articles = query.all()
        
        total = len(articles)
        country_counts = {}
        stage_counts = {}
        grade_counts = {}
        total_impact = 0.0
        
        for art in articles:
            c = art.country or "기타"
            country_counts[c] = country_counts.get(c, 0) + 1
            
            s = art.deal_stage or "기타"
            stage_counts[s] = stage_counts.get(s, 0) + 1
            
            g = art.news_grade or "기타"
            grade_counts[g] = grade_counts.get(g, 0) + 1
            
            total_impact += art.impact_score if art.impact_score else 0.0
            
        avg_impact = round(total_impact / total, 1) if total > 0 else 0.0
        
        stats_data[period_name] = {
            "total_count": total,
            "avg_impact": avg_impact,
            "countries": country_counts,
            "stages": stage_counts,
            "grades": grade_counts
        }
        
    session.close()
    return {"status": "success", "data": stats_data}


crawl_result = {}
is_crawling = False
crawl_progress = {"status": "idle", "message": "", "current": 0, "total": 0, "percent": 0}

def run_pipeline_task(days_limit: int, max_articles: int = 50):
    global is_crawling, crawl_result, crawl_progress
    if is_crawling: return
    is_crawling = True
    crawl_progress = {"status": "starting", "message": "데이터 수집 및 크롤링을 준비하는 중...", "current": 0, "total": 0, "percent": 0}
    try:
        def pipeline_callback(msg, current, total):
            global crawl_progress
            crawl_progress = {
                "status": "analyzing",
                "message": msg,
                "current": current,
                "total": total,
                "percent": int((current / total) * 100) if total > 0 else 0
            }
        
        # 수집 전 단계를 기록하기 위해 run_pipeline 내부 진입 전 메시지 표시
        crawl_progress["message"] = "글로벌 뉴스 RSS 및 네이버 뉴스를 수집하는 중..."
        crawl_result = run_pipeline(progress_callback=pipeline_callback, days_limit=days_limit, max_articles=max_articles)
        crawl_progress = {"status": "completed", "message": "수집 및 AI 분석 완료!", "current": 100, "total": 100, "percent": 100}
    except Exception as e:
        err_msg = str(e)
        friendly_msg = f"수집 실패: {err_msg}"
        if "429" in err_msg or "quota" in err_msg.lower() or "limit" in err_msg.lower():
            friendly_msg = "Gemini API 호출 한도(429 Quota Exceeded)를 초과했습니다. 법인 API 키로 전환하시거나 잠시 후 다시 실행해주세요."
        elif "rate limit" in err_msg.lower():
            friendly_msg = "API 속도 제한을 초과했습니다. 몇 분 후에 다시 가동해 주세요."
        crawl_progress = {"status": "failed", "message": friendly_msg, "current": 0, "total": 0, "percent": 0}
    finally:
        is_crawling = False

@app.post("/api/crawl_now")
def crawl_now(background_tasks: BackgroundTasks, days_limit: int = Query(30), max_articles: int = Query(50)):
    global is_crawling, crawl_result, crawl_progress
    if is_crawling:
        return {"status": "error", "message": "이미 수집 중입니다. 잠시만 기다려 주세요."}
    crawl_result = {}
    background_tasks.add_task(run_pipeline_task, days_limit, max_articles)
    return {"status": "success", "message": f"실시간 데이터 수집 및 업데이트({days_limit}일 기준, 최대 {max_articles}건)가 백그라운드에서 시작되었습니다."}

@app.get("/api/crawl_status")
def get_crawl_status():
    global is_crawling, crawl_result, crawl_progress
    return {"status": "success", "is_crawling": is_crawling, "progress": crawl_progress, "result": crawl_result}

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

    # 3. 선택된 기사 수에 따른 프롬프트 생성 (5개 이상 시 5페이지 이상 심층분석리포트)
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    num_articles = len(urls_to_process)
    
    if num_articles >= 5:
        # 5개 이상 기사 선택 시: 5페이지 이상 심층분석 보고서 프롬프트
        prompt = f"""
당신은 글로벌 탑티어 벤처캐피탈(VC)의 수석 파트너이자 최고 산업 분석가(Chief Analyst)입니다.
수집된 {num_articles}개의 뉴스 기사와 관련 기업/산업 정보 원문을 종합 분석하여, 투자심의위원회에 즉시 제출할 수 있는 **최소 5페이지(5개 이상의 대형 챕터) 이상의 전문 심층분석 보고서(Deep-Dive Investment & Industry Report)**를 작성해 주세요.

[기준 일자]
- 리포트 작성일: {today_str}
- 기사 시점 해석 시 위 작성일을 기준으로 작성하세요.

[분석 대상 기사 원문 데이터 ({num_articles}건)]
{articles_content}

[보고서 작성 가이드라인 (반드시 준수)]
1. **분량 및 구조 (최소 5페이지 이상 분량 보장)**:
   - 보고서는 아래 명시된 **5개 이상의 대형 챕터(# 및 ##)**로 구성하고, 각 챕터마다 풍부한 서술과 구체적인 표/데이터를 포함하여 총 A4 5페이지 이상 분량의 깊이 있는 전문 리포트로 구성하세요.
   - 절대로 간단한 요약에 그치지 말고, 산업적 맥락과 기업 비즈니스 모델을 구체적으로 분석해 주세요.

2. **기업명 및 기사 출처 국가(국가명) 필수 표기 규칙 (매우 중요)**:
   - **기업명 국가 표기**: 본문, 표, 서론 등에서 언급되는 모든 기업명 뒤에는 반드시 **소속 국가(미국, 한국, 일본, 중국, 유럽 등)**를 명시하세요. (예: **OpenAI (미국)**, **네이버 (한국)**, **SoftBank (일본)**, **카카오 (한국)**, **ASML (유럽/네덜란드)**).
   - **기사 출처 국가 표기**: 구체적인 팩트 인용이나 6페이지 출처 모음 부분의 매체명 및 기사 출처에는 반드시 **기사 출처 국가**를 명시하세요. (예: **[출처: TechCrunch (미국) / 2024-10-12]**, **[출처: 한국경제 (한국) / 2024-10-12]**, **[출처: Nihon Keizai Shimbun (일본) / 2024-10-12]**).

3. **서론 및 본론의 전문성 극대화**:
   - **[서론] 전문 산업 동향**: 단순 뉴스 요약이 아닌, 해당 산업 분야의 글로벌 기술 개발 트렌드, 시장 규모 및 성장률(CAGR), 글로벌 규제 환경, 메가 트렌드 변화를 학술/투자리포트 수준으로 구체적으로 서술하세요.
   - **[본론] 구체적인 기업 정보 정리**: 기사에 언급된 스타트업/기업들(및 관련 대표 경쟁사들)의 **기업명 (국가명 필수 포함), 핵심 기술/제품, 대표자/창업진 배경, 투자 유치 단계(Seed/Series A~Unicorn), 예상 밸류에이션, 주요 매출/재무 지표, 핵심 경쟁 우위(Moat)**를 마크다운 테이블(표)과 함께 매우 구체적으로 세분화하여 정리하세요.
   - **[본론] 딜 스펙트럼 및 기술 비교**: 주요 딜의 투자자(VC/CVC), 금액, 전략적 타겟을 명시하고 기술적 차별점을 다각도로 비교 분석하세요.

4. **마크다운 서식 준수**:
   - 챕터 제목은 `#`, `##`을 사용하고, 중요 기업명/수치는 **굵게(Bold)**, 비교는 **마크다운 표(Table)**로 가독성을 극대화하세요.
   - 슬라이드 구분선(`---`) 없이 매끄럽게 이어지는 완결된 5페이지 이상의 심층 보고서 형태로 작성하세요.

[보고서 구성 필수 목차 구조]
# 📄 [글로벌 VC 심층 분석] 기술 산업 동향 및 핵심 기업 투자 분석 보고서
*작성일자: {today_str} | 수집 딜 기사: 총 {num_articles}건*

---

## 1페이지: Executive Summary & 글로벌 산업 메가 트렌드 (서론)
- **1.1 종합 요약 (Executive Summary)**: 현 시점 투자 시장의 핵심 키워드 및 시사점
- **1.2 글로벌 산업 동향 및 기술 파동 분석**: 
  - 최근 글로벌 시장 규모, 성장 전망, 주요 기술적 변곡점(Inflection Point) 분석
  - 국가별/정책별(미국, 한국, 일본, 유럽, 중국 등) 산업 지원책 및 규제 동향 전문 정리

## 2페이지: 주요 섹터별 기술 체계 및 세부 산업 동향 (본론 I)
- **2.1 세부 섹터별 핵심 이슈 분석**: 기술 분야별(예: Generative AI, Semiconductor, Biotech, CleanTech 등) 최신 산업 트렌드 및 국가별 동향
- **2.2 시장 경쟁 구도 및 Value Chain 분석**: 공급망, 기술 생태계 및 전방/후방 산업 파급 효과

## 3페이지: 타겟 기업 심층 분석 및 비즈니스 모델 (본론 II)
- **3.1 핵심 관심 기업 프로필 및 재무/투자 현황 (상세 마크다운 표)**:
  | 기업명 (국가) | 소속 국가 | 주요 제품/핵심 기술 | 투자 단계 | 추정 밸류 / 펀딩액 | 핵심 경쟁력 & Moat |
- **3.2 기업별 비즈니스 모델(BM) 및 기술력 심층 서술**: 기사 속 핵심 기업(국가 명시)들의 기술 특허, 경영진 역량, 매출 구조, 성장 동력 구체적 분석

## 4페이지: 주요 딜(Deal) 스펙트럼 & 시장 영향력 평가 (본론 III)
- **4.1 최근 투자/M&A/IPO 딜 트렌드 종합 비교**: 투자 규모별, 주요 투자사(Lead VC)별 전략 분석
- **4.2 투자 유치 기업(국가 명시)과 기존 앤터프라이즈/빅테크 간 전략적 제휴 및 경쟁 구도**

## 5페이지: VC 투자 인사이트, 밸류에이션 & 리스크 평가 (결론)
- **5.1 벤처캐피탈(VC) 투자 시사점 및 Deal Sourcing 기회**: 투자 관점에서의 타겟 분야 및 평가 기준
- **5.2 주요 리스크 요인 (Market, Tech, Financial, Regulatory Risk)**
- **5.3 밸류에이션 프레임워크 및 향후 회수(Exit) 가능성**

## 🔗 6페이지: 참조 기사 원문 및 출처 모음
- 수집된 기사 URL, 매체명(국가 명시) 및 주요 내용 요약 링킹 [예: TechCrunch (미국) / 2024-10-12]
"""
    else:
        # 5개 미만 기사 선택 시 기본 보고서 프롬프트 (전문성 및 국가명 보강)
        prompt = f"""
당신은 최고의 벤처캐피탈(VC) 시니어 애널리스트입니다.
아래 제공된 {num_articles}개의 뉴스 기사를 분석하여, 투자 심사역을 위한 **A4 보고서 형식의 전문 분석 리포트**를 작성해 주세요.

[기준 일자]
- 오늘 날짜(작성일자): {today_str}

[분석할 기사 원문 데이터]
{articles_content}

[작성 지시사항]
1. **기업명 및 기사 출처 국가 명시 필수**:
   - 본문/표에 등장하는 모든 기업명 뒤에 소속 국가(예: **OpenAI (미국)**, **네이버 (한국)**, **SoftBank (일본)**)를 반드시 명시하세요.
   - 각 기사 인용 및 출처 모음에는 매체명과 함께 출처 국가(예: **[출처: TechCrunch (미국) / 2024-10-12]**)를 명시하세요.
2. **서론 및 본론 전문성 강화**:
   - **서론**: 해당 기사들이 속한 산업의 최신 기술 동향, 시장 변화 및 배경을 전문적인 관점에서 서술하세요.
   - **본론**: 언급된 기업들의 핵심 제품, 기술 우위, 투자 단계 및 재무/성장 정보를 구체적으로 정리하고 마크다운 표를 활용하세요.
3. 마크다운 포맷(`#`, `##`, 표, 굵은 글씨)을 준수하여 가독성을 극대화하세요.

[보고서 구성 예시]
# 📄 글로벌 산업 동향 및 주요 기업 이슈 보고서
## 1. 서론: 산업 동향 및 기술 배경 (국가별 트렌드)
## 2. 본론: 핵심 기업 및 투자/딜 분석 (기업명(국가) 및 기업 정보 표 포함)
## 3. 결론: VC 투자 인사이트 및 시사점
## 🔗 참조 기사 모음 (매체명/국가/발행일 명시)
"""
    try:
        genai.configure(api_key=api_key)
        # 5개 이상 심층 리포트 작성 시 충분한 길이를 출력할 수 있도록 flash 모델 활용
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return {"status": "success", "report": response.text.strip()}
    except Exception as e:
        # flash 실패 시 fallback
        try:
            model = genai.GenerativeModel('gemini-flash-lite-latest')
            response = model.generate_content(prompt)
            return {"status": "success", "report": response.text.strip()}
        except Exception as ex:
            return {"status": "error", "message": str(ex)}

@app.post("/api/update_api_key")
def update_api_key(req: ApiKeyRequest):
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
        new_lines = []
        found = False
        for line in lines:
            if line.startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={req.api_key}\n")
                found = True
            else:
                new_lines.append(line)
                
        if not found:
            new_lines.append(f"GEMINI_API_KEY={req.api_key}\n")
            
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        os.environ["GEMINI_API_KEY"] = req.api_key
        return {"status": "success", "message": "API 키가 성공적으로 업데이트되었습니다."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/download/valuation_excel")
def download_valuation_excel():
    excel_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data", "Startup_Valuation_Master_All_Methods_and_Cases.xlsx"))
    if not os.path.exists(excel_path):
        alt_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "Startup_Valuation_Master_All_Methods_and_Cases.xlsx"))
        if os.path.exists(alt_path):
            excel_path = alt_path
        else:
            return {"status": "error", "message": "엑셀 파일을 찾을 수 없습니다."}
    return FileResponse(
        path=excel_path,
        filename="Startup_Valuation_Master_All_Methods_and_Cases.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
