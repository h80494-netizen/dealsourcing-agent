from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn
import os
import sys

# 상위 폴더 경로 추가하여 모듈 임포트 가능하도록 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import init_db, get_session
from database.models import DealArticle, ResearchDomain, SearchKeyword
from main_pipeline import run_pipeline
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import desc

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

@app.post("/api/crawl_now")
def crawl_now(background_tasks: BackgroundTasks):
    # 백그라운드에서 크롤링 파이프라인 실행
    background_tasks.add_task(run_pipeline)
    return {"status": "success", "message": "실시간 데이터 수집 및 업데이트가 백그라운드에서 시작되었습니다."}

@app.get("/api/domains")
def get_domains():
    engine = init_db()
    session = get_session(engine)
    results = session.query(ResearchDomain).all()
    session.close()
    return {"status": "success", "data": [{"id": r.id, "name": r.name, "url": r.url, "rss_url": r.rss_url, "purpose": r.purpose, "country": r.country, "category": r.category, "is_active": r.is_active} for r in results]}

@app.post("/api/domains")
def create_domain(domain: DomainCreate):
    engine = init_db()
    session = get_session(engine)
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
    return {"status": "success", "data": [{"id": r.id, "keyword": r.keyword, "type": r.type, "category": r.category, "is_active": r.is_active} for r in results]}

@app.post("/api/keywords")
def create_keyword(kw: KeywordCreate):
    engine = init_db()
    session = get_session(engine)
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
def delete_keyword(keyword_id: int):
    engine = init_db()
    session = get_session(engine)
    kw = session.query(SearchKeyword).filter_by(id=keyword_id).first()
    if kw:
        session.delete(kw)
        session.commit()
    session.close()
    return {"status": "success"}

@app.get("/api/report")
def generate_report():
    try:
        from processor.report_generator import generate_daily_report
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
    
    from processor.analyzer import analyze_text
    from newspaper import Article
    import datetime
    
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
