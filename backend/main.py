from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn
import os
import sys
import yaml
import datetime

# 상위 폴더 경로 추가하여 모듈 임포트 가능하도록 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import init_db, get_session
from database.models import DealArticle, ResearchDomain, SearchKeyword
from main_pipeline import run_pipeline
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from newspaper import Article
from processor.analyzer import analyze_text
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
    sort_by: str = Query("latest") # "latest" or "importance"
):
    engine = init_db()
    session = get_session(engine)
    
    query = session.query(DealArticle)
    
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

is_crawling = False

def run_pipeline_task():
    global is_crawling
    if is_crawling: return
    is_crawling = True
    try:
        run_pipeline()
    finally:
        is_crawling = False

@app.post("/api/crawl_now")
def crawl_now(background_tasks: BackgroundTasks):
    global is_crawling
    if is_crawling:
        return {"status": "error", "message": "이미 수집 중입니다. 잠시만 기다려 주세요."}
    background_tasks.add_task(run_pipeline_task)
    return {"status": "success", "message": "실시간 데이터 수집 및 업데이트가 백그라운드에서 시작되었습니다."}

@app.get("/api/crawl_status")
def get_crawl_status():
    global is_crawling
    return {"status": "success", "is_crawling": is_crawling}

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
        
        result = analyze_text(title, "", req.url)
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
