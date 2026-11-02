"""
벤처펀드 결성·운용 현황 수집기 (한국벤처캐피탈협회 전자공시 DIVA 실시간 연동)
"""
import re
import hashlib
import requests
from bs4 import BeautifulSoup

DIVA_URL = "http://diva.kvca.or.kr/div/dii/DivItmAssoInq"

def _parse_krw_to_eok(raw_str: str):
    if not raw_str:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(raw_str))
    if not cleaned:
        return None
    try:
        return round(float(cleaned) / 100_000_000.0, 1)
    except ValueError:
        return None

def fetch_diva_funds(page_index: int = 1, page_unit: int = 40, gp_keyword: str = "", fund_keyword: str = "", motae_only: bool = False):
    """
    DIVA(한국벤처캐피탈협회 전자공시) 조합결성현황 실시간 조회
    - 회사명(운용사 GP), 조합명, 등록일(결성일), 결성총액(억원), 만기일, 투자분야, 목적구분, 지원구분, 모태펀드 출자여부 수집
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": DIVA_URL
    }
    payload = {
        "PAGE_INDEX": str(page_index),
        "PAGE_UNIT": str(page_unit),
        "S_OPER_INST_NM": gp_keyword.strip(),
        "S_ASCT_NM": fund_keyword.strip(),
        "COND_OPER_INST_NM": gp_keyword.strip(),
        "COND_ASCT_NM": fund_keyword.strip(),
        "COND_MFUND_INVST_YN": "Y" if motae_only else "",
        "S_ORDER_BAS_TP_CD": "1",  # 등록일 기준 정렬 시도
        "S_ORDER_BY_TP_CD": "DESC",
    }

    resp = requests.post(DIVA_URL, headers=headers, data=payload, timeout=15)
    resp.encoding = "utf-8"
    if resp.status_code != 200:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table tbody tr")
    funds = []

    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 8:
            continue
        gp_name = tds[1].get_text(" ", strip=True)
        raw_fund_name = tds[2].get_text(" ", strip=True)
        if not gp_name or "조회된" in gp_name or "데이터가" in gp_name:
            continue

        # DIVA에서 조합명 뒤 '*' 표시는 모태펀드 출자 조합을 의미하는 관례 반영 + motae_only 플래그 반영
        has_star = "*" in raw_fund_name
        clean_fund_name = raw_fund_name.replace("*", "").strip()
        reg_date = tds[3].get_text(" ", strip=True)
        commitment_eok = _parse_krw_to_eok(tds[4].get_text(" ", strip=True))
        maturity_date = tds[5].get_text(" ", strip=True)
        invest_field = tds[6].get_text(" ", strip=True)
        purpose_type = tds[7].get_text(" ", strip=True)
        support_type = tds[8].get_text(" ", strip=True) if len(tds) > 8 else ""

        # 숨겨진 input ASCT_ID 추출 또는 고유 해시 생성
        asct_input = tr.find("input", {"name": "ASCT_ID"})
        asct_id = asct_input.get("value", "").strip() if asct_input else ""
        if not asct_id:
            uid_src = f"{gp_name}|{clean_fund_name}|{reg_date}"
            asct_id = "DIVA_" + hashlib.md5(uid_src.encode("utf-8")).hexdigest()[:12]

        is_motae = bool(motae_only or has_star or ("모태" in clean_fund_name) or ("초격차" in clean_fund_name) or ("창업초기" in support_type))

        funds.append({
            "asct_id": asct_id,
            "fund_name": clean_fund_name,
            "gp_name": gp_name,
            "reg_date": reg_date,
            "maturity_date": maturity_date,
            "commitment_krw": commitment_eok,
            "invest_field": invest_field,
            "purpose_type": purpose_type,
            "support_type": support_type,
            "motae_backed": is_motae,
            "source_name": "DIVA 전자공시 (KVCA)",
            "source_url": DIVA_URL
        })

    return funds

def sync_diva_funds_to_db(session, pages: int = 2, gp_keyword: str = "", fund_keyword: str = ""):
    """DIVA 최신 조합 결성 데이터 및 모태출자 조합을 DB에 Upsert"""
    from database.models import VentureFund

    collected = []
    for p in range(1, pages + 1):
        collected.extend(fetch_diva_funds(page_index=p, page_unit=40, gp_keyword=gp_keyword, fund_keyword=fund_keyword, motae_only=False))
    # 모태펀드 출자 조합 전용 1페이지 추가 수집하여 정책 펀드 커버리지 강화
    if not gp_keyword and not fund_keyword:
        collected.extend(fetch_diva_funds(page_index=1, page_unit=30, motae_only=True))

    added = 0
    updated = 0
    for item in collected:
        existing = session.query(VentureFund).filter_by(asct_id=item["asct_id"]).first()
        if existing:
            existing.commitment_krw = item["commitment_krw"]
            existing.maturity_date = item["maturity_date"]
            if item["motae_backed"]:
                existing.motae_backed = True
            updated += 1
        else:
            session.add(VentureFund(**item))
            added += 1

    session.commit()
    return {"added": added, "updated": updated, "total_fetched": len(collected)}

