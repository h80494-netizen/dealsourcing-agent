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
        model = genai.GenerativeModel('gemini-1.5-flash-8b')
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
    
    def match_keywords(kws, text):
        found = []
        for kw in kws:
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', text) if kw.isascii() else kw.lower() in text:
                found.append(kw)
        return found
        
    found_industry = match_keywords(INDUSTRY_KEYWORDS, full_text)
    found_signal = match_keywords(SIGNAL_KEYWORDS, full_text)
    found_financial = match_keywords(FINANCIAL_KEYWORDS, full_text)
    
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
        
        # 3. 영향력 점수 및 뉴스 등급 (AI 문맥 평가)
        impact_score = 0
        news_grade = "C"
        reason = ""
        
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key and (compressed_summary or full_text):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash-8b')
                eval_prompt = (
                    "당신은 벤처캐피탈(VC) 심사역입니다. 다음 기사의 [제목]과 [내용]을 읽고, "
                    "이 벤처/스타트업 기사가 투자 대상으로서 가지는 '영향력 점수(0~100)'와 '등급(S+, S, A+, A, B+, B, C, D)'을 평가하세요.\n\n"
                    "- S+ 등급 (95~100점): 초대형 메가 딜, 글로벌 시장 판도를 바꾸는 M&A 등\n"
                    "- S 등급 (90~94점): 대규모 투자 유치, 주요 상장(IPO) 등 결정적 기사\n"
                    "- A+ 등급 (80~89점): 대형 시리즈 B/C 투자, 핵심 파트너십 체결\n"
                    "- A 등급 (70~79점): 시리즈 A/B 등 중간 규모 투자, 주요 실적 발표\n"
                    "- B+ 등급 (60~69점): 초기 시드 투자(팁스 등), 유의미한 신제품 출시\n"
                    "- B 등급 (50~59점): 일반적인 산업 동향, 벤처 관련 일반 기사\n"
                    "- C 등급 (40~49점): 영향력이 미미한 기사\n"
                    "- D 등급 (40점 미만): 단순 가십, 광고, 벤처 투자와 무관한 기사\n\n"
                    f"[제목]: {title}\n"
                    f"[내용]: {compressed_summary if compressed_summary else full_text[:500]}\n\n"
                    "반드시 아래 JSON 형식으로만 응답하세요. 다른 설명은 제외합니다:\n"
                    '{"impact_score": 85, "news_grade": "S", "reason": "평가 사유 1문장"}'
                )
                response = model.generate_content(eval_prompt)
                
                import json
                # 정규식으로 JSON 부분만 추출
                json_str = re.search(r'\{.*\}', response.text.strip(), re.DOTALL)
                if json_str:
                    eval_data = json.loads(json_str.group())
                    impact_score = float(eval_data.get("impact_score", 0))
                    news_grade = eval_data.get("news_grade", "C")
                    reason = eval_data.get("reason", "")
            except Exception as e:
                print(f"AI Evaluation failed: {e}")
                # Fallback to rule-based
                base_score = calculate_mock_score(found_industry, found_signal, found_financial)
                impact_score = base_score * 20.0
                if impact_score >= 95: news_grade = "S+"
                elif impact_score >= 90: news_grade = "S"
                elif impact_score >= 80: news_grade = "A+"
                elif impact_score >= 70: news_grade = "A"
                elif impact_score >= 60: news_grade = "B+"
                elif impact_score >= 50: news_grade = "B"
                elif impact_score >= 40: news_grade = "C"
                else: news_grade = "D"
        else:
            # Fallback to rule-based
            base_score = calculate_mock_score(found_industry, found_signal, found_financial)
            impact_score = base_score * 20.0
            if impact_score >= 95: news_grade = "S+"
            elif impact_score >= 90: news_grade = "S"
            elif impact_score >= 80: news_grade = "A+"
            elif impact_score >= 70: news_grade = "A"
            elif impact_score >= 60: news_grade = "B+"
            elif impact_score >= 50: news_grade = "B"
            elif impact_score >= 40: news_grade = "C"
            else: news_grade = "D"
            
        promising_industry = ", ".join(found_industry) if found_industry else "기타/미정"
        
        return {
            'matched_industry': ", ".join(found_industry) if found_industry else None,
            'matched_signal': ", ".join(found_signal) if found_signal else None,
            'matched_financial': ", ".join(found_financial) if found_financial else None,
            'growth_impact_score': impact_score / 20.0,
            'country': country,
            'deal_stage': deal_stage,
            'impact_score': impact_score,
            'news_grade': news_grade,
            'promising_industry': promising_industry,
            'compressed_summary': f"[{news_grade}등급] {reason}\n{compressed_summary}" if reason else compressed_summary,
            'title': title
        }
    return None

def calculate_mock_score(industry, signal, financial):
    score = 1.0
    if industry: score += 1.0
    if signal: score += 1.5
    if financial: score += 1.5
    return min(5.0, score)
