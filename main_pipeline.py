import sys
import time
from datetime import datetime

# Windows console encoding fix
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
from database.db_manager import init_db, get_session
from database.models import DealArticle, ResearchDomain
from collectors.news_rss_collector import collect_all_rss
from collectors.naver_news_collector import collect_naver_news
from processor.analyzer import analyze_text
from config import INDUSTRY_KEYWORDS, SIGNAL_KEYWORDS

def run_pipeline(progress_callback=None):
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
    print(f"총 {len(all_articles)}개의 기사 중 새로운 기사를 필터링합니다...")
    
    # 먼저 DB에 없으며, 최근 2일 이내의 기사만 추려냄
    from datetime import timedelta
    time_threshold = datetime.now() - timedelta(days=2)
    
    new_articles = []
    for art in all_articles:
        if art['pub_date'] and art['pub_date'] < time_threshold:
            continue
            
        exists = session.query(DealArticle).filter_by(link=art['link']).first()
        if not exists:
            new_articles.append(art)
            
    print(f"분석할 새로운 기사 {len(new_articles)}건 발견. 병렬 분석을 시작합니다...")
    
    import concurrent.futures
    new_count = 0
    country_stats = {}
    
    def process_article(art):
        try:
            return art, analyze_text(art['title'], art['summary'], url=art['link'], source_country=art.get('country'), pub_date=art.get('pub_date'))
        except Exception as e:
            print(f"Error analyzing article {art['link']}: {e}")
            return art, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # submit all tasks
        futures = {executor.submit(process_article, art): art for art in new_articles}
        
        for idx, future in enumerate(concurrent.futures.as_completed(futures), 1):
            art, analysis_result = future.result()
            
            msg = f"분석 진행 중... ({idx}/{len(new_articles)})"
            if idx % 5 == 0 or idx == len(new_articles):
                print(msg)
                
            if progress_callback:
                try:
                    progress_callback(msg, idx, len(new_articles))
                except Exception as e:
                    print(f"Callback error: {e}")
                
            if analysis_result and analysis_result.get('news_grade') not in ['기타', 'C']:
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
                try:
                    session.commit()
                    new_count += 1
                    
                    c = analysis_result.get('country') or '기타'
                    if c not in country_stats:
                        country_stats[c] = 0
                    country_stats[c] += 1
                    
                except Exception as e:
                    session.rollback()
                    print(f"Error committing article {art['link']}: {e}")
            
    print(f"[{datetime.now()}] 파이프라인 완료. 새로 추가된 유의미한 기사 수: {new_count}")
    
    # 3. 일일 리포트 생성
    from processor.report_generator import generate_daily_report
    print("일일 요약 리포트 생성을 시작합니다...")
    generate_daily_report()
    
    # 4. 데이터 보존 정책 실행 (최근 1년 이외 데이터 정리)
    try:
        from datetime import timedelta
        retention_limit = datetime.now() - timedelta(days=365)
        deleted_count = session.query(DealArticle).filter(DealArticle.created_at < retention_limit).delete()
        session.commit()
        print(f"[{datetime.now()}] Retention Policy: 1년 경과된 기사 데이터 {deleted_count}건을 삭제하였습니다.")
    except Exception as e:
        session.rollback()
        print(f"Error during database cleanup: {e}")
        
    return country_stats

if __name__ == "__main__":
    def simple_progress(msg, current, total):
        print(f"[PROGRESS] {msg}")
    run_pipeline(progress_callback=simple_progress)
