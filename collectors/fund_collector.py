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

def fetch_diva_funds(page_index: int = 1, page_unit: int = 500, gp_keyword: str = "", fund_keyword: str = "", motae_only: bool = False):
    """
    DIVA(한국벤처캐피탈협회 전자공시) 조합결성현황 실시간 조회
    - 회사명(운용사 GP), 조합명, 등록일(결성일), 결성총액(억원), 만기일, 투자분야, 목적구분, 지원구분, 모태펀드 출자여부 수집
    - DIVA 유효 정렬코드(EXP_DD: 만기일 내림차순) 및 대량 페이지 유닛을 적용하여 가나다순 절단 누락 방지
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
        "S_ORDER_BAS_TP_CD": "EXP_DD",  # DIVA 유효 정렬코드: 만기일 기준 내림차순
        "S_ORDER_BY_TP_CD": "DESC",
    }

    resp = requests.post(DIVA_URL, headers=headers, data=payload, timeout=30)
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

    # 등록일(reg_date) 내림차순으로 정렬하여 최신 결성 펀드가 최우선 배치되도록 보장
    funds.sort(key=lambda x: x.get("reg_date") or "", reverse=True)
    return funds

def sync_diva_funds_to_db(session, pages: int = 1, gp_keyword: str = "", fund_keyword: str = "", page_unit: int = 3000):
    """DIVA 전체 최신 조합 결성 데이터 및 모태출자 조합을 DB에 초고속 일괄 Upsert"""
    from database.models import VentureFund

    collected = []
    # 전체 조합(약 2,580건)을 한 번에 가져와 가나다순/만기일순 누락 없이 최근 결성분(9월 말 공시분까지) 전수 확보
    for p in range(1, max(1, pages) + 1):
        batch = fetch_diva_funds(page_index=p, page_unit=page_unit, gp_keyword=gp_keyword, fund_keyword=fund_keyword, motae_only=False)
        collected.extend(batch)
        if len(batch) < page_unit:
            break

    # 모태펀드 출자 조합(COND_MFUND_INVST_YN='Y') 플래그 보강
    if not gp_keyword and not fund_keyword:
        motae_batch = fetch_diva_funds(page_index=1, page_unit=1500, motae_only=True)
        collected.extend(motae_batch)

    existing_map = {r.asct_id: r for r in session.query(VentureFund).all()}

    added = 0
    updated = 0
    for item in collected:
        aid = item["asct_id"]
        existing = existing_map.get(aid)
        if existing:
            existing.reg_date = item["reg_date"] or existing.reg_date
            existing.commitment_krw = item["commitment_krw"]
            existing.maturity_date = item["maturity_date"]
            if item["motae_backed"]:
                existing.motae_backed = True
            updated += 1
        else:
            new_obj = VentureFund(**item)
            session.add(new_obj)
            existing_map[aid] = new_obj
            added += 1

    session.commit()
    latest_reg = max((item.get("reg_date") or "" for item in collected), default="")
    return {"added": added, "updated": updated, "total_fetched": len(collected), "latest_reg_date": latest_reg}

