import os
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database.db_manager import init_db, get_session
from database.models import DealArticle

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

def generate_daily_report():
    engine = init_db()
    session = get_session(engine)
    
    # 최근 24시간 이내 기사 수집
    time_threshold = datetime.utcnow() - timedelta(days=1)
    recent_articles = session.query(DealArticle).filter(DealArticle.created_at >= time_threshold).all()
    
    if not recent_articles:
        print("최근 24시간 내 수집된 기사가 없어 리포트를 생성하지 않습니다.")
        session.close()
        return
        
    # 국가별 그룹핑 및 점수순 정렬
    articles_by_country = {}
    for art in recent_articles:
        country = art.country or "한국"
        if country not in articles_by_country:
            articles_by_country[country] = []
        articles_by_country[country].append(art)
        
    for country in articles_by_country:
        # impact_score 역순 정렬 후 최대 5개 선택
        articles_by_country[country].sort(key=lambda x: (x.impact_score or 0), reverse=True)
        articles_by_country[country] = articles_by_country[country][:5]
        
    # Markdown 리포트 초기화
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_lines = [
        f"# 글로벌 산업별 뉴스 파이프라인 일일 요약 리포트 ({today_str})",
        "",
        "## 💡 AI 트렌드 브리핑 및 해석",
        ""
    ]
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
    
    # 전체 기사를 하나의 컨텍스트로 통합
    context_lines = []
    for country, arts in articles_by_country.items():
        if not arts:
            continue
        context_lines.append(f"### 지역: {country}")
        for idx, art in enumerate(arts):
            date_str = art.pub_date.strftime("%Y-%m-%d") if art.pub_date else "최근"
            grade = art.news_grade or "C"
            source = art.source_name or "알 수 없음"
            title = art.title
            summary = art.summary[:300] if art.summary else ""
            context_lines.append(f"{idx+1}. [일자: {date_str}] [중요도: {grade}] [출처: {source}] 원문/번역제목: {title}\n요약: {summary}")
        context_lines.append("")
        
    context_text = "\n".join(context_lines)
    
    if api_key and context_text.strip():
        try:
            prompt = (
                "당신은 벤처캐피탈(VC) 심사역을 위한 시니어 애널리스트입니다.\n"
                "다음은 오늘 수집된 글로벌 벤처캐피탈/스타트업 핵심 뉴스 목록입니다.\n"
                "이 뉴스들을 분석하여 **깔끔한 경영 보고서(Document Report) 형태**의 마크다운 리포트를 작성해 주세요.\n\n"
                "## [리포트 구성 양식]\n"
                "# [일간] 글로벌 벤처캐피탈·스타트업 뉴스 브리핑\n"
                f"- 발송일자: {today_str}\n"
                "- 작성자: AI 애널리스트\n\n"
                "## 1. 주요 기업 분석 (Company Analysis)\n"
                "※ 제공된 뉴스 중 특정 '기업'과 관련된 기사들을 기업별로 묶어서 아래 양식으로 정리해 주세요.\n"
                "### [기업명 (국가/라운드)]\n"
                "- **투자 금액**: \n"
                "- **핵심 요약**: 한국어 번역 헤드라인 및 주요 비즈니스 모델\n"
                "- **기업 분석**: (1) Executive summary (2) 산업 및 사업 분석\n\n"
                "## 2. 시장 동향 및 정책 (Market & Policy)\n"
                "※ 벤처캐피탈 시장, 펀드, 정책 등 일반 '뉴스' 성격의 기사들을 주제별로 요약해 주세요.\n"
                "### [주제 카테고리명]\n"
                "- **기사 제목 (일자/출처)**\n"
                "  - 주요 내용 요약\n\n"
                "조건: 반드시 프로페셔널한 한국어로 작성해 주세요. 모든 내용은 제공된 [뉴스 목록]에 기반해야 합니다.\n\n"
                f"[뉴스 목록]\n{context_text}"
            )
            
            response = model.generate_content(prompt)
            report_lines.append(response.text.strip())
            report_lines.append("")
        except Exception as e:
            print(f"Briefing generation failed: {e}")
            report_lines.append(f"AI 브리핑을 생성하는 도중 오류가 발생했습니다: {e}")
            report_lines.append("")
    elif not api_key:
        report_lines.append("API 키가 설정되지 않아 AI 브리핑을 생성할 수 없습니다.")
        report_lines.append("")
        
    report_content = "\n".join(report_lines)
    
    # 파일 저장
    report_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
    os.makedirs(report_dir, exist_ok=True)
    
    file_path = os.path.join(report_dir, f"daily_report_{today_str}.md")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"일일 요약 리포트 생성 완료: {file_path}")
    session.close()
    
    return report_content

if __name__ == "__main__":
    generate_daily_report()
