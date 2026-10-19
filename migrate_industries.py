import os
import sys
import io

# 콘솔 UTF-8 출력 보장
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db_manager import init_db, get_session
from database.models import DealArticle
from industry_manager import industry_manager

def migrate_existing_articles():
    engine = init_db()
    session = get_session(engine)
    
    articles = session.query(DealArticle).all()
    print(f"Total articles to inspect: {len(articles)}")
    
    updated_count = 0
    for art in articles:
        # 제목과 기존 요약/본문 기반으로 재분류
        text_for_eval = f"{art.title} {art.summary or ''} {art.compressed_summary or ''} {art.matched_industry or ''}"
        
        classification = industry_manager.classify_text(text_for_eval)
        new_formatted = classification['formatted']
        
        changed = False
        # 산업분류 업데이트
        if art.promising_industry != new_formatted:
            old_val = art.promising_industry
            art.promising_industry = new_formatted
            changed = True

        # 뉴스 등급 (A, B, C, D, E) 업데이트
        score = art.impact_score or 0
        if score >= 80: new_grade = "A"
        elif score >= 70: new_grade = "B"
        elif score >= 60: new_grade = "C"
        elif score >= 50: new_grade = "D"
        else: new_grade = "E"

        if art.news_grade != new_grade:
            art.news_grade = new_grade
            changed = True

        if changed:
            updated_count += 1
            if updated_count <= 10:
                print(f"[{art.id}] 등급:{art.news_grade}, 산업:{art.promising_industry} | {art.title[:30]}...")

    session.commit()
    session.close()
    print(f"Migration completed! Updated {updated_count} of {len(articles)} articles.")

if __name__ == '__main__':
    migrate_existing_articles()
