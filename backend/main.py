from fastapi import FastAPI, BackgroundTasks, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
import uvicorn
import os
import sys
import json
import math
import yaml
import datetime
import asyncio

import google.generativeai as genai
from dotenv import load_dotenv

# 상위 폴더 경로 추가하여 모듈 임포트 가능하도록 설정
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from database.db_manager import init_db, get_session
from database.models import (
    DealArticle,
    ResearchDomain,
    SearchKeyword,
    CompanyProfile,
    VentureFund,
    VenturePolicyStat,
    GovGrantNotice,
    CompanyPatent,
    DynamicConfigRegistry,
)
from main_pipeline import run_pipeline
from sqlalchemy import desc, or_, and_
from pydantic import BaseModel
from typing import Optional, List
from processor.analyzer import analyze_text, extract_and_clean_text, determine_news_grade
from processor.ic_memo_generator import (
    generate_ic_memo,
    build_ic_memo_prompt,
    extract_text_from_pdf,
    extract_text_from_file,
    scrape_website_content,
    extract_urls_from_text,
)
from industry_manager import industry_manager
from collectors.news_rss_collector import collect_public_gov_news
from collectors.company_collector import (
    search_dart_candidates,
    fetch_dart_company_detail,
    parse_uploaded_company_report,
)
from collectors.fund_collector import sync_diva_funds_to_db
from collectors.venture_policy_collector import (
    ensure_venture_policy_stats,
    sync_live_policy_briefings,
    get_dynamic_legal_tax_registry,
)
from collectors.grant_patent_collector import sync_grants_to_db, search_company_patents

app = FastAPI(title="VC Deal Sourcing & Intelligence Pro API")


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
    api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    dart_api_key: Optional[str] = None
    data_go_kr_service_key: Optional[str] = None
    kipris_api_key: Optional[str] = None
    nice_api_key: Optional[str] = None


class AnalyzeUrlRequest(BaseModel):
    url: str


class DartFetchRequest(BaseModel):
    corp_code: Optional[str] = None
    company_name: Optional[str] = None


class FundSyncRequest(BaseModel):
    pages: int = 2
    gp_keyword: str = ""
    fund_keyword: str = ""


class PatentSearchRequest(BaseModel):
    company_name: str
    max_rows: int = 15


class ConfigUpdateRequest(BaseModel):
    config_value: str
    effective_date: Optional[str] = None
    legal_basis: Optional[str] = None
    description: Optional[str] = None


async def fetch_url_content(url: str) -> str:
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, extract_and_clean_text, url)
    if text and len(text.strip()) > 0:
        return text
    return "내용이 없습니다."


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


frontend_dir = os.path.join(ROOT_DIR, "frontend")
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/static", NoCacheStaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")


# =========================================================================
# 1. 뉴스 & 공공기관 정책브리핑 API
# =========================================================================
@app.get("/api/articles")
def get_articles(
    country: List[str] = Query([]),
    deal_stage: List[str] = Query([]),
    news_grade: List[str] = Query([]),
    promising_industry: List[str] = Query([]),
    source_type: str = Query("all"),  # "all" | "private_media" | "public_gov"
    ministry: str = Query(""),
    q: str = Query(""),
    sort_by: str = Query("latest"),
    date_filter: str = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
):
    engine = init_db()
    session = get_session(engine)

    query = session.query(DealArticle)

    if source_type == "public_gov":
        query = query.filter(DealArticle.source_type == "public_gov")
    elif source_type == "private_media":
        query = query.filter(or_(DealArticle.source_type == "private_media", DealArticle.source_type.is_(None)))

    if ministry and ministry.strip():
        query = query.filter(DealArticle.ministry_name.like(f"%{ministry.strip()}%"))

    if q and q.strip():
        kw = f"%{q.strip()}%"
        query = query.filter(or_(DealArticle.title.like(kw), DealArticle.summary.like(kw), DealArticle.source_name.like(kw)))

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
        grade_conds = []
        for g in news_grade:
            if g == "A":
                grade_conds.append(or_(DealArticle.news_grade == "A", DealArticle.impact_score >= 80))
            elif g == "B":
                grade_conds.append(or_(DealArticle.news_grade == "B", and_(DealArticle.impact_score >= 70, DealArticle.impact_score < 80)))
            elif g == "C":
                grade_conds.append(or_(DealArticle.news_grade == "C", and_(DealArticle.impact_score >= 60, DealArticle.impact_score < 70)))
            elif g == "D":
                grade_conds.append(or_(DealArticle.news_grade == "D", and_(DealArticle.impact_score >= 50, DealArticle.impact_score < 60)))
            elif g == "E":
                grade_conds.append(or_(DealArticle.news_grade == "E", DealArticle.impact_score < 50))
            else:
                grade_conds.append(DealArticle.news_grade == g)
        if grade_conds:
            query = query.filter(or_(*grade_conds))

    if promising_industry and len(promising_industry) > 0 and promising_industry[0] != "":
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
        norm_grade = determine_news_grade(r.impact_score or 0) if r.impact_score is not None else (r.news_grade or "E")
        data.append({
            "id": r.id,
            "source_name": r.source_name,
            "source_type": r.source_type or "private_media",
            "ministry_name": r.ministry_name,
            "title": r.title,
            "link": r.link,
            "pub_date": r.pub_date.strftime("%Y-%m-%d") if isinstance(r.pub_date, datetime.datetime) else str(r.pub_date or ""),
            "summary": r.summary,
            "matched_industry": r.matched_industry,
            "matched_signal": r.matched_signal,
            "matched_financial": r.matched_financial,
            "country": r.country,
            "deal_stage": r.deal_stage,
            "impact_score": r.impact_score,
            "news_grade": norm_grade,
            "promising_industry": r.promising_industry,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
        })
    return {
        "status": "success",
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total_count / page_size) if total_count > 0 else 1,
        "data": data,
    }


@app.post("/api/sync_public_news")
def sync_public_news_now():
    """정부부처(중기부·과기부·금융위·산업부·특허청) 공식 정책브리핑 기사를 즉시 수집 및 저장"""
    engine = init_db()
    session = get_session(engine)
    try:
        gov_items = collect_public_gov_news(limit_per_ministry=12)
        added = 0
        for art in gov_items:
            if session.query(DealArticle).filter_by(link=art["link"]).first():
                continue
            classified = industry_manager.classify_text(f"{art['title']} {art.get('summary', '')}")
            new_row = DealArticle(
                source_name=art["source_name"],
                source_type="public_gov",
                ministry_name=art.get("ministry_name"),
                title=art["title"],
                link=art["link"],
                pub_date=art.get("pub_date") or datetime.datetime.now(),
                summary=art.get("summary", "")[:400],
                country="한국",
                deal_stage="Deal Sourcing",
                impact_score=76.0,
                news_grade="B",
                promising_industry=classified.get("formatted", "기타 > 정책/제도 > 벤처정책"),
                compressed_summary=art.get("summary", "")[:400],
            )
            session.add(new_row)
            added += 1
        session.commit()
        return {"status": "success", "added": added, "total_fetched": len(gov_items)}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


@app.get("/api/statistics")
def get_statistics():
    engine = init_db()
    session = get_session(engine)
    now = datetime.datetime.now()

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - datetime.timedelta(days=1)
    yesterday_end = today_start
    week_start = today_start - datetime.timedelta(days=7)
    month_start = today_start - datetime.timedelta(days=30)

    periods = {
        "today": (today_start, None),
        "yesterday": (yesterday_start, yesterday_end),
        "1week": (week_start, None),
        "1month": (month_start, None),
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
        public_gov_count = 0
        total_impact = 0.0

        for art in articles:
            c = art.country or "기타"
            country_counts[c] = country_counts.get(c, 0) + 1
            s = art.deal_stage or "기타"
            stage_counts[s] = stage_counts.get(s, 0) + 1
            g = art.news_grade or "기타"
            grade_counts[g] = grade_counts.get(g, 0) + 1
            if art.source_type == "public_gov":
                public_gov_count += 1
            total_impact += art.impact_score if art.impact_score else 0.0

        avg_impact = round(total_impact / total, 1) if total > 0 else 0.0
        stats_data[period_name] = {
            "total_count": total,
            "public_gov_count": public_gov_count,
            "avg_impact": avg_impact,
            "countries": country_counts,
            "stages": stage_counts,
            "grades": grade_counts,
        }

    session.close()
    return {"status": "success", "data": stats_data}


# =========================================================================
# 2. THE VC 스타일 통합 오버뷰 & 통합검색 API
# =========================================================================
def _calc_dday(end_date_str: str) -> str:
    if not end_date_str:
        return "상시"
    try:
        dt = datetime.datetime.strptime(end_date_str[:10], "%Y-%m-%d").date()
        diff = (dt - datetime.date.today()).days
        if diff < 0:
            return "마감"
        elif diff == 0:
            return "D-Day"
        return f"D-{diff}"
    except Exception:
        return end_date_str


@app.get("/api/overview_summary")
def get_overview_summary():
    """통합 오버뷰 화면용 요약 지표 및 각 도메인 최신 프리뷰 반환"""
    engine = init_db()
    session = get_session(engine)
    try:
        ensure_venture_policy_stats(session)

        # 초기 진입 시 펀드 또는 지원사업이 비어 있으면 가볍게 1회 자동 수집 시도
        if session.query(VentureFund).count() == 0:
            try:
                sync_diva_funds_to_db(session, pages=1)
            except Exception:
                pass
        if session.query(GovGrantNotice).count() == 0:
            try:
                sync_grants_to_db(session, pages=1)
            except Exception:
                pass

        article_cnt = session.query(DealArticle).count()
        gov_news_cnt = session.query(DealArticle).filter(DealArticle.source_type == "public_gov").count()
        company_cnt = session.query(CompanyProfile).count()
        fund_cnt = session.query(VentureFund).count()
        grant_cnt = session.query(GovGrantNotice).count()
        patent_cnt = session.query(CompanyPatent).count()

        recent_articles = session.query(DealArticle).order_by(desc(DealArticle.created_at)).limit(6).all()
        recent_funds = session.query(VentureFund).order_by(desc(VentureFund.reg_date), desc(VentureFund.id)).limit(5).all()
        recent_companies = session.query(CompanyProfile).order_by(desc(CompanyProfile.updated_at)).limit(6).all()
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        active_grants = (
            session.query(GovGrantNotice)
            .filter(or_(GovGrantNotice.end_date >= today_str, GovGrantNotice.end_date == ""))
            .order_by(GovGrantNotice.end_date.asc())
            .limit(5)
            .all()
        )
        latest_scale = (
            session.query(VenturePolicyStat)
            .filter_by(category="funding_scale")
            .order_by(desc(VenturePolicyStat.period_label))
            .first()
        )

        return {
            "status": "success",
            "counts": {
                "articles": article_cnt,
                "public_gov_articles": gov_news_cnt,
                "companies": company_cnt,
                "funds": fund_cnt,
                "grants": grant_cnt,
                "patents": patent_cnt,
            },
            "latest_venture_scale": {
                "period": latest_scale.period_label if latest_scale else "2025년 연간",
                "new_investment_trillion": round((latest_scale.new_investment_krw or 0) / 10000.0, 2) if latest_scale else 12.68,
                "new_fund_trillion": round((latest_scale.new_fund_formation_krw or 0) / 10000.0, 2) if latest_scale else 11.85,
                "yoy_growth_pct": latest_scale.yoy_growth_pct if latest_scale else 6.1,
            },
            "recent_articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "link": a.link,
                    "source_name": a.source_name,
                    "source_type": a.source_type or "private_media",
                    "ministry_name": a.ministry_name,
                    "news_grade": determine_news_grade(a.impact_score or 0) if a.impact_score else (a.news_grade or "C"),
                    "country": a.country,
                    "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "",
                }
                for a in recent_articles
            ],
            "recent_funds": [
                {
                    "id": f.id,
                    "fund_name": f.fund_name,
                    "gp_name": f.gp_name,
                    "reg_date": f.reg_date,
                    "maturity_date": f.maturity_date,
                    "commitment_krw": f.commitment_krw,
                    "invest_field": f.invest_field,
                    "motae_backed": f.motae_backed,
                }
                for f in recent_funds
            ],
            "recent_companies": [
                {
                    "id": c.id,
                    "corp_name": c.corp_name,
                    "corp_cls": c.corp_cls,
                    "ceo_name": c.ceo_name,
                    "revenue_krw": c.revenue_krw,
                    "op_profit_krw": c.op_profit_krw,
                    "credit_grade": c.credit_grade,
                    "latest_bsns_year": c.latest_bsns_year,
                }
                for c in recent_companies
            ],
            "active_grants": [
                {
                    "id": g.id,
                    "category": g.category,
                    "title": g.title,
                    "ministry": g.ministry,
                    "executor": g.executor,
                    "end_date": g.end_date,
                    "d_day": _calc_dday(g.end_date),
                    "detail_url": g.detail_url,
                }
                for g in active_grants
            ],
        }
    finally:
        session.close()


@app.get("/api/integrated_search")
def integrated_search(q: str = Query("")):
    """단일 키워드로 기업(DB+DART후보), 펀드, 뉴스(민간+공공), 지원사업, 특허, 벤처정책 통합 검색"""
    kw_raw = (q or "").strip()
    if not kw_raw:
        return {"status": "error", "message": "검색어를 입력해주세요."}

    engine = init_db()
    session = get_session(engine)
    like_kw = f"%{kw_raw}%"
    try:
        db_companies = (
            session.query(CompanyProfile)
            .filter(or_(CompanyProfile.corp_name.like(like_kw), CompanyProfile.ceo_name.like(like_kw), CompanyProfile.biz_reg_no.like(like_kw)))
            .limit(10)
            .all()
        )
        dart_candidates = []
        try:
            dart_candidates = search_dart_candidates(kw_raw, limit=8)
        except Exception:
            pass

        funds = (
            session.query(VentureFund)
            .filter(or_(VentureFund.fund_name.like(like_kw), VentureFund.gp_name.like(like_kw), VentureFund.invest_field.like(like_kw)))
            .order_by(desc(VentureFund.reg_date))
            .limit(10)
            .all()
        )
        articles = (
            session.query(DealArticle)
            .filter(or_(DealArticle.title.like(like_kw), DealArticle.summary.like(like_kw), DealArticle.promising_industry.like(like_kw)))
            .order_by(desc(DealArticle.created_at))
            .limit(10)
            .all()
        )
        grants = (
            session.query(GovGrantNotice)
            .filter(or_(GovGrantNotice.title.like(like_kw), GovGrantNotice.category.like(like_kw), GovGrantNotice.ministry.like(like_kw)))
            .order_by(GovGrantNotice.end_date.asc())
            .limit(10)
            .all()
        )
        patents = (
            session.query(CompanyPatent)
            .filter(or_(CompanyPatent.applicant_name.like(like_kw), CompanyPatent.invention_title.like(like_kw)))
            .order_by(desc(CompanyPatent.application_date))
            .limit(10)
            .all()
        )

        return {
            "status": "success",
            "query": kw_raw,
            "companies": [
                {
                    "id": c.id,
                    "corp_name": c.corp_name,
                    "corp_code": c.corp_code,
                    "corp_cls": c.corp_cls,
                    "ceo_name": c.ceo_name,
                    "revenue_krw": c.revenue_krw,
                    "op_profit_krw": c.op_profit_krw,
                    "credit_grade": c.credit_grade,
                    "latest_bsns_year": c.latest_bsns_year,
                }
                for c in db_companies
            ],
            "dart_candidates": dart_candidates,
            "funds": [
                {
                    "id": f.id,
                    "fund_name": f.fund_name,
                    "gp_name": f.gp_name,
                    "reg_date": f.reg_date,
                    "commitment_krw": f.commitment_krw,
                    "invest_field": f.invest_field,
                    "motae_backed": f.motae_backed,
                }
                for f in funds
            ],
            "articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "link": a.link,
                    "source_name": a.source_name,
                    "source_type": a.source_type or "private_media",
                    "created_at": a.created_at.strftime("%Y-%m-%d") if a.created_at else "",
                }
                for a in articles
            ],
            "grants": [
                {
                    "id": g.id,
                    "category": g.category,
                    "title": g.title,
                    "ministry": g.ministry,
                    "end_date": g.end_date,
                    "d_day": _calc_dday(g.end_date),
                    "detail_url": g.detail_url,
                }
                for g in grants
            ],
            "patents": [
                {
                    "id": p.id,
                    "applicant_name": p.applicant_name,
                    "invention_title": p.invention_title,
                    "application_date": p.application_date,
                    "registration_status": p.registration_status,
                }
                for p in patents
            ],
        }
    finally:
        session.close()


# =========================================================================
# 3. 기업·재무 DB (DART + 금융위 + NICE 리포트 업로드) API
# =========================================================================
def _serialize_company(c: CompanyProfile):
    fin_list = []
    if c.financial_history_json:
        try:
            fin_list = json.loads(c.financial_history_json)
        except Exception:
            fin_list = []
    return {
        "id": c.id,
        "corp_name": c.corp_name,
        "corp_code": c.corp_code,
        "biz_reg_no": c.biz_reg_no,
        "corp_reg_no": c.corp_reg_no,
        "stock_code": c.stock_code,
        "corp_cls": c.corp_cls,
        "ceo_name": c.ceo_name,
        "est_dt": c.est_dt,
        "industry_code": c.industry_code,
        "address": c.address,
        "homepage_url": c.homepage_url,
        "venture_cert_type": c.venture_cert_type,
        "employee_count": c.employee_count,
        "avg_salary_est_krw": c.avg_salary_est_krw,
        "credit_grade": c.credit_grade,
        "latest_bsns_year": c.latest_bsns_year,
        "revenue_krw": c.revenue_krw,
        "op_profit_krw": c.op_profit_krw,
        "net_income_krw": c.net_income_krw,
        "total_assets_krw": c.total_assets_krw,
        "total_liab_krw": c.total_liab_krw,
        "total_equity_krw": c.total_equity_krw,
        "capital_increase_summary": c.capital_increase_summary,
        "financial_history": fin_list,
        "data_source": c.data_source,
        "notes": c.notes,
        "updated_at": c.updated_at.strftime("%Y-%m-%d %H:%M") if c.updated_at else None,
    }


def _upsert_company_dict(session, data: dict) -> CompanyProfile:
    existing = None
    if data.get("corp_code"):
        existing = session.query(CompanyProfile).filter_by(corp_code=data["corp_code"]).first()
    if not existing and data.get("corp_name"):
        existing = session.query(CompanyProfile).filter_by(corp_name=data["corp_name"]).first()

    if existing:
        for k, v in data.items():
            if v is not None and v != "":
                setattr(existing, k, v)
        session.commit()
        session.refresh(existing)
        return existing
    else:
        row = CompanyProfile(**data)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


@app.get("/api/companies")
def list_companies(q: str = Query(""), corp_cls: str = Query("")):
    engine = init_db()
    session = get_session(engine)
    try:
        query = session.query(CompanyProfile)
        if q.strip():
            lk = f"%{q.strip()}%"
            query = query.filter(or_(CompanyProfile.corp_name.like(lk), CompanyProfile.ceo_name.like(lk), CompanyProfile.biz_reg_no.like(lk)))
        if corp_cls.strip():
            query = query.filter(CompanyProfile.corp_cls.like(f"%{corp_cls.strip()}%"))
        rows = query.order_by(desc(CompanyProfile.updated_at), desc(CompanyProfile.id)).limit(100).all()
        return {"status": "success", "count": len(rows), "data": [_serialize_company(r) for r in rows]}
    finally:
        session.close()


@app.get("/api/companies/dart_search")
def dart_search_companies(q: str = Query("")):
    try:
        candidates = search_dart_candidates(q, limit=15)
        return {"status": "success", "data": candidates}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/companies/fetch_dart")
def fetch_and_save_dart_company(req: DartFetchRequest):
    engine = init_db()
    session = get_session(engine)
    try:
        corp_code = (req.corp_code or "").strip()
        if not corp_code and req.company_name:
            cands = search_dart_candidates(req.company_name, limit=1)
            if not cands:
                return {"status": "error", "message": f"DART에서 '{req.company_name}' 법인을 찾을 수 없습니다. (비외감 초기 스타트업은 NICE/재무 리포트 업로드를 이용해 주세요.)"}
            corp_code = cands[0]["corp_code"]

        detail = fetch_dart_company_detail(corp_code)
        if not detail:
            return {"status": "error", "message": "DART 기업개황 조회에 실패했습니다. API 키 또는 법인코드를 확인해주세요."}

        saved = _upsert_company_dict(session, detail)
        return {"status": "success", "data": _serialize_company(saved)}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


@app.post("/api/companies/sync_featured")
def sync_featured_venture_companies():
    """대표 국내 유니콘·AI·바이오·로보틱스 기업의 실시간 DART 개황 및 3개년 재무 일괄 동기화"""
    featured_names = ["비바리퍼블리카", "컬리", "무신사", "야놀자", "루닛", "레인보우로보틱스", "리벨리온", "퓨리오사AI"]
    engine = init_db()
    session = get_session(engine)
    synced = []
    try:
        for name in featured_names:
            cands = search_dart_candidates(name, limit=1)
            if not cands:
                continue
            detail = fetch_dart_company_detail(cands[0]["corp_code"])
            if detail:
                saved = _upsert_company_dict(session, detail)
                synced.append(saved.corp_name)
        return {"status": "success", "synced_count": len(synced), "companies": synced}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


@app.post("/api/companies/upload_report")
async def upload_company_report(
    company_name: str = Form(""),
    file: UploadFile = File(...),
):
    engine = init_db()
    session = get_session(engine)
    try:
        file_bytes = await file.read()
        records = parse_uploaded_company_report(file.filename, file_bytes, fallback_name=company_name)
        if not records:
            return {"status": "error", "message": "파일에서 기업 정보를 추출할 수 없습니다. 기업명을 함께 입력하거나 CSV 컬럼(기업명, 대표자, 신용등급, 매출액 등)을 확인해주세요."}
        saved_list = []
        for rec in records:
            saved = _upsert_company_dict(session, rec)
            saved_list.append(_serialize_company(saved))
        return {"status": "success", "count": len(saved_list), "data": saved_list}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


# =========================================================================
# 4. 벤처펀드 결성·GP 현황 (DIVA 전자공시) API
# =========================================================================
@app.get("/api/funds")
def get_venture_funds(
    q: str = Query(""),
    gp: str = Query(""),
    invest_field: str = Query(""),
    motae_only: bool = Query(False),
    page: int = Query(1),
    page_size: int = Query(25),
):
    engine = init_db()
    session = get_session(engine)
    try:
        if session.query(VentureFund).count() == 0:
            try:
                sync_diva_funds_to_db(session, pages=2)
            except Exception as se:
                print(f"Initial DIVA sync warning: {se}")

        query = session.query(VentureFund)
        if q.strip():
            lk = f"%{q.strip()}%"
            query = query.filter(or_(VentureFund.fund_name.like(lk), VentureFund.gp_name.like(lk), VentureFund.support_type.like(lk)))
        if gp.strip():
            query = query.filter(VentureFund.gp_name.like(f"%{gp.strip()}%"))
        if invest_field.strip():
            query = query.filter(VentureFund.invest_field.like(f"%{invest_field.strip()}%"))
        if motae_only:
            query = query.filter(VentureFund.motae_backed.is_(True))

        query = query.order_by(desc(VentureFund.reg_date), desc(VentureFund.id))
        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()

        # 총 약정액 합계 계산
        all_commitments = [r.commitment_krw or 0.0 for r in query.limit(500).all()]
        sum_eok = round(sum(all_commitments), 1)

        return {
            "status": "success",
            "count": total,
            "sum_commitment_krw": sum_eok,
            "page": page,
            "total_pages": math.ceil(total / page_size) if total > 0 else 1,
            "data": [
                {
                    "id": r.id,
                    "asct_id": r.asct_id,
                    "fund_name": r.fund_name,
                    "gp_name": r.gp_name,
                    "reg_date": r.reg_date,
                    "maturity_date": r.maturity_date,
                    "commitment_krw": r.commitment_krw,
                    "invest_field": r.invest_field,
                    "purpose_type": r.purpose_type,
                    "support_type": r.support_type,
                    "motae_backed": r.motae_backed,
                    "source_name": r.source_name,
                    "source_url": r.source_url,
                }
                for r in rows
            ],
        }
    finally:
        session.close()


@app.post("/api/funds/sync")
def sync_venture_funds(req: FundSyncRequest):
    engine = init_db()
    session = get_session(engine)
    try:
        res = sync_diva_funds_to_db(session, pages=max(1, min(req.pages, 5)), gp_keyword=req.gp_keyword, fund_keyword=req.fund_keyword)
        return {"status": "success", **res}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


# =========================================================================
# 5. 중기부 벤처산업 펀딩규모 · 모태펀드 방향 · 동적 법령/세제 레지스트리 API
# =========================================================================
@app.get("/api/venture_policy")
def get_venture_policy_hub():
    engine = init_db()
    session = get_session(engine)
    try:
        ensure_venture_policy_stats(session)
        stats_rows = session.query(VenturePolicyStat).order_by(VenturePolicyStat.period_label.asc()).all()

        scale_series = []
        motae_directions = []
        live_trends = []

        for s in stats_rows:
            sector_dict = json.loads(s.sector_share_json) if s.sector_share_json else {}
            stage_dict = json.loads(s.stage_share_json) if s.stage_share_json else {}
            item = {
                "id": s.id,
                "stat_key": s.stat_key,
                "period_label": s.period_label,
                "category": s.category,
                "new_investment_krw": s.new_investment_krw,
                "new_fund_formation_krw": s.new_fund_formation_krw,
                "motae_budget_krw": s.motae_budget_krw,
                "yoy_growth_pct": s.yoy_growth_pct,
                "sector_share": sector_dict,
                "stage_share": stage_dict,
                "title": s.title,
                "summary": s.summary,
                "ministry": s.ministry,
                "source_url": s.source_url,
                "published_date": s.published_date,
            }
            if s.category == "funding_scale":
                scale_series.append(item)
            elif s.category == "motae_direction":
                motae_directions.append(item)
            else:
                live_trends.append(item)

        live_trends.sort(key=lambda x: x.get("published_date") or "", reverse=True)
        registry = get_dynamic_legal_tax_registry(session)

        return {
            "status": "success",
            "scale_series": scale_series,
            "motae_directions": motae_directions,
            "live_trends": live_trends[:20],
            "legal_tax_registry": registry,
        }
    finally:
        session.close()


@app.post("/api/venture_policy/sync")
def sync_venture_policy():
    engine = init_db()
    session = get_session(engine)
    try:
        ensure_venture_policy_stats(session)
        added = sync_live_policy_briefings(session, limit=12)
        return {"status": "success", "added": added}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


@app.get("/api/config_registry")
def get_config_registry(group: Optional[str] = Query(None)):
    engine = init_db()
    session = get_session(engine)
    try:
        return {"status": "success", "data": get_dynamic_legal_tax_registry(session, group=group)}
    finally:
        session.close()


@app.put("/api/config_registry/{config_key}")
def update_config_registry_item(config_key: str, req: ConfigUpdateRequest):
    engine = init_db()
    session = get_session(engine)
    try:
        row = session.query(DynamicConfigRegistry).filter_by(config_key=config_key).first()
        if not row:
            return {"status": "error", "message": "해당 설정 키를 찾을 수 없습니다."}
        row.config_value = req.config_value
        if req.effective_date is not None:
            row.effective_date = req.effective_date
        if req.legal_basis is not None:
            row.legal_basis = req.legal_basis
        if req.description is not None:
            row.description = req.description
        session.commit()
        return {"status": "success", "message": "동적 설정 레지스트리가 업데이트되었습니다."}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


# =========================================================================
# 6. 정부 지원사업 · 국가 R&D · 특허(IP) API
# =========================================================================
@app.get("/api/grants")
def get_gov_grants(
    q: str = Query(""),
    category: str = Query(""),
    active_only: bool = Query(True),
    page: int = Query(1),
    page_size: int = Query(25),
):
    engine = init_db()
    session = get_session(engine)
    try:
        if session.query(GovGrantNotice).count() == 0:
            try:
                sync_grants_to_db(session, pages=2)
            except Exception:
                pass

        query = session.query(GovGrantNotice)
        if q.strip():
            lk = f"%{q.strip()}%"
            query = query.filter(or_(GovGrantNotice.title.like(lk), GovGrantNotice.ministry.like(lk), GovGrantNotice.executor.like(lk)))
        if category.strip():
            query = query.filter(GovGrantNotice.category.like(f"%{category.strip()}%"))
        if active_only:
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            query = query.filter(or_(GovGrantNotice.end_date >= today_str, GovGrantNotice.end_date == ""))

        query = query.order_by(GovGrantNotice.end_date.asc(), desc(GovGrantNotice.id))
        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "status": "success",
            "count": total,
            "page": page,
            "total_pages": math.ceil(total / page_size) if total > 0 else 1,
            "data": [
                {
                    "id": g.id,
                    "notice_uid": g.notice_uid,
                    "category": g.category,
                    "title": g.title,
                    "ministry": g.ministry,
                    "executor": g.executor,
                    "apply_period": g.apply_period,
                    "end_date": g.end_date,
                    "d_day": _calc_dday(g.end_date),
                    "reg_date": g.reg_date,
                    "detail_url": g.detail_url,
                    "source_name": g.source_name,
                }
                for g in rows
            ],
        }
    finally:
        session.close()


@app.post("/api/grants/sync")
def sync_gov_grants(pages: int = Query(2)):
    engine = init_db()
    session = get_session(engine)
    try:
        res = sync_grants_to_db(session, pages=max(1, min(pages, 5)))
        return {"status": "success", **res}
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


@app.get("/api/patents")
def list_patents(q: str = Query("")):
    engine = init_db()
    session = get_session(engine)
    try:
        query = session.query(CompanyPatent)
        if q.strip():
            lk = f"%{q.strip()}%"
            query = query.filter(or_(CompanyPatent.applicant_name.like(lk), CompanyPatent.invention_title.like(lk)))
        rows = query.order_by(desc(CompanyPatent.application_date), desc(CompanyPatent.id)).limit(100).all()
        return {
            "status": "success",
            "count": len(rows),
            "data": [
                {
                    "id": p.id,
                    "applicant_name": p.applicant_name,
                    "application_number": p.application_number,
                    "invention_title": p.invention_title,
                    "ipc_code": p.ipc_code,
                    "application_date": p.application_date,
                    "registration_number": p.registration_number,
                    "registration_status": p.registration_status,
                    "abstract_text": p.abstract_text,
                    "source_name": p.source_name,
                }
                for p in rows
            ],
        }
    finally:
        session.close()


@app.post("/api/patents/search")
def search_and_save_patents(req: PatentSearchRequest):
    engine = init_db()
    session = get_session(engine)
    try:
        res = search_company_patents(req.company_name, max_rows=req.max_rows)
        added = 0
        for it in res.get("items", []):
            if not it.get("application_number"):
                continue
            exists = session.query(CompanyPatent).filter_by(application_number=it["application_number"]).first()
            if not exists:
                session.add(CompanyPatent(**it))
                added += 1
        session.commit()

        saved_rows = (
            session.query(CompanyPatent)
            .filter(CompanyPatent.applicant_name.like(f"%{req.company_name.strip()}%"))
            .order_by(desc(CompanyPatent.application_date))
            .limit(30)
            .all()
        )
        # Fallback to returned items if assignee string differs slightly (e.g. English vs Korean)
        out_items = [
            {
                "id": p.id,
                "applicant_name": p.applicant_name,
                "application_number": p.application_number,
                "invention_title": p.invention_title,
                "ipc_code": p.ipc_code,
                "application_date": p.application_date,
                "registration_number": p.registration_number,
                "registration_status": p.registration_status,
                "abstract_text": p.abstract_text,
                "source_name": p.source_name,
            }
            for p in saved_rows
        ] or res.get("items", [])

        return {
            "status": "success",
            "source": res.get("source"),
            "kipris_active": res.get("kipris_active"),
            "added": added,
            "data": out_items,
        }
    except Exception as e:
        session.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        session.close()


# =========================================================================
# 7. 기존 파이프라인, 도메인/키워드, 리포트, 밸류에이션 & 고도화된 IC Memo API
# =========================================================================
crawl_result = {}
is_crawling = False
crawl_progress = {"status": "idle", "message": "", "current": 0, "total": 0, "percent": 0}


def run_pipeline_task(days_limit: int, max_articles: int = 50):
    global is_crawling, crawl_result, crawl_progress
    if is_crawling:
        return
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
                "percent": int((current / total) * 100) if total > 0 else 0,
            }

        crawl_progress["message"] = "글로벌 뉴스 RSS · 공공부처 브리핑 · 네이버 뉴스를 수집하는 중..."
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

    data = [
        {
            "id": r.id,
            "name": r.name,
            "url": r.url,
            "rss_url": r.rss_url,
            "purpose": r.purpose,
            "country": r.country,
            "category": r.category,
            "is_active": r.is_active,
            "is_builtin": False,
        }
        for r in results
    ]

    builtin_domains = [
        {"id": "builtin_korea_kr", "name": "대한민국 정책브리핑 (중기부/과기부/금융위/산업부)", "url": "https://www.korea.kr", "rss_url": None, "purpose": "정부부처 벤처·모태펀드·R&D 공식 정책브리핑", "country": "한국", "category": "정부/정책", "is_active": True, "is_builtin": True},
        {"id": "builtin_diva", "name": "DIVA 전자공시 (한국벤처캐피탈협회)", "url": "http://diva.kvca.or.kr", "rss_url": None, "purpose": "벤처투자조합 신규 결성 및 GP 운용 공시", "country": "한국", "category": "협회/기관", "is_active": True, "is_builtin": True},
        {"id": "builtin_bizinfo", "name": "기업마당 / K-Startup (중소벤처기업부)", "url": "https://www.bizinfo.go.kr", "rss_url": None, "purpose": "창업·기술개발(R&D)·정책자금 지원사업 공고", "country": "한국", "category": "정부/정책", "is_active": True, "is_builtin": True},
        {"id": "builtin_dart", "name": "DART 전자공시시스템 (금융감독원)", "url": "https://opendart.fss.or.kr", "rss_url": None, "purpose": "상장·외감 비상장사 기업개황·3개년 재무·유상증자(RCPS)", "country": "한국", "category": "기업 DB", "is_active": True, "is_builtin": True},
        {"id": "builtin_naver", "name": "Naver News", "url": "https://news.naver.com", "rss_url": None, "purpose": "한국 벤처/스타트업/경제 뉴스", "country": "한국", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_kr", "name": "Google News (KR)", "url": "https://news.google.com/?hl=ko&gl=KR", "rss_url": "https://news.google.com/rss", "purpose": "한국 IT/스타트업", "country": "한국", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_us", "name": "Google News (US)", "url": "https://news.google.com/?hl=en-US&gl=US", "rss_url": "https://news.google.com/rss", "purpose": "미국 IT/스타트업", "country": "미국", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_jp", "name": "Google News (JP)", "url": "https://news.google.com/?hl=ja&gl=JP", "rss_url": "https://news.google.com/rss", "purpose": "일본 IT/스타트업", "country": "일본", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_cn", "name": "Google News (CN)", "url": "https://news.google.com/?hl=zh-CN&gl=CN", "rss_url": "https://news.google.com/rss", "purpose": "중국 IT/스타트업", "country": "중국", "category": "news", "is_active": True, "is_builtin": True},
        {"id": "builtin_google_eu", "name": "Google News (EU)", "url": "https://news.google.com/?hl=en-GB&gl=GB", "rss_url": "https://news.google.com/rss", "purpose": "유럽 IT/스타트업", "country": "유럽", "category": "news", "is_active": True, "is_builtin": True},
    ]
    data.extend(builtin_domains)
    return {"status": "success", "data": data}


@app.post("/api/domains")
def create_domain(domain: DomainCreate):
    engine = init_db()
    session = get_session(engine)
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


@app.get("/api/industries")
def get_industries():
    return {
        "status": "success",
        "hierarchy": industry_manager.get_hierarchy(),
        "all_rows": industry_manager.get_all_rows(),
    }


@app.get("/api/keywords")
def get_keywords():
    engine = init_db()
    session = get_session(engine)
    results = session.query(SearchKeyword).all()
    session.close()

    data = [{"id": r.id, "keyword": r.keyword, "type": r.type, "category": r.category, "is_active": r.is_active, "is_builtin": False} for r in results]

    try:
        config_path = os.path.join(ROOT_DIR, "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        for cat, langs in config.get("keywords", {}).items():
            for kw in langs.get("ko", []):
                if not any(d["keyword"] == kw for d in data):
                    data.append({
                        "id": f"builtin_{cat}_{kw}",
                        "keyword": kw,
                        "type": "기존 (내장)",
                        "category": cat,
                        "is_active": True,
                        "is_builtin": True,
                    })
    except Exception as e:
        print("YAML Load Error:", e)

    for item in data:
        kw = item.get("keyword", "")
        classification = industry_manager.classify_keyword(kw)
        item["major"] = classification.get("major", "기타")
        item["middle"] = classification.get("middle", "기타/미정")
        item["minor"] = classification.get("minor", "기타")
        item["formatted_industry"] = classification.get("formatted", "기타 > 기타/미정 > 기타")

    return {"status": "success", "data": data}


@app.post("/api/keywords")
def create_keyword(kw: KeywordCreate):
    engine = init_db()
    session = get_session(engine)
    existing = session.query(SearchKeyword).filter_by(keyword=kw.keyword).first()
    if existing:
        session.close()
        return {"status": "error", "message": "이미 존재하는 키워드입니다."}
    classification = industry_manager.classify_keyword(kw.keyword)
    major_cat = classification.get("major", "기타")
    new_kw = SearchKeyword(keyword=kw.keyword, type=kw.type, category=major_cat)
    try:
        session.add(new_kw)
        session.commit()
    except Exception as e:
        session.rollback()
        session.close()
        return {"status": "error", "message": str(e)}
    session.close()
    return {"status": "success", "message": "Keyword added", "classification": classification}


@app.delete("/api/keywords/{keyword_id}")
def delete_keyword(keyword_id: str):
    engine = init_db()
    session = get_session(engine)
    if keyword_id.startswith("builtin_"):
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
        from processor.report_generator import generate_daily_report
        report_text = generate_daily_report()
        if not report_text:
            return {"status": "success", "report": "최근 24시간 내 수집된 기사가 없어 리포트를 생성할 수 없습니다. 데이터를 먼저 수집해주세요."}
        return {"status": "success", "report": report_text}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.post("/api/analyze_url")
def analyze_custom_url(req: AnalyzeUrlRequest):
    engine = init_db()
    session = get_session(engine)
    try:
        title = ""
        try:
            from newspaper import Article
            article = Article(req.url, language="ko")
            article.download()
            article.parse()
            title = article.title
        except Exception:
            import requests
            from bs4 import BeautifulSoup
            resp = requests.get(req.url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else req.url

        result = analyze_text(title, "", req.url, pub_date=datetime.datetime.now())
        if not result:
            session.close()
            return {"status": "error", "message": "유효한 벤처/스타트업/경제 키워드가 매칭되지 않았습니다."}

        new_article = DealArticle(
            source_name="Manual",
            source_type="private_media",
            title=title,
            link=req.url,
            pub_date=datetime.datetime.now(),
            summary=result.get("compressed_summary", "")[:200],
            matched_industry=result.get("matched_industry"),
            matched_signal=result.get("matched_signal"),
            matched_financial=result.get("matched_financial"),
            country=result.get("country"),
            deal_stage=result.get("deal_stage"),
            impact_score=result.get("impact_score"),
            news_grade=result.get("news_grade"),
            promising_industry=result.get("promising_industry"),
            compressed_summary=result.get("compressed_summary"),
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

    env_path = os.path.join(ROOT_DIR, ".env")
    load_dotenv(dotenv_path=env_path, override=True)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"status": "error", "message": "API 키가 설정되지 않았습니다 (.env 파일 확인)."}

    engine = init_db()
    session = get_session(engine)
    db_articles = session.query(DealArticle).filter(DealArticle.link.in_(req.urls)).all()
    url_to_summary = {article.link: article.compressed_summary or article.summary for article in db_articles}
    session.close()

    async def get_content(url):
        if url in url_to_summary and url_to_summary[url]:
            return url_to_summary[url]
        try:
            return await fetch_url_content(url)
        except Exception as e:
            return f"수집 실패: {e}"

    sem = asyncio.Semaphore(10)

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

    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    num_articles = len(urls_to_process)

    if num_articles >= 5:
        prompt = f"""
당신은 글로벌 탑티어 벤처캐피탈(VC)의 수석 파트너이자 최고 산업 분석가(Chief Analyst)입니다.
수집된 {num_articles}개의 뉴스 기사와 관련 기업/산업 정보 원문을 종합 분석하여, 투자심의위원회에 즉시 제출할 수 있는 **최소 5페이지(5개 이상의 대형 챕터) 이상의 전문 심층분석 보고서(Deep-Dive Investment & Industry Report)**를 작성해 주세요.

[기준 일자]
- 리포트 작성일: {today_str}

[분석 대상 기사 원문 데이터 ({num_articles}건)]
{articles_content}

[보고서 구성 필수 목차 구조]
# 📄 [글로벌 VC 심층 분석] 기술 산업 동향 및 핵심 기업 투자 분석 보고서
*작성일자: {today_str} | 수집 딜 기사: 총 {num_articles}건*
## 1페이지: Executive Summary & 글로벌 산업 메가 트렌드 (서론)
## 2페이지: 주요 섹터별 기술 체계 및 세부 산업 동향 (본론 I)
## 3페이지: 타겟 기업 심층 분석 및 비즈니스 모델 (본론 II - 기업명(국가) 표 필수 포함)
## 4페이지: 주요 딜(Deal) 스펙트럼 & 시장 영향력 평가 (본론 III)
## 5페이지: VC 투자 인사이트, 밸류에이션 & 리스크 평가 (결론)
## 🔗 6페이지: 참조 기사 원문 및 출처 모음
"""
    else:
        prompt = f"""
당신은 최고의 벤처캐피탈(VC) 시니어 애널리스트입니다.
아래 제공된 {num_articles}개의 뉴스 기사를 분석하여, 투자 심사역을 위한 **A4 보고서 형식의 전문 분석 리포트**를 작성해 주세요.
- 기준 일자: {today_str}
- 모든 기업명 뒤에 소속 국가를 명시하고 마크다운 표를 활용하세요.

[분석할 기사 원문 데이터]
{articles_content}
"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-flash-lite-latest")
        response = model.generate_content(prompt)
        return {"status": "success", "report": response.text.strip()}
    except Exception:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return {"status": "success", "report": response.text.strip()}
        except Exception as ex:
            return {"status": "error", "message": str(ex)}


@app.get("/api/api_keys_status")
def get_api_keys_status():
    env_path = os.path.join(ROOT_DIR, ".env")
    load_dotenv(dotenv_path=env_path, override=True)

    def _mask(k):
        val = (os.getenv(k) or "").strip()
        if not val:
            return {"configured": False, "masked": "미설정"}
        return {"configured": True, "masked": f"{val[:4]}...{val[-4:]} ({len(val)}자)"}

    return {
        "status": "success",
        "keys": {
            "GEMINI_API_KEY": _mask("GEMINI_API_KEY"),
            "DART_API_KEY": _mask("DART_API_KEY"),
            "DATA_GO_KR_SERVICE_KEY": _mask("DATA_GO_KR_SERVICE_KEY"),
            "KIPRIS_API_KEY": _mask("KIPRIS_API_KEY"),
            "NICE_API_KEY": _mask("NICE_API_KEY"),
        },
    }


@app.post("/api/update_api_key")
def update_api_key(req: ApiKeyRequest):
    try:
        env_path = os.path.join(ROOT_DIR, ".env")
        kv = {}
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        kv[k.strip()] = v.strip()

        updates = {
            "GEMINI_API_KEY": req.gemini_api_key or req.api_key,
            "DART_API_KEY": req.dart_api_key,
            "DATA_GO_KR_SERVICE_KEY": req.data_go_kr_service_key,
            "KIPRIS_API_KEY": req.kipris_api_key,
            "NICE_API_KEY": req.nice_api_key,
        }
        updated_names = []
        for env_name, val in updates.items():
            if val is not None and val.strip() != "":
                kv[env_name] = val.strip()
                os.environ[env_name] = val.strip()
                updated_names.append(env_name)

        with open(env_path, "w", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")

        return {"status": "success", "message": f"인증키({', '.join(updated_names) or '변경 없음'})가 안전하게 저장되었습니다."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/download/valuation_excel")
def download_valuation_excel():
    excel_path = os.path.abspath(os.path.join(ROOT_DIR, "..", "data", "Startup_Valuation_Master_All_Methods_and_Cases.xlsx"))
    if not os.path.exists(excel_path):
        alt_path = os.path.abspath(os.path.join(ROOT_DIR, "data", "Startup_Valuation_Master_All_Methods_and_Cases.xlsx"))
        if os.path.exists(alt_path):
            excel_path = alt_path
        else:
            return {"status": "error", "message": "엑셀 파일을 찾을 수 없습니다."}
    return FileResponse(
        path=excel_path,
        filename="Startup_Valuation_Master_All_Methods_and_Cases.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/api/analyze_company")
async def analyze_company(
    company_name: str = Form(...),
    industry_code: Optional[str] = Form("auto"),
    materials_text: Optional[str] = Form(""),
    file: Optional[UploadFile] = File(None),
):
    try:
        combined_text = materials_text or ""

        # 0. 기업 DB 및 DART 전자공시 · 특허 · 동적 세제/법령 레지스트리 데이터 자동 결합!
        engine = init_db()
        session = get_session(engine)
        auto_enriched_sources = []
        try:
            comp = session.query(CompanyProfile).filter(CompanyProfile.corp_name.like(f"%{company_name.strip()}%")).first()
            if not comp:
                # 로컬 DB에 없으면 DART 실시간 조회 시도
                cands = search_dart_candidates(company_name.strip(), limit=1)
                if cands:
                    detail = fetch_dart_company_detail(cands[0]["corp_code"])
                    if detail:
                        comp = _upsert_company_dict(session, detail)

            if comp:
                auto_enriched_sources.append(comp.data_source or "DART")
                combined_text += (
                    f"\n\n[시스템 자동 연동 - 공인 기업개황 및 재무정보 ({comp.data_source})]\n"
                    f"- 법인명: {comp.corp_name} ({comp.corp_cls or '비상장'}) | 대표이사: {comp.ceo_name or '-'} | 설립일: {comp.est_dt or '-'}\n"
                    f"- 사업자번호: {comp.biz_reg_no or '-'} | 주소: {comp.address or '-'} | 임직원수: {comp.employee_count or '미공시'}명\n"
                    f"- 재무/신용등급: {comp.credit_grade or '-'} | 최근 결산연도({comp.latest_bsns_year or '-'}년): "
                    f"매출액 {comp.revenue_krw if comp.revenue_krw is not None else '-'}억원, "
                    f"영업이익 {comp.op_profit_krw if comp.op_profit_krw is not None else '-'}억원, "
                    f"당기순이익 {comp.net_income_krw if comp.net_income_krw is not None else '-'}억원, "
                    f"자산총계 {comp.total_assets_krw if comp.total_assets_krw is not None else '-'}억원, "
                    f"부채총계 {comp.total_liab_krw if comp.total_liab_krw is not None else '-'}억원, "
                    f"자본총계 {comp.total_equity_krw if comp.total_equity_krw is not None else '-'}억원\n"
                )
                if comp.financial_history_json:
                    combined_text += f"- 3개년 재무 추이(억원): {comp.financial_history_json}\n"
                if comp.capital_increase_summary:
                    combined_text += f"- 주요 유상증자·RCPS·자본변동 공시 내역:\n{comp.capital_increase_summary}\n"

            patents = session.query(CompanyPatent).filter(CompanyPatent.applicant_name.like(f"%{company_name.strip()}%")).limit(8).all()
            if patents:
                auto_enriched_sources.append("특허DB")
                pat_lines = [f"  * [{p.application_date}] {p.invention_title} ({p.registration_status})" for p in patents]
                combined_text += "\n[시스템 자동 연동 - 보유 특허/IP 현황]\n" + "\n".join(pat_lines) + "\n"

            # 동적 설정 레지스트리(벤처 세제·조합 의무비율) 참조 주입
            reg_items = get_dynamic_legal_tax_registry(session)
            if reg_items:
                reg_lines = [f"  * {r['config_label']}: {r['config_value']}{r['unit']} ({r['legal_basis']})" for r in reg_items[:6]]
                combined_text += "\n[동적 설정 레지스트리 - 현행 벤처투자 법령·세제 기준]\n" + "\n".join(reg_lines) + "\n"
        except Exception as enrich_err:
            print(f"Auto-enrich warning: {enrich_err}")
        finally:
            session.close()

        # 1. 첨부 파일 텍스트 추출
        if file and file.filename:
            file_bytes = await file.read()
            extracted_file_text = extract_text_from_file(file.filename, file_bytes)
            combined_text += f"\n\n[첨부 문서: {file.filename}]\n{extracted_file_text}"

        # 2. 홈페이지 URL 자동 웹 크롤링
        detected_urls = extract_urls_from_text(materials_text or "")
        if detected_urls:
            loop = asyncio.get_event_loop()
            for u in detected_urls[:2]:
                try:
                    scraped_info = await loop.run_in_executor(None, scrape_website_content, u)
                    combined_text += f"\n\n{scraped_info}"
                except Exception as sc_err:
                    combined_text += f"\n\n[웹사이트 크롤링 오류: {str(sc_err)}]"

        industry_info = None
        if industry_code and industry_code != "auto":
            industry_info = industry_manager.code_map.get(industry_code)
            if not industry_info:
                industry_info = industry_manager.minor_map.get(industry_code)

        if not industry_info:
            classified = industry_manager.classify_text(f"{company_name}\n{combined_text}")
            matched_code = classified.get("code")
            if matched_code and matched_code in industry_manager.code_map:
                industry_info = industry_manager.code_map[matched_code]
            else:
                industry_info = {
                    "code": classified.get("code", "OT-T-01"),
                    "major": classified.get("major", "기타"),
                    "type": "기존 산업",
                    "middle": classified.get("middle", "전통 소부장"),
                    "minor": classified.get("minor", "기타"),
                }

        prompt_script, major = build_ic_memo_prompt(company_name, industry_info, combined_text)
        report = await generate_ic_memo(company_name, industry_info, combined_text)

        return {
            "status": "success",
            "company_name": company_name,
            "industry_info": industry_info,
            "auto_enriched_sources": auto_enriched_sources,
            "report": report,
            "prompt_script": prompt_script,
        }
    except Exception as e:
        return {"status": "error", "message": f"기업 분석 중 오류 발생: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
