from config import INDUSTRY_KEYWORDS, SIGNAL_KEYWORDS, FINANCIAL_KEYWORDS
import re
from newspaper import Article

STAGE_KEYWORDS = {
    "Deal Sourcing": ["시드", "시리즈", "창업", "팁스", "tips", "seed", "발굴", "스타트업"],
    "Due Diligence": ["실사", "due diligence", "검토", "감사", "평가"],
    "Investment": ["투자", "유치", "펀딩", "조달", "자금", "series"],
    "Value-up": ["성장", "파트너십", "수주", "mou", "채용", "확장", "매출", "흑자", "bep"],
    "Exit": ["상장", "ipo", "인수", "합병", "m&a", "매각", "엑시트", "스팩"]
}

import os
import google.generativeai as genai
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

def translate_to_korean(text):
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return text
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.5-flash')
        prompt = f"다음 텍스트를 한국어로 자연스럽게 번역해줘. 번역 결과만 출력해:\n\n{text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Translation failed: {e}")
        return text

def analyze_text(title, content="", url="", source_country=None):
    """
    텍스트(제목+내용)를 분석하여 매칭된 키워드와 분류 정보를 반환합니다.
    매칭된 키워드가 없으면 None을 반환합니다.
    """
    full_text = f"{title} {content}".lower()
    compressed_summary = None
    
    if url:
        try:
            article = Article(url, language='ko')
            article.download()
            article.parse()
            article.nlp()
            if article.summary:
                compressed_summary = article.summary
            else:
                compressed_summary = article.text[:200] + "..." if article.text else ""
        except Exception as e:
            print(f"Failed to extract summary from {url}: {e}")
    
    found_industry = [kw for kw in INDUSTRY_KEYWORDS if kw.lower() in full_text]
    found_signal = [kw for kw in SIGNAL_KEYWORDS if kw.lower() in full_text]
    found_financial = [kw for kw in FINANCIAL_KEYWORDS if kw.lower() in full_text]
    
    if found_industry or found_signal or found_financial:
        # 1. 국가 분류 (source_country 우선)
        country = source_country
        if not country:
            country = "한국"
            if any(kw in full_text for kw in ["미국", "us", "usa", "실리콘밸리", "뉴욕"]):
                country = "미국"
            elif any(kw in full_text for kw in ["유럽", "eu", "영국", "프랑스", "독일", "런던", "europe"]):
                country = "유럽"
            elif any(kw in full_text for kw in ["일본", "japan", "도쿄", "tokyo"]):
                country = "일본"
            elif any(kw in full_text for kw in ["중국", "china", "베이징", "상하이", "홍콩"]):
                country = "중국"
        
        # 번역 처리 (한국이 아닌 경우)
        if country != "한국":
            title = translate_to_korean(title)
            if compressed_summary:
                compressed_summary = translate_to_korean(compressed_summary)
        
        # 2. 절차(Stage) 분류
        deal_stage = "Deal Sourcing"
        for stage, kws in STAGE_KEYWORDS.items():
            if any(kw in full_text for kw in kws):
                deal_stage = stage
        
        # 3. 영향력 점수 및 뉴스 등급
        base_score = calculate_mock_score(found_industry, found_signal, found_financial)
        
        impact_score = base_score * 20.0
        
        if impact_score >= 80:
            news_grade = "S"
        elif impact_score >= 60:
            news_grade = "A"
        elif impact_score >= 40:
            news_grade = "B"
        else:
            news_grade = "C"
            
        promising_industry = ", ".join(found_industry) if found_industry else "기타/미정"
        
        return {
            'matched_industry': ", ".join(found_industry) if found_industry else None,
            'matched_signal': ", ".join(found_signal) if found_signal else None,
            'matched_financial': ", ".join(found_financial) if found_financial else None,
            'growth_impact_score': base_score,
            'country': country,
            'deal_stage': deal_stage,
            'impact_score': impact_score,
            'news_grade': news_grade,
            'promising_industry': promising_industry,
            'compressed_summary': compressed_summary,
            'title': title
        }
    return None

def calculate_mock_score(industry, signal, financial):
    score = 1.0
    if industry: score += 1.0
    if signal: score += 1.5
    if financial: score += 1.5
    return min(5.0, score)
