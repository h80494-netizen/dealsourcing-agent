"""
VC 투자심사역(Investment Committee) 관점 기업분석 프롬프트 자동화 및 리포트 생성기
- 42개 업종 분류 체계(대·중·소분류 및 기존/신종 산업)
- 6대 핵심 투자심사 항목 (Cap Table, 시장, 기업/경영진, 프라이싱, 자금용도, 자본조달)
- 5대 섹터별(AI, ICT, 바이오, 커머스, 기타) 특화 지침 동적 결합
"""

import os
import io
import json
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# 업종별 특화 심사 지침 모듈
INDUSTRY_SPECIFIC_MODULES = {
    "AI": """[AI (인공지능) 업종 추가 심사 지시사항]
- 기존 산업 (AI-T-01~02: 예측형 AI·비전·NLP): SI성 용역 매출 비중과 반복 매출(ARR) 비중을 엄격히 구분하십시오. 인건비 투입 대비 매출 총이익률(Gross Margin)이 60% 이상 나오는 제품화(Productization)가 완료되었는지 검증하십시오.
- 신종 산업 (AI-E-01~03: 생성형·에이전틱·피지컬 AI): 빅테크(OpenAI, Google 등)의 모델 업데이트 시 사업 모델이 소멸할 위험(Wrapper Risk)을 평가하십시오. 피지컬 AI의 경우 시뮬레이션(Sim-to-Real) 데이터 확보 역량과 하드웨어(액추에이터/센서) 통합 제어 능력을 집중 분석하십시오.
- 신종 산업 (AI-E-04~05: AI 반도체·인프라): 자금용도에서 파운드리 공정(Tape-out) 비용과 클라우드 GPU 서버 임차 비용(Compute Burn Rate)을 면밀히 따지십시오. 프라이싱 시 단순 기술 기대감이 아닌 실제 고객사 PoC 통과 및 양산 수주(Design Win) 여부를 반영하십시오.""",

    "ICT": """[ICT (정보통신·SW·HW) 업종 추가 심사 지시사항]
- 기존 산업 (IC-T-01~03: 엔터프라이즈 SW·모바일·통신HW): 시장 포화도와 고객 이탈률(Churn Rate)을 최우선으로 보십시오. 자본조달 시 과도한 밸류에이션의 보통주/RCPS보다는 현금흐름에 기반한 메자닌(CB/BW)이나 배당 조건부 투자가 적합한지 검토하십시오.
- 신종 산업 (IC-E-01~02: 버티컬 SaaS·차세대 보안): 순매출유지율(NRR 110% 이상 여부), LTV/CAC 비율(3배 이상 여부), CAC 회수기간(Payback Period)을 기준으로 프라이싱 멀티플(PSR)의 적정성을 검증하십시오.
- 신종 산업 (IC-E-03~05: 양자기술·공간컴퓨팅·웹3): 상용화까지 긴 시간이 걸리는 딥테크이므로 정부 R&D 과제(무상 자금) 조달 능력과 핵심 특허 포트폴리오를 체크하십시오. 웹3의 경우 토큰 이코노미와 지분(Equity) 가치가 충돌하지 않는지(가치 귀속 구조) 법적·구조적으로 분석하십시오.""",

    "바이오": """[바이오 (바이오·헬스케어) 업종 추가 심사 지시사항]
- 기존 산업 (BI-T-01~03: 제네릭·일반 의료기기·건기식·CMO): 공장 증설(GMP 인증) 등 시설투자(CAPEX) 비중이 높으므로, 가동률(Utilization Rate)과 수주 잔고에 기반해 유상증자 외에 시설자금 차입이나 CB/BW 활용 가능성을 분석하십시오.
- 신종 산업 (BI-E-01~02: 차세대 모달리티 CGT/ADC·합성생물학): 임상 단계(비임상/1상/2상)별 성공 확률을 반영한 위험조정 순현재가치(rNPV)와 글로벌 빅파마의 최근 기술이전(L/O) 계약 규모(Upfront 비율 및 마일스톤)를 기준으로 프라이싱을 검증하십시오. 자금용도가 임상시험수탁기관(CRO) 비용과 CDMO 시료 생산에 정확히 매칭되는지 확인하십시오.
- 신종 산업 (BI-E-03~05: AI 신약·디지털치료제·뇌과학/역노화): FDA/식약처 인허가 통과 여부뿐 아니라, 건강보험 수가(Reimbursement) 적용 가능성과 실제 일선 의사들의 처방 유인책을 시장 진입장벽의 핵심으로 분석하십시오.""",

    "커머스": """[커머스 (유통·소비재) 업종 추가 심사 지시사항]
- 기존 산업 (CM-T-01~03: 종합몰·F&B/패션·로컬 O2O): 거래액(GMV)의 착시를 제거하고 실질 수수료율(Take Rate)과 공헌이익(Contribution Margin) 흑자 여부를 검증하십시오. 재고자산 회전율과 운전자본(Working Capital) 묶임 현상을 분석해 자본조달 수단(단기 차입 vs 지분 투자)을 구분하십시오.
- 신종 산업 (CM-E-01~04: 크로스보더·리커머스·리테일테크·슬립/펨/펫테크): 특정 플랫폼(아마존, 틱톡샵 등) 알고리즘 변경 리스크, 해외 물류/관세 장벽, 재구매율(Retention Cohort)을 집중 분석하십시오. 자금용도에서 단순 퍼포먼스 마케팅(광고비 태우기) 비중이 과도한 경우 프라이싱을 보수적으로 깎으십시오.""",

    "기타": """[기타 (기후·모빌리티·로봇·핀테크·콘텐츠) 업종 추가 심사 지시사항]
- 기존 산업 (OT-T-01~04: 전통 소부장·물류·초기 핀테크·게임/미디어): 전방 산업(완성차, 반도체, 건설 등)의 경기 사이클 의존도와 특정 대기업 매출 편중 리스크(단가 인하 압력)를 분석하십시오. 게임/미디어는 단일 프로젝트 흥행 리스크를 줄일 수 있는 파이프라인 다각화 여부를 체크하십시오.
- 신종 산업 (OT-E-01~02: 기후테크·클린에너지): 정부 보조금이나 탄소배출권 가격 변동 없이도 자체적인 경제성(Unit Economics, 그린 프리미엄 극복 여부)이 나오는 시점을 산출하십시오. 대규모 파일럿 플랜트 설비투자가 필요하므로 프로젝트 파이낸싱(PF), 정책자금 차입, 메자닌(CB/BW)을 결합한 자본조달 구조를 설계하십시오.
- 신종 산업 (OT-E-03~05: 미래 모빌리티·우주/방산·로보틱스): 방산/우주/로봇은 수주 리드타임이 길고 양산 전환 시점에 막대한 운전자본이 소요되는 '죽음의 계곡(Valley of Death)'이 존재합니다. 이번 펀딩 규모가 양산 라인 구축(CAPEX)까지 버틸 수 있는지, 창업자가 기술자 마인드를 넘어 제조·양산·품질관리(QA) 역량을 갖추었는지 검증하십시오.
- 신종 산업 (OT-E-06~08: B2B 핀테크·애그/푸드테크·크리에이터/IP): 금융 규제(라이선스 진입장벽), 식약처 신소재 승인(배양육 등), 핵심 크리에이터/IP 이탈 리스크(Key-man Risk)를 집중 점검하고, 주주간계약서(SHA)에 핵심 인력 의무재직(Lock-up) 및 IP 귀속 조항을 반드시 포함하도록 제안하십시오."""
}

MASTER_IC_TEMPLATE = """# Role: 글로벌 Top-Tier 벤처캐피탈(VC) 수석 투자심사역 (Partner & IC Member)

# Task
제공된 기업의 데이터(IR 자료, 재무제표, 뉴스, 사업계획서, 다국어 기업 정보 등)를 바탕으로, 우리 하우스의 표준 산업 분류 체계에 따라 업종을 매핑하고 아래 6가지 핵심 심사 기준 및 업종별 특화 기준에 맞춰 냉철하고 입체적인 투자심사보고서(Investment Committee Memo)를 한국어로 작성하십시오.

---

## [Step 0] 산업 분류 및 포지셔닝 매핑
제공된 기업 설명과 키워드(한국어/영어/중국어/일본어/독일어/프랑스어)를 분석하여 아래 항목을 먼저 정의하십시오.
- **분류 코드 및 경로:** {industry_mapping}
- **포지셔닝 진단:** 해당 기업이 '기존 산업(안정적 현금흐름·시장점유율 싸움)'인지 '신종 산업(선점효과·기술 해자·밸류에이션 리레이팅)'인지 정의하고, 이에 맞는 심사 잣대를 적용하십시오.

---

## [Step 1] 6대 핵심 투자심사 분석 (Deep-Dive Analysis)

### 1. 지분구성 및 펀드레이징 스토리 (Cap Table & Fundraising Equity Story)
- **주주 구성(Cap Table) 건전성:** 창업자(대표이사) 및 핵심 경영진의 현재 지분율과 이번 라운드 및 향후 Exit(IPO/M&A) 시점까지 예상되는 지분 희석(Dilution) 후 경영권 방어 가능성을 평가하십시오. (Dead Equity: 퇴사한 공동창업자나 초기 비활동 투자자 지분 유무 체크)
- **펀드레이징 히스토리:** 시드(Seed)부터 현재 라운드까지의 투자 유치 시점, 밸류에이션 추이(Step-up 배수), 기존 투자사(FI/SI)의 면면 및 후속 투자(Follow-on) 참여 여부를 분석하십시오.
- **스토리의 일관성:** 이전 라운드에서 투자자들에게 약속했던 마일스톤(KPI)을 실제로 달성했는지, 피벗(Pivot)이 있었다면 그 논리적 타당성이 충분한지 검증하십시오.

### 2. 시장 분석 (Market Dynamics: 성장성·확장성·규모·진입장벽)
- **시장 규모 (TAM-SAM-SOM):** 단순 글로벌 통계 인용이 아닌, 해당 기업의 제품 단가(ARPU)와 타깃 고객 수를 기반으로 한 Bottom-up 방식의 실질 유효 시장(SOM) 규모를 산출하십시오.
- **성장성(CAGR) 및 타이밍(Why Now?):** 시장의 연평균 성장률과 함께, 왜 하필 지금 이 시장이 폭발하는지(규제 변화, 기술 단가 하락, 소비자 행동 변화 등)를 분석하십시오.
- **글로벌 및 인접 시장 확장성(Scalability):** 한계비용 증가 없이 타 지역(크로스보더)이나 인접 버티컬 산업으로 확장할 수 있는 구조인지 평가하십시오.
- **구조적 시장 진입장벽:** 인허가/규제, 초기 자본 집약도, 네트워크 효과, 전환 비용(Switching Cost) 등 후발주자의 진입을 막는 시장 자체의 장벽을 분석하십시오.

### 3. 기업 및 경영진 분석 (Company & Founder: 기술력·해자·오너 역량)
- **기술력 및 독점적 해자(Moat):** 경쟁사 대비 기술적 우위(특허, 독점 데이터셋, 수율, 원가 경쟁력, 알고리즘 성능 등)와 경쟁자가 이를 복제하는 데 걸리는 시간(Lead Time)을 평가하십시오.
- **오너(창업자) 및 핵심 팀 역량 (Founder-Market Fit):** 대표이사의 도메인 전문성, 과거 성공/실패 경험, 기술/영업 핵심 인력(C-level)의 구성, 그리고 위기 상황에서의 실행력과 자본 배분(Capital Allocation) 능력을 냉정하게 평가하십시오.

### 4. 프라이싱 및 밸류에이션 (Pricing: 가격 적정성·펀딩 규모)
- **Pre/Post-money 밸류에이션 적정성:** 동종 업계(Peer Group) 상장사 및 최근 비상장 M&A/투자 거래의 멀티플(PSR, PER, EV/EBITDA, 파이프라인 가치 등)과 비교하여 현재 요구하는 기업가치가 고평가(Overvalued)인지 할인(Discount) 상태인지 산출하십시오.
- **펀딩 규모의 적정성:** 현재 회사의 월간 현금소진율(Burn Rate)과 런웨이(Runway)를 고려할 때, 이번 목표 펀딩 금액이 과도한 지분 희석 없이 다음 라운드(또는 BEP 달성)의 마일스톤을 달성하기에 충분한 금액인지 검증하십시오.
- **예상 투자수익률 (Exit Scenario):** 보수적·기본·낙관적 시나리오별 예상 Exit 시점, Exit 기업가치, 목표 IRR 및 멀티플(MOIC)을 시뮬레이션하십시오.

### 5. 자금 용도 (Use of Proceeds: 인력·시설·R&D·운전자본)
- **자금 투입 계획의 구체성:** 조달 자금이 ① 핵심 인력 충원(R&D/영업), ② 시설 및 장비 투자(CAPEX/인프라), ③ 연구개발 및 임상/인증, ④ 마케팅 및 운전자본(OPEX)에 각각 몇 %씩 배분되는지 분석하십시오.
- **자본 효율성(Capital Efficiency) 검증:** 조달된 자금이 단순 과거 부채 상환이나 비효율적 고정비 유지에 쓰이지 않고, 직접적인 기업가치 상승(Value-up)과 매출/기술 마일스톤 달성에 직결되는지 평가하십시오.

### 6. 자본조달 방법 및 구조 (Financing Structure: 증자·CB·BW·차입 등)
- **최적 조달 수단 검토:** 기업의 현금흐름, 담보력, 리스크 수준을 고려할 때 아래 수단 중 무엇이 투자자와 기업 양쪽에 가장 유리한지 제안하십시오.
  1) **보통주/상환전환우선주(RCPS)/전환우선주(CPS) 유상증자:** 리픽싱(Refixing) 조건, 상환권, 우선청산권(Liquidation Preference) 설계
  2) **메자닌 (CB 전환사채 / BW 신주인수권부사채):** 하방 경직성 확보(원리금 보장 + 전환권/워런트 업사이드), 만기보장수익률(YTM) 및 표면이자율, 콜옵션(Call Option)/풋옵션(Put Option) 비율
  3) **벤처대출(Venture Debt) 및 일반 차입:** 지분 희석을 최소화하기 위한 에쿼티+데트(Equity+Debt) 혼합 조달 가능성
- **딜 구조(Term Sheet) 핵심 특약 제안:** 투자자 보호를 위해 반드시 삽입해야 할 주요 계약 조건(Tag-along, Drag-along, 주요 경영사항 동의권, 경업금지, 마일스톤 분할 납입 등)을 제시하십시오.

---

## [Step 2] 업종 특화 핵심 체크포인트
{industry_specific_instructions}

---

## [Step 3] 최종 투자 의견 (Investment Verdict)
- **투자 매력도 종합 등급:** 강력 추천(A) / 긍정적 검토(B) / 조건부 보류(C) / 투자 부적합(D)
- **핵심 투자 포인트 (Key Investment Highlights):** 3가지 요약
- **핵심 리스크 및 완화 방안 (Key Risks & Mitigation):** 3가지 요약
- **IC 심의 권고 코멘트:** 파트너/심사위원 관점의 결론 제언

---

# 입력 데이터 (기업 정보 및 제출 자료):
- **분석 대상 기업명:** {company_name}
- **산업 분류 기준:** {industry_mapping}
- **기업 제출 데이터 (IR, 재무제표, 사업내용 등):**
{materials_content}
"""

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """PDF 바이트 데이터에서 텍스트를 추출"""
    extracted_text = []
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted_text.append(f"--- [Page {page_idx + 1}] ---\n" + text.strip())
        return "\n\n".join(extracted_text)
    except ImportError:
        try:
            import pypdf2
            reader = pypdf2.PdfReader(io.BytesIO(file_bytes))
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    extracted_text.append(f"--- [Page {page_idx + 1}] ---\n" + text.strip())
            return "\n\n".join(extracted_text)
        except Exception as e:
            logger.warning(f"PDF extraction fallback error: {e}")
            return "[PDF 텍스트 추출 라이브러리 미설치 또는 파싱 실패]"
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return f"[PDF 텍스트 추출 중 오류 발생: {str(e)}]"


def extract_text_from_docx(file_bytes: bytes) -> str:
    """MS Word (.docx) 파일에서 텍스트 및 표 데이터를 추출"""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        parts = []

        # 1. 단락(Paragraphs) 추출
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                parts.append(text)

        # 2. 표(Tables) 데이터 추출
        if doc.tables:
            parts.append("\n[문서 내 표(Table) 데이터 요약]")
            for table_idx, table in enumerate(doc.tables):
                table_lines = []
                for row in table.rows:
                    row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    # 중복 셀(merged cells) 정리
                    dedup_cells = []
                    for c in row_cells:
                        if not dedup_cells or dedup_cells[-1] != c:
                            dedup_cells.append(c)
                    if any(dedup_cells):
                        table_lines.append(" | ".join(dedup_cells))
                if table_lines:
                    parts.append(f"--- 표 {table_idx + 1} ---\n" + "\n".join(table_lines))

        return "\n\n".join(parts)
    except Exception as e:
        logger.error(f"Error extracting text from Word docx: {e}")
        return f"[Word(.docx) 파일 텍스트 추출 중 오류: {str(e)}]"


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    """확장자별(PDF, DOCX, TXT 등) 통합 텍스트 추출 함수"""
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in [".docx"]:
        return extract_text_from_docx(file_bytes)
    elif ext in [".txt", ".csv", ".json", ".md"]:
        for enc in ['utf-8', 'cp949', 'euc-kr', 'latin-1']:
            try:
                return file_bytes.decode(enc)
            except Exception:
                continue
        return file_bytes.decode('utf-8', errors='ignore')
    elif ext == ".doc":
        # 구형 .doc 바이너리 파일: 문자열 검색 추출 시도
        try:
            raw_str = file_bytes.decode('latin-1', errors='ignore')
            import re
            words = re.findall(r'[\w가-힣\s.,!?:;%()/\-]{4,}', raw_str)
            return "\n".join(words[:2000])
        except Exception as e:
            return f"[구형 .doc 파일 파싱 제한 (최신 .docx 파일 저장을 권장합니다): {e}]"
    else:
        try:
            return file_bytes.decode('utf-8', errors='ignore')
        except Exception:
            return f"[{filename}: 지원하지 않는 파일 형식이거나 읽을 수 없습니다]"


def scrape_website_content(url: str, timeout: int = 8) -> str:
    """기업 홈페이지 URL에서 메타데이터 및 주요 텍스트를 크롤링하여 정제"""
    import urllib.request
    import urllib.parse
    import re
    from bs4 import BeautifulSoup

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            html = response.read().decode('utf-8', errors='ignore')

        soup = BeautifulSoup(html, 'html.parser')

        # 불필요한 태그 제거
        for tag in soup(['script', 'style', 'noscript', 'svg', 'header', 'footer', 'nav', 'iframe']):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if desc_tag and desc_tag.get('content'):
            meta_desc = desc_tag['content'].strip()

        # 주요 텍스트 추출 (h1~h4, p, li)
        text_elements = []
        for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li']):
            t = elem.get_text(strip=True)
            if len(t) >= 15:  # 너무 짧은 메뉴 텍스트 제외
                text_elements.append(t)

        combined_text = "\n".join(text_elements)
        # 중복 라인 정리
        lines = []
        seen = set()
        for line in combined_text.split('\n'):
            line_str = line.strip()
            if line_str and line_str not in seen:
                seen.add(line_str)
                lines.append(line_str)

        result_summary = f"[기업 공식 웹사이트 실시간 크롤링 정보: {url}]\n"
        if title:
            result_summary += f"- 사이트 제목: {title}\n"
        if meta_desc:
            result_summary += f"- 사이트 설명: {meta_desc}\n"
        result_summary += "- 주요 소개 및 본문 내용:\n" + "\n".join(lines[:120])  # 최대 120개 핵심 문장

        return result_summary
    except Exception as e:
        logger.warning(f"Failed to scrape website {url}: {e}")
        return f"[기업 웹사이트 크롤링 오류 ({url}): {str(e)}]"


def extract_urls_from_text(text: str) -> list:
    """텍스트 내 포함된 웹사이트 URL 목록 추출"""
    import re
    # http://, https:// 및 www. 형태의 URL 추출
    pattern = r'(https?://[a-zA-Z0-9.\-_~:/?#\[\]@!$&\'()*+,;=%]+|www\.[a-zA-Z0-9.\-_~:/?#\[\]@!$&\'()*+,;=%]+)'
    matches = re.findall(pattern, text)
    cleaned_urls = []
    for m in matches:
        u = m.rstrip('.,!?:;')
        if len(u) > 5 and '.' in u:
            cleaned_urls.append(u)
    return list(dict.fromkeys(cleaned_urls))


def build_ic_memo_prompt(
    company_name: str,
    industry_info: Dict[str, Any],
    materials_content: str
) -> Tuple[str, str]:
    """
    산업분류 및 기업자료를 결합한 마스터 IC Memo 프롬프트 생성
    Returns:
        (prompt_text, major_category)
    """
    major = industry_info.get("major", "기타")
    middle = industry_info.get("middle", "기타/미정")
    minor = industry_info.get("minor", "기타")
    code = industry_info.get("code", "OT-T-01")
    ind_type = industry_info.get("type", "신종 산업" if "-E-" in code else "기존 산업")

    mapping_str = f"{code} | {major} > {ind_type} > {middle} > {minor}"
    specific_inst = INDUSTRY_SPECIFIC_MODULES.get(major, INDUSTRY_SPECIFIC_MODULES["기타"])

    # 텍스트가 너무 길면 LLM 컨텍스트 한도 고려 (최대 100,000자)
    if len(materials_content) > 100000:
        materials_content = materials_content[:100000] + "\n\n[...이하 내용 분량 초과로 축약됨...]"

    final_prompt = MASTER_IC_TEMPLATE.format(
        company_name=company_name,
        industry_mapping=mapping_str,
        industry_specific_instructions=specific_inst,
        materials_content=materials_content if materials_content.strip() else "[제공된 상세 자료 없음 - 기업명 및 공개 정보 기반 추정 분석 실시]"
    )

    return final_prompt, major


def format_financial_history_table(fin_history: list) -> str:
    """3개년 재무 추이 리스트를 가독성 높은 마크다운 표로 변환"""
    if not fin_history or not isinstance(fin_history, list):
        return ""

    lines = [
        "| 결산연도 | 재무기준 | 매출액(억원) | 영업이익(억원) | 영업이익률 | 당기순이익(억원) | 자산총계(억원) | 부채총계(억원) | 자본총계(억원) | 부채비율 |",
        "| :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    def _fmt(v):
        if v is None or v == "":
            return "-"
        try:
            return f"{float(v):,.1f}"
        except Exception:
            return str(v)

    sorted_rows = sorted(fin_history, key=lambda x: str(x.get("year", "")), reverse=True)
    for r in sorted_rows:
        rev = r.get("revenue_krw")
        op = r.get("op_profit_krw")
        ni = r.get("net_income_krw")
        ast = r.get("total_assets_krw")
        liab = r.get("total_liab_krw")
        eq = r.get("total_equity_krw")

        opm_str = "-"
        if rev is not None and op is not None:
            try:
                if float(rev) > 0:
                    opm_str = f"{(float(op) / float(rev)) * 100:.1f}%"
            except Exception:
                pass

        debt_ratio_str = "-"
        if liab is not None and eq is not None:
            try:
                if float(eq) > 0:
                    debt_ratio_str = f"{(float(liab) / float(eq)) * 100:.1f}%"
                elif float(eq) <= 0:
                    debt_ratio_str = "자본잠식"
            except Exception:
                pass

        lines.append(
            f"| {r.get('year', '-')}년 | {r.get('fs_div', '연결')} | {_fmt(rev)} | {_fmt(op)} | {opm_str} | {_fmt(ni)} | {_fmt(ast)} | {_fmt(liab)} | {_fmt(eq)} | {debt_ratio_str} |"
        )
    return "\n".join(lines)


def build_quantitative_ic_memo(
    company_name: str,
    industry_info: Dict[str, Any],
    materials_content: str,
    enrichment_bundle: Optional[Dict[str, Any]] = None,
    ai_status_note: str = "",
) -> str:
    """
    AI 크레딧 소진·오프라인·응답 지연 시에도 깨짐 없이 즉시 제공되는
    DART 공시재무 · 자본변동(RCPS/전환권) · 특허(IP) · 동적 법령/세제 레지스트리 기반 정량 투자심사보고서(IC Memo)
    """
    bundle = enrichment_bundle or {}
    comp = bundle.get("company") or {}
    patents = bundle.get("patents") or []
    registry = bundle.get("registry") or []
    web_info = (bundle.get("website_summary") or "").strip()
    user_note = (bundle.get("user_materials") or "").strip()

    major = industry_info.get("major", "기타")
    middle = industry_info.get("middle", "기타/미정")
    minor = industry_info.get("minor", "기타")
    code = industry_info.get("code", "OT-T-01")
    ind_type = industry_info.get("type", "신종 산업" if "-E-" in code else "기존 산업")
    specific_inst = INDUSTRY_SPECIFIC_MODULES.get(major, INDUSTRY_SPECIFIC_MODULES["기타"])

    fin_hist = comp.get("financial_history") or []
    fin_table = format_financial_history_table(fin_hist)

    # 재무 핵심 지표 계산
    rev = comp.get("revenue_krw")
    op = comp.get("op_profit_krw")
    ni = comp.get("net_income_krw")
    ast = comp.get("total_assets_krw")
    liab = comp.get("total_liab_krw")
    eq = comp.get("total_equity_krw")
    bsns_yr = comp.get("latest_bsns_year") or "최근"

    yoy_comment = "다년도 비교 데이터 확보 시 산출"
    if len(fin_hist) >= 2:
        sorted_fin = sorted(fin_hist, key=lambda x: str(x.get("year", "")), reverse=True)
        r_cur = sorted_fin[0].get("revenue_krw")
        r_prev = sorted_fin[1].get("revenue_krw")
        if r_cur is not None and r_prev is not None:
            try:
                if float(r_prev) > 0:
                    yoy = ((float(r_cur) - float(r_prev)) / float(r_prev)) * 100.0
                    yoy_comment = f"**{yoy:+.1f}%** ({sorted_fin[1].get('year')}년 {float(r_prev):,.1f}억원 → {sorted_fin[0].get('year')}년 {float(r_cur):,.1f}억원)"
            except Exception:
                pass

    opm_comment = "미공시"
    if rev is not None and op is not None:
        try:
            if float(rev) > 0:
                opm_val = (float(op) / float(rev)) * 100.0
                opm_comment = f"**{opm_val:.1f}%** ({'영업흑자 시현' if float(op) >= 0 else '영업적자 구간 - 런웨이 점검 필요'})"
        except Exception:
            pass

    debt_comment = "미공시"
    if liab is not None and eq is not None:
        try:
            if float(eq) > 0:
                dr = (float(liab) / float(eq)) * 100.0
                stability = "매우 우량(100% 미만)" if dr < 100 else ("양호(200% 미만)" if dr < 200 else "레버리지 관리 필요(200% 이상)")
                debt_comment = f"**{dr:.1f}%** — {stability}"
            else:
                debt_comment = "**자본잠식 구간** — 유상증자 또는 전환사채 전환을 통한 자본확충 시급"
        except Exception:
            pass

    # 예비 종합 등급 산출
    score_pts = 65
    if rev is not None and float(rev or 0) >= 100:
        score_pts += 8
    if op is not None and float(op or 0) > 0:
        score_pts += 10
    if eq is not None and liab is not None and float(eq or 0) > 0 and (float(liab or 0) / float(eq)) < 1.5:
        score_pts += 7
    if len(patents) >= 3:
        score_pts += 5

    if score_pts >= 85:
        verdict_label = "긍정적 검토 권고 (A- / 우량 정량지표 보유)"
    elif score_pts >= 72:
        verdict_label = "조건부 긍정 검토 (B+ / 핵심 마일스톤 및 밸류에이션 검증 조건)"
    else:
        verdict_label = "보수적 실사 필요 (B0 / 수익성·재무구조 또는 초기 기술실사 선행 필요)"

    sections = []
    if ai_status_note:
        sections.append(
            f"> 💡 **[안내] DART·특허·세제 실데이터 기반 정량 투자심사보고서 모드**\n"
            f"> - 사유: {ai_status_note}\n"
            f"> - 우측 상단 **`🔑 API 키 관리`**에서 크레딧이 충전된 Gemini API 키 또는 OpenAI API 키(`sk-...`)를 등록하시면 LLM 심층 서술이 추가되며, 상단 **`[완성된 프롬프트 스크립트]`** 탭을 복사하여 외부 AI에서도 즉시 활용하실 수 있습니다."
        )

    sections.append(f"# 📋 투자심사보고서 (IC Memo): {comp.get('corp_name') or company_name}")

    # Step 0
    emp_display = f"{int(comp['employee_count']):,}명" if comp.get("employee_count") else "비공개/확인 필요"
    sections.append(
        "## [Step 0] 기업 개황 및 표준 산업 포지셔닝\n\n"
        "| 구분 | 주요 내용 | 구분 | 주요 내용 |\n"
        "| :--- | :--- | :--- | :--- |\n"
        f"| **분석 대상 법인** | {comp.get('corp_name') or company_name} ({comp.get('corp_cls') or '비상장'}) | **대표이사** | {comp.get('ceo_name') or '확인 필요'} |\n"
        f"| **설립일 / 업력** | {comp.get('est_dt') or '-'} | **사업자등록번호** | {comp.get('biz_reg_no') or '-'} |\n"
        f"| **임직원 수** | {emp_display} | **재무건전성 등급** | **{comp.get('credit_grade') or '산출 대기'}** |\n"
        f"| **표준 산업 분류** | `{code}` {major} > {middle} > **{minor}** | **포지셔닝 구분** | **{ind_type}** |\n"
        f"| **본점 소재지** | {comp.get('address') or '-'} | **공식 홈페이지** | {comp.get('homepage') or '-'} |\n\n"
        f"- **포지셔닝 심사 기준:** 본 기업은 우리 하우스 42개 표준 업종 체계상 **`{major} > {middle} > {minor} ({ind_type})`** 영역에 위치합니다. "
        + (
            "기존 산업군 특성상 **실질 공헌이익·영업현금흐름(OCF)·시장점유율 방어력 및 Take Rate 건전성**을 중심으로 밸류에이션 하방을 검증해야 합니다."
            if "기존" in ind_type
            else "신종 성장 산업군 특성상 **독점적 기술/데이터 해자(Moat), 선점 효과, 고객 유지율(NRR) 및 다음 라운드 리레이팅 마일스톤 달성 가능성**을 핵심 잣대로 심사합니다."
        )
    )

    # Step 1 - 1. Cap Table
    cap_hist = (comp.get("capital_increase_summary") or "").strip()
    cap_md = "### 1. 지분구성 및 자본변동 이력 (Cap Table & Fundraising History)\n"
    if cap_hist:
        cap_lines = "\n".join([f"- {ln.strip()}" for ln in cap_hist.splitlines() if ln.strip()])
        cap_md += (
            "**[DART 전자공시 기준 주요 유상증자 · 전환권 · 주식매수선택권 이력]**\n"
            f"{cap_lines}\n\n"
            "- **심사 체크포인트:** 기발행 상환전환우선주(RCPS)·전환우선주(CPS) 및 스톡옵션 행사 물량에 따른 **잠재 지분 희석률(Fully-Diluted Share Count)**과 기존 FI의 상환권·청산우선권 만기 도래(오버행 이슈)를 주주명부 원본 대조로 확정해야 합니다."
        )
    else:
        cap_md += (
            "- DART 정기공시상 최근 증자·전환 세부 내역이 조회되지 않는 초기/비외감 구간이거나 보통주 중심 구조입니다.\n"
            "- **필수 실사 요청자료:** 최신 주주명부(Fully-Diluted 기준), 기발행 RCPS/CB/BW 투자계약서(리픽싱 하한 및 동반매도청구권 조항), 잔여 스톡옵션 부여 현황표."
        )

    # Step 1 - 2. 시장 및 사업 모델
    biz_summary_blocks = []
    if user_note:
        biz_summary_blocks.append(f"- **입력된 기업/딜 요약:** {user_note[:600]}")
    if web_info:
        clean_web_lines = [ln.strip() for ln in web_info.splitlines() if ln.strip() and not ln.startswith("[기업 공식 웹사이트")][:6]
        if clean_web_lines:
            biz_summary_blocks.append("- **공식 채널 확인 사업 내용:**\n  " + "\n  ".join(clean_web_lines))
    if not biz_summary_blocks:
        biz_summary_blocks.append(f"- `{minor}` 도메인 내 핵심 제품/플랫폼 단가(ARPU) 및 유효 타깃 고객군 기반의 Bottom-up 유효시장(SOM) 산정이 필요합니다.")

    market_md = (
        "### 2. 시장 분석 및 사업 모델 진단 (Market & Business Model)\n"
        + "\n".join(biz_summary_blocks)
        + "\n- **시장 확장성 및 진입장벽 점검:** ① 고객 전환비용(Switching Cost) 및 네트워크 효과 존재 여부, ② 크로스보더(글로벌) 또는 인접 B2B/SaaS 수익모델 확장 시 한계비용 구조, ③ 플랫폼/규제 환경 변화에 따른 수수료율·원가율 방어력을 중점 점검합니다."
    )

    # Step 1 - 3. 3개년 재무
    fin_md = f"### 3. 재무 실적 및 건전성 정량 분석 ({comp.get('data_source') or 'DART'} 기준)\n"
    if fin_table:
        fin_md += (
            f"{fin_table}\n\n"
            f"- **외형 성장성 (YoY):** {yoy_comment}\n"
            f"- **수익성 진단 ({bsns_yr}년 영업이익률):** {opm_comment}\n"
            f"- **재무 안정성 (부채비율):** {debt_comment}\n"
        )
    elif rev is not None or ast is not None:
        fin_md += (
            f"- **{bsns_yr}년 요약 실적:** 매출액 {rev if rev is not None else '-'}억원 | 영업이익 {op if op is not None else '-'}억원 | "
            f"당기순이익 {ni if ni is not None else '-'}억원 | 자산총계 {ast if ast is not None else '-'}억원 | 자본총계 {eq if eq is not None else '-'}억원\n"
            f"- **수익성 및 건전성:** 영업이익률 {opm_comment} / 부채비율 {debt_comment}\n"
        )
    else:
        fin_md += (
            "- 현재 DART 외부감사 재무제표 공시 이전 단계이거나 비외감 법인입니다.\n"
            "- **실사 필수 징구:** 최근 3개년 표준재무제표증명원(국세청 홈택스), 월별 관리회계 손익계산서(Burn Rate 및 공헌이익 확인용), 부가가치세 과세표준증명원.\n"
        )

    # Step 1 - 4. 기술력 & 특허(IP)
    ip_md = "### 4. 기술력 · 특허(IP) 해자 및 경영진 역량\n"
    if patents:
        ip_rows = [
            "| 출원/등록일 | 특허(발명) 명칭 | 상태 | 출원/등록번호 | 출처 |",
            "| :---: | :--- | :---: | :---: | :---: |",
        ]
        for p in patents[:8]:
            ip_rows.append(
                f"| {p.get('application_date') or '-'} | {p.get('invention_title') or '-'} | **{p.get('registration_status') or '공개'}** | `{p.get('application_number') or '-'}` | {p.get('source_name') or '특허DB'} |"
            )
        ip_md += (
            "\n".join(ip_rows)
            + f"\n\n- **IP 포트폴리오 진단:** 총 **{len(patents)}건**의 핵심 특허/출원 시그널이 확인됩니다. 핵심 매출 제품과 등록 특허 청구항 간의 직접적 매칭 여부 및 대표이사·핵심 연구인력의 직무발명보상 승계 완료 여부를 법률 실사에서 확인하십시오."
        )
    else:
        ip_md += (
            "- 조회된 공개 국내 특허 시그널이 제한적이므로 영업비밀·독점 데이터셋·소프트웨어 파이프라인 또는 브랜드/네트워크 해자 중심의 경쟁우위 검증이 필요합니다.\n"
            f"- **경영진/조직 점검:** 대표이사({comp.get('ceo_name') or '창업자'}) 및 C-Level 핵심 인력의 도메인 경력, 임직원({comp.get('employee_count') or '미공시'}명) 인당 생산성 및 핵심 인력 이탈 방지(Lock-up) 조항을 점검하십시오."
        )

    # Step 1 - 5. 프라이싱 & 밸류에이션
    pricing_md = "### 5. 프라이싱(밸류에이션) 적정성 및 자금 용도 가이드\n"
    if rev is not None and float(rev or 0) > 0:
        r_f = float(rev)
        op_f = float(op) if op is not None else 0.0
        if op_f > 0:
            pricing_md += (
                f"- **실적 기반 밸류에이션 기준점:** {bsns_yr}년 매출액 **{r_f:,.1f}억원**, 영업이익 **{op_f:,.1f}억원** 시현 기업으로, 단순 PSR 외에 동종 피어그룹 **EV/EBITDA 및 PER 멀티플 교차 검증**이 가능합니다.\n"
                f"  - 참고 시뮬레이션 (Peer PSR 1.5x ~ 3.0x 가정 시): 내재 영업가치 약 **{r_f * 1.5:,.0f}억원 ~ {r_f * 3.0:,.0f}억원** 밴드 (순차입금 가감 및 성장률 프리미엄 별도 반영, 좌측 사이드바 `📊 밸류에이션 계산기`에서 정밀 산출 권장).\n"
            )
        else:
            pricing_md += (
                f"- **성장 단계 밸류에이션 기준점:** {bsns_yr}년 매출액 **{r_f:,.1f}억원**(영업손익 {op_f:,.1f}억원) 구간으로, 매출 총이익률(Gross Margin) 및 YoY 성장률로 보정한 **EV/Sales(PSR) 및 공헌이익 전환 시점 DCF** 병행 검증이 적합합니다.\n"
            )
    else:
        pricing_md += "- **초기/비공개 실적 밸류에이션:** 마일스톤 기반 스코어카드법·VC Method(목표 Exit 가치 할인) 및 동종 라운드 거래 사례 비교법을 결합하여 Pre-money 기업가치를 산정하십시오.\n"
    pricing_md += "- **자금 용도(Use of Proceeds) 심사 원칙:** 신규 조달 자금이 기존 고금리 차입금 단순 상환이나 비효율적 마케팅 소진(Burn)이 아닌 **R&D·핵심 인재 확보·글로벌/B2B 매출 직결 CAPEX**에 최소 70% 이상 배분되는지 투자계약서상 자금사용 협의권으로 통제해야 합니다."

    # Step 1 - 6. 자본조달 구조 & 동적 법령/세제 레지스트리
    struct_md = "### 6. 최적 자본조달 구조 및 현행 벤처투자 법령·세제 검토\n"
    if op is not None and float(op or 0) > 0:
        struct_md += "- **권고 딜 구조:** 영업흑자 창출력이 확인되므로 하방 보호와 업사이드를 겸비한 **상환전환우선주(RCPS)** 또는 **전환사채(CB) / 교환사채(EB)** 구조 모두 설계 가능하며, IPO 가시성에 따른 Refixing 및 동반매도참여권(Tag-along) 확보를 권고합니다.\n"
    else:
        struct_md += "- **권고 딜 구조:** 손익분기점(BEP) 도달 전 또는 성장 투자 구간이므로 **리픽싱(Refixing 70% 하한 등) 및 우선청산권(Liquidation Preference 1x Participating 등)이 부여된 RCPS** 또는 **마일스톤 분할 납입(Tranche) 조건부 투자**가 투자자 하방 경직성 확보에 유리합니다.\n"

    if registry:
        reg_table = [
            "\n**[동적 설정 레지스트리(`DynamicConfigRegistry`) 연동 — 현행 벤처투자 법령·세제 기준]**",
            "| 제도/규제 항목 | 현행 기준값 | 근거 법령 및 비고 |",
            "| :--- | :---: | :--- |",
        ]
        for r in registry[:8]:
            reg_table.append(
                f"| {r.get('config_label', '-')} | **{r.get('config_value', '')}{r.get('unit', '')}** | {r.get('legal_basis', '-')} |"
            )
        struct_md += "\n".join(reg_table)

    sections.append("## [Step 1] 6대 핵심 투자심사 분석\n\n" + "\n\n".join([cap_md, market_md, fin_md, ip_md, pricing_md, struct_md]))

    # Step 2
    sections.append(f"## [Step 2] 업종 특화 핵심 심사 체크포인트 ({major})\n\n{specific_inst}")

    # Step 3
    sections.append(
        "## [Step 3] 예비 투자 심사 의견 (Preliminary IC Verdict)\n\n"
        f"- **정량 지표 종합 예비 등급:** **{verdict_label}**\n"
        "- **핵심 투자 포인트 (Key Highlights):**\n"
        f"  1. 공인 기업데이터({comp.get('data_source') or 'DART'}) 및 업종 분류(`{code}`) 기준 외형·재무 구조의 객관적 검증 기반 확보\n"
        f"  2. `{major} > {minor}` 도메인 내 사업 확장성 및 자본시장 조달 이력 보유\n"
        "  3. 벤처투자조합 의무투자 비율 및 세제 혜택 요건과의 부합성 검토 가능\n"
        "- **IC 상정 전 필수 확인 리스크 (Key DD Questions):**\n"
        "  1. 기발행 우선주(RCPS/CPS)·전환사채·스톡옵션 전량 전환 가정 시 창업자 유효 지분율 및 오버행 물량은 적정한가?\n"
        "  2. 일회성 수익을 제거한 핵심 사업부의 공헌이익률(Contribution Margin)과 순매출유지율(NRR) 추이는 어떠한가?\n"
        "  3. 피어그룹 최근 멀티플 대비 요구 Pre-money 밸류에이션의 할인율(Safety Margin)이 충분히 확보되었는가?"
    )

    return "\n\n---\n\n".join(sections)


async def generate_ic_memo(
    company_name: str,
    industry_info: Dict[str, Any],
    materials_content: str,
    api_key: Optional[str] = None,
    enrichment_bundle: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Gemini 또는 OpenAI 모델을 호출하여 심층 IC Memo 리포트 생성.
    크레딧 소진(402/429) 또는 API 장애 시 깨진 에러 문자열 대신 실데이터 정량 IC Memo를 즉시 반환.
    """
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(dotenv_path=env_path, override=True)

    prompt, major = build_ic_memo_prompt(company_name, industry_info, materials_content)

    key = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return build_quantitative_ic_memo(
            company_name=company_name,
            industry_info=industry_info,
            materials_content=materials_content,
            enrichment_bundle=enrichment_bundle,
            ai_status_note="AI API 키(`GEMINI_API_KEY` 또는 `OPENAI_API_KEY`)가 아직 설정되지 않았습니다.",
        )

    # 1. OpenAI 호환 키(sk-...) 자동 지원
    openai_key = key if key.startswith("sk-") else (os.getenv("OPENAI_API_KEY") or "").strip()
    if openai_key.startswith("sk-"):
        try:
            import requests
            r_oa = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "당신은 글로벌 Top-Tier 벤처캐피탈 수석 투자심사역입니다."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                },
                timeout=60,
            )
            if r_oa.status_code == 200:
                choices = r_oa.json().get("choices", [])
                if choices and choices[0].get("message", {}).get("content"):
                    return choices[0]["message"]["content"]
        except Exception as oa_err:
            logger.warning(f"OpenAI fallback attempt warning: {oa_err}")

    # 2. Gemini 현행 지원 모델 호출
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)

        model_candidates = [
            "gemini-3.8-flash",
            "gemini-flash-latest",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
        ]

        credit_depleted = False
        invalid_key = False
        last_error = None

        for model_name in model_candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and getattr(response, "text", None):
                    return response.text
            except Exception as e:
                err_str = str(e)
                last_error = err_str
                logger.warning(f"Model {model_name} failed: {err_str}, trying next...")
                if "prepayment credits are depleted" in err_str.lower() or "402" in err_str or "quota" in err_str.lower() or "429" in err_str:
                    credit_depleted = True
                    break  # 계정 단위 크레딧 소진이므로 불필요한 재시도 즉시 중단
                if "api key not valid" in err_str.lower() or "400" in err_str or "403" in err_str:
                    invalid_key = True
                    break

        if credit_depleted:
            reason_msg = "현재 등록된 Google AI Studio 프로젝트의 선불 크레딧(Prepayment Credits) 또는 호출 한도가 소진되었습니다."
        elif invalid_key:
            reason_msg = "현재 등록된 Gemini API 키가 유효하지 않거나 권한이 없습니다."
        else:
            reason_msg = f"AI 모델 응답 지연 또는 일시적 제한 ({str(last_error)[:120]})"

        return build_quantitative_ic_memo(
            company_name=company_name,
            industry_info=industry_info,
            materials_content=materials_content,
            enrichment_bundle=enrichment_bundle,
            ai_status_note=reason_msg,
        )

    except Exception as e:
        logger.error(f"Error calling Gemini for IC Memo: {e}")
        return build_quantitative_ic_memo(
            company_name=company_name,
            industry_info=industry_info,
            materials_content=materials_content,
            enrichment_bundle=enrichment_bundle,
            ai_status_note=f"AI 엔진 연결 중 예외가 발생하여 정량 심사 모드로 자동 전환되었습니다 ({str(e)[:100]}).",
        )
