"""
기업·재무 인텔리전스 수집기 (DART OpenAPI + 공공데이터포털 금융위/국민연금 + NICE 업로드 하이브리드)
"""
import os
import io
import re
import json
import zipfile
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
CORP_CODE_CACHE = os.path.join(DATA_DIR, "dart_corp_codes.json")

CORP_CLS_MAP = {
    "Y": "유가증권(KOSPI)",
    "K": "코스닥(KOSDAQ)",
    "N": "코넥스(KONEX)",
    "E": "비상장(외감/기타)"
}

def _load_keys():
    load_dotenv(os.path.join(ROOT_DIR, ".env"), override=True)
    return {
        "dart_key": os.getenv("DART_API_KEY", "").strip(),
        "data_go_kr_key": os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip(),
        "nice_api_key": os.getenv("NICE_API_KEY", "").strip(),
    }

def ensure_dart_corp_codes(force_refresh=False):
    """DART 전체 법인 고유번호(corpCode.xml) 다운로드 및 로컬 JSON 캐싱 (상장 + 비상장 외감 포함 약 10만여 법인)"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(CORP_CODE_CACHE) and not force_refresh:
        try:
            with open(CORP_CODE_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    keys = _load_keys()
    dart_key = keys["dart_key"]
    if not dart_key:
        return []

    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    resp = requests.get(url, params={"crtfc_key": dart_key}, timeout=30)
    if resp.status_code != 200 or not resp.content.startswith(b"PK"):
        return []

    items = []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_name = zf.namelist()[0]
        xml_bytes = zf.read(xml_name)
        root = ET.fromstring(xml_bytes)
        for el in root.findall("list"):
            corp_code = (el.findtext("corp_code") or "").strip()
            corp_name = (el.findtext("corp_name") or "").strip()
            stock_code = (el.findtext("stock_code") or "").strip()
            modify_date = (el.findtext("modify_date") or "").strip()
            if corp_code and corp_name:
                items.append({
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code,
                    "modify_date": modify_date
                })

    with open(CORP_CODE_CACHE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    return items

def search_dart_candidates(query: str, limit: int = 15):
    """기업명으로 DART 고유번호 목록에서 후보 검색 (정확일치 -> 전방일치 -> 부분일치 우선순위)"""
    q = (query or "").strip()
    if not q:
        return []
    q_norm = re.sub(r"\(주\)|주식회사|\s+", "", q).lower()
    corps = ensure_dart_corp_codes()
    exact, prefix, partial = [], [], []

    for c in corps:
        cname = c["corp_name"]
        cnorm = re.sub(r"\(주\)|주식회사|\s+", "", cname).lower()
        if cnorm == q_norm:
            exact.append(c)
        elif cnorm.startswith(q_norm):
            prefix.append(c)
        elif q_norm in cnorm:
            partial.append(c)

    # 최근 공시 갱신일 내림차순 정렬
    exact.sort(key=lambda x: x.get("modify_date", ""), reverse=True)
    prefix.sort(key=lambda x: (0 if x.get("stock_code") else 1, x.get("modify_date", "")), reverse=False)
    partial.sort(key=lambda x: x.get("modify_date", ""), reverse=True)
    return (exact + prefix + partial)[:limit]

def _parse_amount_to_eok(val_str):
    """원(KRW) 문자열을 억원(float) 단위로 변환"""
    if val_str is None:
        return None
    cleaned = str(val_str).replace(",", "").strip()
    if not cleaned or cleaned == "-":
        return None
    try:
        return round(float(cleaned) / 100_000_000.0, 2)
    except ValueError:
        return None

def _estimate_financial_grade(rev_eok, op_eok, assets_eok, liab_eok, equity_eok):
    """NICE 미연동 시 재무지표(자본잠식·부채비율·영업이익률·외형) 기반 재무건전성 등급 산출"""
    if equity_eok is None and rev_eok is None:
        return "재무미공시(비외감/초기)"
    if equity_eok is not None and equity_eok <= 0:
        return "주의 (자본잠식)"
    debt_ratio = (liab_eok / equity_eok * 100.0) if (liab_eok is not None and equity_eok and equity_eok > 0) else 100.0
    op_margin = (op_eok / rev_eok * 100.0) if (op_eok is not None and rev_eok and rev_eok > 0) else 0.0

    score = 60
    if rev_eok and rev_eok >= 500:
        score += 15
    elif rev_eok and rev_eok >= 100:
        score += 10
    elif rev_eok and rev_eok >= 30:
        score += 5

    if op_eok is not None and op_eok > 0:
        score += 15 if op_margin >= 10 else 10
    elif op_eok is not None and op_eok < 0:
        score -= 10

    if debt_ratio < 100:
        score += 10
    elif debt_ratio > 250:
        score -= 12

    if score >= 85:
        return "A+ (우량·재무추정)"
    elif score >= 75:
        return "A0 (양호·재무추정)"
    elif score >= 65:
        return "BBB+ (보통·성장기)"
    elif score >= 52:
        return "BB0 (투자기·적자관리)"
    return "B (초기·런웨이점검)"

def fetch_dart_company_detail(corp_code: str):
    """DART 기업개황 + 최근 3개년 요약재무 + 유상증자(RCPS/CPS 등) + 임직원 현황 통합 조회"""
    keys = _load_keys()
    dart_key = keys["dart_key"]
    if not dart_key or not corp_code:
        return None

    # 1. 기업개황 (company.json)
    r_info = requests.get(
        "https://opendart.fss.or.kr/api/company.json",
        params={"crtfc_key": dart_key, "corp_code": corp_code},
        timeout=12
    ).json()

    if r_info.get("status") != "000":
        return None

    est_raw = r_info.get("est_dt") or ""
    est_dt = f"{est_raw[:4]}-{est_raw[4:6]}-{est_raw[6:8]}" if len(est_raw) == 8 else est_raw
    bizr_raw = r_info.get("bizr_no") or ""
    biz_reg_no = f"{bizr_raw[:3]}-{bizr_raw[3:5]}-{bizr_raw[5:]}" if len(bizr_raw) == 10 else bizr_raw
    jurir_raw = r_info.get("jurir_no") or ""
    corp_reg_no = f"{jurir_raw[:6]}-{jurir_raw[6:]}" if len(jurir_raw) == 13 else jurir_raw
    hm_url = (r_info.get("hm_url") or "").strip()
    if hm_url and not hm_url.startswith("http"):
        hm_url = "https://" + hm_url

    # 2. 최근 결산 재무제표 탐색 (최신 가용 사업연도부터 최대 3개년)
    now_year = datetime.now().year
    candidate_years = [str(y) for y in range(min(now_year - 1, 2025), 2020, -1)]
    fin_history = []

    for yr in candidate_years:
        if len(fin_history) >= 3:
            break
        try:
            r_fin = requests.get(
                "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json",
                params={"crtfc_key": dart_key, "corp_code": corp_code, "bsns_year": yr, "reprt_code": "11011"},
                timeout=10
            ).json()
            if r_fin.get("status") != "000" or not r_fin.get("list"):
                continue

            # 연결재무제표(CFS) 우선, 없으면 개별재무제표(OFS)
            rows = r_fin["list"]
            cfs_rows = [x for x in rows if x.get("fs_div") == "CFS"]
            use_rows = cfs_rows if cfs_rows else rows

            yr_map = {"year": yr, "fs_div": "연결" if cfs_rows else "개별"}
            for row in use_rows:
                acct = (row.get("account_nm") or "").strip()
                amt = _parse_amount_to_eok(row.get("thstrm_amount"))
                if acct in ("매출액", "수익(매출액)", "영업수익") and "revenue_krw" not in yr_map:
                    yr_map["revenue_krw"] = amt
                elif acct in ("영업이익", "영업이익(손실)") and "op_profit_krw" not in yr_map:
                    yr_map["op_profit_krw"] = amt
                elif acct in ("당기순이익", "당기순이익(손실)") and "net_income_krw" not in yr_map:
                    yr_map["net_income_krw"] = amt
                elif acct == "자산총계" and "total_assets_krw" not in yr_map:
                    yr_map["total_assets_krw"] = amt
                elif acct == "부채총계" and "total_liab_krw" not in yr_map:
                    yr_map["total_liab_krw"] = amt
                elif acct == "자본총계" and "total_equity_krw" not in yr_map:
                    yr_map["total_equity_krw"] = amt
            fin_history.append(yr_map)
        except Exception:
            continue

    latest_fin = fin_history[0] if fin_history else {}

    # 3. 임직원 현황 및 유상증자(RCPS/CPS/보통주) 내역 조회 (최근 결산연도 기준)
    emp_count = None
    avg_salary_manwon = None
    cap_summary_parts = []
    check_yr = latest_fin.get("year") or "2024"

    try:
        r_emp = requests.get(
            "https://opendart.fss.or.kr/api/empSttus.json",
            params={"crtfc_key": dart_key, "corp_code": corp_code, "bsns_year": check_yr, "reprt_code": "11011"},
            timeout=8
        ).json()
        if r_emp.get("status") == "000" and r_emp.get("list"):
            total_emp = 0
            salaries = []
            for erow in r_emp["list"]:
                if "합계" in (erow.get("fo_bbm") or "") or erow.get("sexdstn") in ("남", "여"):
                    cnt_str = str(erow.get("sm") or "0").replace(",", "").strip()
                    if cnt_str.isdigit():
                        total_emp += int(cnt_str)
                    sal_str = str(erow.get("jan_salary_am") or "0").replace(",", "").strip()
                    if sal_str.isdigit() and int(sal_str) > 0:
                        salaries.append(int(sal_str) / 10_000.0)
            if total_emp > 0:
                emp_count = total_emp
            if salaries:
                avg_salary_manwon = round(sum(salaries) / len(salaries), 0)
    except Exception:
        pass

    try:
        r_irds = requests.get(
            "https://opendart.fss.or.kr/api/irdsSttus.json",
            params={"crtfc_key": dart_key, "corp_code": corp_code, "bsns_year": check_yr, "reprt_code": "11011"},
            timeout=8
        ).json()
        if r_irds.get("status") == "000" and r_irds.get("list"):
            for irow in r_irds["list"][:5]:
                dt = irow.get("isu_dcrs_de") or ""
                st = irow.get("isu_dcrs_stle") or ""
                knd = irow.get("isu_dcrs_stock_knd") or ""
                qy = irow.get("isu_dcrs_qy") or ""
                val = irow.get("isu_dcrs_mstvdv_fval_amount") or ""
                if dt and dt != "-":
                    cap_summary_parts.append(f"[{dt}] {st} ({knd}, 수량: {qy}, 주당가액: {val}원)")
    except Exception:
        pass

    # 4. 공공데이터포털 금융위 기업기본정보 폴백/보강 (키 등록 시)
    data_sources = ["DART 전자공시"]
    fsc_data = _try_fsc_corp_outline(r_info.get("corp_name", ""), keys["data_go_kr_key"])
    if fsc_data:
        data_sources.append("금융위 기업정보API")
        if not emp_count and fsc_data.get("enpEmpeCnt"):
            try:
                emp_count = int(str(fsc_data["enpEmpeCnt"]).replace(",", ""))
            except Exception:
                pass

    credit_grade = _estimate_financial_grade(
        latest_fin.get("revenue_krw"),
        latest_fin.get("op_profit_krw"),
        latest_fin.get("total_assets_krw"),
        latest_fin.get("total_liab_krw"),
        latest_fin.get("total_equity_krw")
    )

    return {
        "corp_name": r_info.get("corp_name") or "",
        "corp_code": corp_code,
        "biz_reg_no": biz_reg_no,
        "corp_reg_no": corp_reg_no,
        "stock_code": (r_info.get("stock_code") or "").strip(),
        "corp_cls": CORP_CLS_MAP.get(r_info.get("corp_cls", "E"), "비상장"),
        "ceo_name": r_info.get("ceo_nm") or "",
        "est_dt": est_dt,
        "industry_code": r_info.get("induty_code") or "",
        "address": r_info.get("adres") or "",
        "homepage_url": hm_url,
        "employee_count": emp_count,
        "avg_salary_est_krw": avg_salary_manwon,
        "credit_grade": credit_grade,
        "latest_bsns_year": latest_fin.get("year"),
        "revenue_krw": latest_fin.get("revenue_krw"),
        "op_profit_krw": latest_fin.get("op_profit_krw"),
        "net_income_krw": latest_fin.get("net_income_krw"),
        "total_assets_krw": latest_fin.get("total_assets_krw"),
        "total_liab_krw": latest_fin.get("total_liab_krw"),
        "total_equity_krw": latest_fin.get("total_equity_krw"),
        "capital_increase_summary": "\n".join(cap_summary_parts) if cap_summary_parts else None,
        "financial_history_json": json.dumps(fin_history, ensure_ascii=False),
        "data_source": " + ".join(data_sources)
    }

def _try_fsc_corp_outline(corp_name: str, service_key: str):
    """공공데이터포털 금융위원회 기업기본정보 V2 (활용신청 완료된 경우 자동 보강)"""
    if not service_key or not corp_name:
        return None
    try:
        decoded = urllib.parse.unquote(service_key)
        encoded = urllib.parse.quote(decoded)
        url = (
            f"https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline_V2"
            f"?serviceKey={encoded}&pageNo=1&numOfRows=1&resultType=json&corpNm={urllib.parse.quote(corp_name)}"
        )
        r = requests.get(url, timeout=6)
        if r.status_code == 200 and "response" in r.text:
            items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
            if isinstance(items, list) and items:
                return items[0]
            if isinstance(items, dict):
                return items
    except Exception:
        pass
    return None

def parse_uploaded_company_report(filename: str, file_bytes: bytes, fallback_name: str = ""):
    """NICE 비즈인포 / 크레딧뷰 / 재무 엑셀·CSV·PDF 업로드 파일에서 핵심 기업·재무·신용정보 파싱"""
    lower = (filename or "").lower()
    records = []

    if lower.endswith(".csv"):
        import csv
        text_data = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text_data))
        for row in reader:
            name = row.get("기업명") or row.get("회사명") or row.get("corp_name") or fallback_name
            if not name:
                continue
            def _f(keys_list):
                for k in keys_list:
                    if k in row and row[k]:
                        try:
                            return float(str(row[k]).replace(",", "").strip())
                        except Exception:
                            pass
                return None
            records.append({
                "corp_name": name.strip(),
                "biz_reg_no": (row.get("사업자번호") or row.get("사업자등록번호") or "").strip(),
                "ceo_name": (row.get("대표자") or row.get("대표이사") or "").strip(),
                "credit_grade": (row.get("신용등급") or row.get("NICE등급") or row.get("credit_grade") or "NICE 업로드").strip(),
                "venture_cert_type": (row.get("벤처유형") or row.get("벤처확인") or "").strip(),
                "revenue_krw": _f(["매출액(억)", "매출액", "revenue_krw"]),
                "op_profit_krw": _f(["영업이익(억)", "영업이익", "op_profit_krw"]),
                "net_income_krw": _f(["순이익(억)", "당기순이익", "net_income_krw"]),
                "total_assets_krw": _f(["자산총계(억)", "자산총계"]),
                "total_equity_krw": _f(["자본총계(억)", "자본총계"]),
                "employee_count": int(_f(["종업원수", "임직원수", "직원수"]) or 0) or None,
                "data_source": "NICE/외부리포트 업로드",
                "notes": f"업로드 원본: {filename}"
            })
        return records

    # PDF / DOCX / TXT 보고서에서 정규식으로 신용등급·사업자번호·대표자 추출
    from processor.ic_memo_generator import extract_text_from_file
    raw_text = extract_text_from_file(filename, file_bytes)
    biz_match = re.search(r"\b(\d{3}-\d{2}-\d{5})\b", raw_text)
    grade_match = re.search(r"(?:신용등급|기업신용등급|평가등급|CRI|현금흐름등급)\s*[:：]?\s*([A-D][+\-0]?|[A-Z]{1,3}[+\-0]?)", raw_text)
    ceo_match = re.search(r"(?:대표자|대표이사)\s*[:：]\s*([가-힣a-zA-Z\s]{2,15})", raw_text)

    if fallback_name:
        records.append({
            "corp_name": fallback_name.strip(),
            "biz_reg_no": biz_match.group(1) if biz_match else None,
            "ceo_name": ceo_match.group(1).strip() if ceo_match else None,
            "credit_grade": f"{grade_match.group(1)} (리포트 추출)" if grade_match else "리포트 첨부됨",
            "data_source": "NICE/PDF 리포트 업로드",
            "notes": raw_text[:2500]
        })
    return records

