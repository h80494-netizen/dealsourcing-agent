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

import requests

def resolve_meta_redirect(url: str) -> str:
    try:
        res = requests.get(url, timeout=10)
        # HTTP redirect는 requests가 자동 처리함
        # HTML 내 meta refresh 확인
        match = re.search(r'content="\d+;\s*url=([^"]+)"', res.text, re.IGNORECASE)
        if match:
            return match.group(1)
        return res.url
    except:
        return url

def extract_and_clean_text(url):
    """1단계: 웹페이지 본문(텍스트만) 수집 및 정제"""
    try:
        real_url = resolve_meta_redirect(url)
        article = Article(real_url, language='ko')
        article.download()
        article.parse()
        text = article.text.strip() if article.text else ""
        # 3000자로 Truncate
        return text[:3000]
    except Exception as e:
        print(f"Failed to extract text from {url}: {e}")
        return ""

def evaluate_and_summarize_article(title, clean_text, country, pub_date=None):
    """2단계: 정제된 기사 텍스트를 바탕으로 평가 및 요약 (gemini-3.5-flash)"""
    impact_score = 0
    news_grade = "C"
    reason = ""
    summary = ""
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key and (clean_text or title):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-3.5-flash')
            eval_prompt = (
                "당신은 벤처캐피탈(VC) 심사역입니다. 다음 기사의 [제목]과 [내용]을 읽고, "
                "이 기사가 가지는 투자 '영향력 점수(0~100점)'를 아래 6가지 구체적 기준에 따라 엄격하게 평가하세요.\n"
                "각 항목은 고정 점수가 아니며, 기사의 세부 내용(파급력, 신뢰성 등)에 따라 해당 점수 구간 내에서 1점 단위로 미세조정(Fine-tuning)하여 부여해야 합니다. 모든 기사에 70점 등 동일한 점수를 주지 말고 42, 73, 86처럼 철저히 차등 평가하세요.\n\n"
                "### 평가 기준 (총 100점 만점)\n"
                "1. 지역별 중요도 (최대 10점)\n"
                "   - 8~10점: 글로벌 선도 거점 (미국 실리콘밸리, 뉴욕, 영국 런던 등 파급력이 큰 지역)\n"
                "   - 4~7점: 주요 벤처 거점 (한국, 주요 유럽(독일/프랑스 포함), 일본 등)\n"
                "   - 1~3점: 기타 지역 또는 제한적 영향력\n"
                "2. 직접적인 영향 (최대 15점)\n"
                "   - 13~15점: 생태계 판도를 바꾸는 M&A, 규제 철폐, 산업 패러다임 변화 (게임체인저)\n"
                "   - 7~12점: 특정 기업의 괄목할만한 성과, 주요 기술 개발 성공, 유의미한 규제 통과\n"
                "   - 1~6점: 단순 트렌드, 가십성 기사, 간접적 영향\n"
                "3. 투자 단계별 가점 (최대 20점)\n"
                "   - 16~20점: Deal Sourcing (초기 발굴, 시드~시리즈A 직전, 극초기 유망주)\n"
                "   - 11~15점: Due Diligence (실사 단계, 시리즈 A~B 진행 중)\n"
                "   - 6~10점: Investment (본격적 자금 조달 완료, 시리즈 C 이상)\n"
                "   - 4~5점: Value-up (성장기, 파트너십, 수주 계약)\n"
                "   - 1~3점: Exit (IPO, M&A 완료 등 - 이미 가치가 반영됨)\n"
                "4. 펀딩 규모 및 확실성 (최대 15점)\n"
                "   - 11~15점: 대형 규모 투자 확정 (100억 이상 규모 등)\n"
                "   - 6~10점: 중간 규모 투자 확정 또는 대형 펀딩 루머/진행중\n"
                "   - 4~5점: 초기 시드 펀딩 확정 또는 정부 지원금\n"
                "   - 1~3점: 자금 조달 계획 없음 또는 불확실\n"
                "5. 사업 전망 및 성장성 (최대 15점)\n"
                "   - 11~15점: 시장 내 독점적 지위 기대, 압도적 성장 모멘텀\n"
                "   - 6~10점: 준수한 성장성, 안정적인 BM\n"
                "   - 1~5점: 경쟁 심화, 제한적 성장성\n"
                "6. 화제성 및 대중성 (최대 10점)\n"
                "   - 8~10점: 전 세계적 메가 트렌드, 빅테크 연관 뉴스, 압도적 화제성(조회수 폭발 예상)\n"
                "   - 4~7점: 업계 내 주요 화제거리, 다수 매체 보도\n"
                "   - 1~3점: 특정 기업만의 국소적 이슈, 대중적 관심 저조\n"
                "7. 적시성 및 최신성 (최대 15점)\n"
                "   - 11~15점: 기사 발행일이 최근 1주일 이내로 매우 최신 정보인 경우\n"
                "   - 6~10점: 기사 발행일이 1주~1달 사이인 경우\n"
                "   - 1~5점: 과거 뉴스이거나 날짜 미상인 경우\n\n"
                "총점(impact_score)은 위 7개 항목의 합(최대 100점)입니다.\n\n"
                f"[제목]: {title}\n"
                f"[발행일]: {pub_date if pub_date else '미상'}\n"
                f"[내용]: {clean_text}\n\n"
                "반드시 아래 JSON 형식으로만 응답하세요. (점수는 예시가 아닌 실제 계산값을 넣으세요):\n"
                '{"impact_score": 계산된_숫자, "reason": "평가 사유 1문장", "summary": "기사 3줄 요약", "score_details": {"region": 0, "impact": 0, "stage": 0, "funding": 0, "prospect": 0, "virality": 0, "timeliness": 0}}'
            )
            response = model.generate_content(eval_prompt)
            
            import json
            json_str = re.search(r'\{.*\}', response.text.strip(), re.DOTALL)
            if json_str:
                eval_data = json.loads(json_str.group())
                impact_score = float(eval_data.get("impact_score", 0))
                
                # Python에서 점수에 따른 등급을 강제 할당
                if impact_score >= 95: news_grade = "S"
                elif impact_score >= 90: news_grade = "AAA"
                elif impact_score >= 85: news_grade = "AA"
                elif impact_score >= 80: news_grade = "A"
                elif impact_score >= 70: news_grade = "BBB"
                elif impact_score >= 60: news_grade = "BB"
                elif impact_score >= 50: news_grade = "B"
                else: news_grade = "기타"
                
                reason = eval_data.get("reason", "")
                summary = eval_data.get("summary", "")
                details = eval_data.get("score_details", {})
                print(f"[AI 득점 로그] {title[:30]}... -> 총 {impact_score}점 {details}")
        except Exception as e:
            print(f"AI Evaluation failed: {e}")
            
    return impact_score, news_grade, reason, summary

def analyze_text(title, content="", url="", source_country=None, pub_date=None):
    """
    텍스트(제목+내용)를 분석하여 매칭된 키워드와 분류 정보를 반환합니다.
    매칭된 키워드가 없으면 None을 반환합니다.
    """
    full_text = f"{title} {content}".lower()
    clean_text = ""
    
    if url:
        clean_text = extract_and_clean_text(url)
        
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
            if any(kw in full_text for kw in ["미국", "us", "usa", "실리콘밸리", "뉴욕", "silicon valley", "new york", "america"]):
                country = "미국"
            elif any(kw in full_text for kw in ["유럽", "eu", "영국", "프랑스", "독일", "런던", "europe", "uk", "london", "france", "paris", "germany", "berlin", "deutschland"]):
                country = "유럽"
            elif any(kw in full_text for kw in ["일본", "japan", "도쿄", "tokyo"]):
                country = "일본"
            elif any(kw in full_text for kw in ["중국", "china", "베이징", "상하이", "홍콩"]):
                country = "중국"
        
        # 번역 처리 (한국어가 아닌 경우 또는 한국어가 포함되지 않은 경우)
        if country != "한국" or not re.search(r'[가-힣]', title):
            title = translate_to_korean(title)
            if clean_text:
                clean_text = translate_to_korean(clean_text)
        
        # 2. 절차(Stage) 분류
        deal_stage = "Deal Sourcing"
        for stage, kws in STAGE_KEYWORDS.items():
            if any(kw in full_text for kw in kws):
                deal_stage = stage
        
        # 3. 영향력 점수 및 뉴스 등급 (AI 문맥 평가)
        impact_score, news_grade, reason, ai_summary = evaluate_and_summarize_article(title, clean_text, country, pub_date)
        
        # Fallback to rule-based if AI evaluation failed
        if impact_score == 0 and news_grade == "C":
            impact_score = calculate_mock_score(found_industry, found_signal, found_financial, country, deal_stage, pub_date)

            if impact_score >= 95: news_grade = "S"
            elif impact_score >= 90: news_grade = "AAA"
            elif impact_score >= 85: news_grade = "AA"
            elif impact_score >= 80: news_grade = "A"
            elif impact_score >= 70: news_grade = "BBB"
            elif impact_score >= 60: news_grade = "BB"
            elif impact_score >= 50: news_grade = "B"
            else: news_grade = "기타"
            
        promising_industry = ", ".join(found_industry) if found_industry else "기타/미정"
        
        compressed_summary = ""
        if reason:
            compressed_summary = f"[{news_grade}등급] {reason}\n{ai_summary if ai_summary else clean_text[:200]}"
        else:
            compressed_summary = ai_summary if ai_summary else clean_text[:200]
            
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
            'compressed_summary': compressed_summary,
            'title': title
        }
    return None

def calculate_mock_score(industry, signal, financial, country, deal_stage, pub_date=None):
    import random
    from datetime import datetime, timedelta
    
    # Rule-based fallback scoring matching the 7 criteria
    score = 0
    # 1. 지역 (max 10)
    if country == "미국": score += random.randint(8, 10)
    elif country in ["한국", "유럽", "일본"]: score += random.randint(4, 7)
    else: score += random.randint(1, 3)
    
    # 2. 직접적 영향 (max 15)
    if signal and len(signal) > 2: score += random.randint(12, 15)
    elif signal: score += random.randint(6, 11)
    else: score += random.randint(1, 5)
    
    # 3. 단계 (max 20)
    if deal_stage == "Deal Sourcing": score += random.randint(16, 20)
    elif deal_stage == "Due Diligence": score += random.randint(11, 15)
    elif deal_stage == "Investment": score += random.randint(6, 10)
    elif deal_stage == "Value-up": score += random.randint(4, 5)
    else: score += random.randint(1, 3)
    
    # 4. 펀딩 (max 15)
    if financial and len(financial) > 1: score += random.randint(11, 15)
    elif financial: score += random.randint(6, 10)
    else: score += random.randint(2, 5)
    
    # 5. 사업전망 (max 15)
    if industry: score += random.randint(10, 15)
    else: score += random.randint(1, 9)
    
    # 6. 화제성 (max 10)
    if signal or financial: score += random.randint(6, 10)
    else: score += random.randint(1, 5)
    
    # 7. 적시성 (max 15)
    if pub_date:
        if isinstance(pub_date, str):
            score += random.randint(6, 10) # parsing skipped for simplicity
        else:
            diff = (datetime.now() - pub_date).days
            if diff <= 7: score += random.randint(11, 15)
            elif diff <= 30: score += random.randint(6, 10)
            else: score += random.randint(1, 5)
    else:
        score += random.randint(1, 5)
    
    return min(95.0, float(score))
