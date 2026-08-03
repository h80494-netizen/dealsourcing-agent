import time
from datetime import datetime
from database.db_manager import init_db, get_session
from database.models import DealArticle, ResearchDomain
from collectors.news_rss_collector import collect_all_rss
from collectors.naver_news_collector import collect_naver_news
from processor.analyzer import analyze_text
from config import INDUSTRY_KEYWORDS, SIGNAL_KEYWORDS

def run_pipeline():
    print(f"[{datetime.now()}] 파이프라인 시작...")
    engine = init_db()
    session = get_session(engine)
    
    # 1. 수집
    from config import SIGNAL_KEYWORDS_DICT, INDUSTRY_KEYWORDS_DICT
    ko_signals = SIGNAL_KEYWORDS_DICT.get('ko', [])[:3]
    ko_industries = INDUSTRY_KEYWORDS_DICT.get('ko', [])[:2]
    naver_kws = ko_signals + ko_industries

    domains = session.query(ResearchDomain).filter_by(is_active=True).all()
    
    print("글로벌 RSS 및 Google News 수집 중...")
    rss_articles = collect_all_rss(domains=domains)
    
    print("Naver News 스크래핑 중...")
    naver_articles = collect_naver_news(naver_kws)
    
    all_articles = rss_articles + naver_articles
    
    # 2. 분석 및 저장
    new_count = 0
    for art in all_articles:
        # 중복 체크
        exists = session.query(DealArticle).filter_by(link=art['link']).first()
        if exists:
            continue
            
        # 분석
        analysis_result = analyze_text(art['title'], art['summary'], url=art['link'], source_country=art.get('country'))
        
        # 유의미한 데이터만 DB 저장
        if analysis_result:
            new_deal = DealArticle(
                source_name=art['source_name'],
                title=analysis_result.get('title', art['title']),
                link=art['link'],
                summary=art['summary'],
                pub_date=art['pub_date'],
                matched_industry=analysis_result['matched_industry'],
                matched_signal=analysis_result['matched_signal'],
                matched_financial=analysis_result['matched_financial'],
                growth_impact_score=analysis_result['growth_impact_score'],
                country=analysis_result['country'],
                deal_stage=analysis_result['deal_stage'],
                impact_score=analysis_result['impact_score'],
                news_grade=analysis_result['news_grade'],
                promising_industry=analysis_result['promising_industry'],
                compressed_summary=analysis_result.get('compressed_summary')
            )
            session.add(new_deal)
            new_count += 1
            
    session.commit()
    print(f"[{datetime.now()}] 파이프라인 완료. 새로 추가된 유의미한 기사 수: {new_count}")
    
    # 3. 일일 리포트 생성
    from processor.report_generator import generate_daily_report
    print("일일 요약 리포트 생성을 시작합니다...")
    generate_daily_report()

if __name__ == "__main__":
    run_pipeline()
