"""
정부 지원사업(기업마당 bizinfo / K-Startup OpenAPI) 및 기업 특허/IP(KIPRISPlus OpenAPI / 특허검색) 수집기
"""
import os
import re
import hashlib
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIZINFO_LIST_URL = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"

def _get_env_keys():
    load_dotenv(os.path.join(ROOT_DIR, ".env"), override=True)
    return {
        "data_go_kr_key": os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip(),
        "kipris_key": os.getenv("KIPRIS_API_KEY", "").strip()
    }

def fetch_bizinfo_grants(pages: int = 2, field_code: str = ""):
    """중소벤처기업부 기업마당(bizinfo.go.kr) 최신 정부·지자체 지원사업 공고 수집"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"
    }
    notices = []
    for p in range(1, pages + 1):
        params = {"rows": "20", "cpage": str(p)}
        if field_code:
            params["schJrsdCodeTy"] = field_code
        try:
            r = requests.get(BIZINFO_LIST_URL, headers=headers, params=params, timeout=12)
            r.encoding = "utf-8"
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for tr in soup.select("table tbody tr"):
                tds = tr.find_all("td")
                if len(tds) < 7:
                    continue
                num_txt = tds[0].get_text(" ", strip=True)
                category = tds[1].get_text(" ", strip=True)
                title_el = tds[2].find("a")
                title = title_el.get_text(" ", strip=True) if title_el else tds[2].get_text(" ", strip=True)
                href = title_el.get("href", "") if title_el else ""
                detail_url = urllib.parse.urljoin(BIZINFO_LIST_URL, href) if href else BIZINFO_LIST_URL
                apply_period = tds[3].get_text(" ", strip=True)
                ministry = tds[4].get_text(" ", strip=True)
                executor = tds[5].get_text(" ", strip=True)
                reg_date = tds[6].get_text(" ", strip=True)

                end_match = re.findall(r"\d{4}-\d{2}-\d{2}", apply_period)
                end_date = end_match[-1] if end_match else ""

                uid_match = re.search(r"pblancId=([A-Za-z0-9_]+)", href)
                notice_uid = uid_match.group(1) if uid_match else ("BIZ_" + hashlib.md5(f"{num_txt}|{title}".encode("utf-8")).hexdigest()[:12])

                notices.append({
                    "notice_uid": notice_uid,
                    "category": category,
                    "title": title,
                    "ministry": ministry,
                    "executor": executor,
                    "apply_period": apply_period,
                    "end_date": end_date,
                    "reg_date": reg_date,
                    "detail_url": detail_url,
                    "source_name": "기업마당 (중기부)"
                })
        except Exception as e:
            print(f"Bizinfo fetch warning: {e}")

    # K-Startup OpenAPI 활용신청 되어 있을 경우 추가 병합
    keys = _get_env_keys()
    if keys["data_go_kr_key"]:
        try:
            enc_key = urllib.parse.quote(urllib.parse.unquote(keys["data_go_kr_key"]))
            ks_url = (
                f"https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
                f"?serviceKey={enc_key}&page=1&perPage=20&returnType=json"
            )
            rk = requests.get(ks_url, timeout=8)
            if rk.status_code == 200 and "data" in rk.text:
                items = rk.json().get("data", [])
                for it in items:
                    pb_id = str(it.get("pbanc_sn") or "")
                    if not pb_id:
                        continue
                    end_raw = str(it.get("pbanc_rcpt_end_dt") or "")
                    end_fmt = f"{end_raw[:4]}-{end_raw[4:6]}-{end_raw[6:8]}" if len(end_raw) == 8 else end_raw
                    bgng_raw = str(it.get("pbanc_rcpt_bgng_dt") or "")
                    bgng_fmt = f"{bgng_raw[:4]}-{bgng_raw[4:6]}-{bgng_raw[6:8]}" if len(bgng_raw) == 8 else bgng_raw
                    notices.append({
                        "notice_uid": f"KSTARTUP_{pb_id}",
                        "category": it.get("supt_biz_clsfc") or "창업사업화",
                        "title": it.get("biz_pbanc_nm") or "",
                        "ministry": it.get("sprv_inst") or "중소벤처기업부",
                        "executor": it.get("biz_prch_dprt_nm") or "창업진흥원",
                        "apply_period": f"{bgng_fmt} ~ {end_fmt}",
                        "end_date": end_fmt,
                        "reg_date": bgng_fmt,
                        "detail_url": it.get("detl_pg_url") or "https://www.k-startup.go.kr",
                        "source_name": "K-Startup OpenAPI"
                    })
        except Exception:
            pass

    return notices

def sync_grants_to_db(session, pages: int = 2):
    from database.models import GovGrantNotice
    fetched = fetch_bizinfo_grants(pages=pages)
    added = 0
    for item in fetched:
        if not item.get("title"):
            continue
        exists = session.query(GovGrantNotice).filter_by(notice_uid=item["notice_uid"]).first()
        if not exists:
            session.add(GovGrantNotice(**item))
            added += 1
    session.commit()
    return {"added": added, "total_fetched": len(fetched)}

def search_company_patents(company_name: str, max_rows: int = 15):
    """
    기업명(출원인) 기준 특허 조회
    1순위: KIPRISPlus 공식 OpenAPI (KIPRIS_API_KEY 또는 공공데이터포털 KIPRIS 활용신청 키)
    2순위: Google Patents 공개 인덱스 / 특허 보도 시그널 폴백
    """
    keys = _get_env_keys()
    active_key = keys["kipris_key"] or keys["data_go_kr_key"]
    cname = (company_name or "").strip()
    if not cname:
        return {"source": "none", "items": [], "kipris_active": False}

    # 1. KIPRISPlus REST API 호출 시도 (출원인 검색)
    if active_key:
        try:
            enc_applicant = urllib.parse.quote(cname)
            enc_key = urllib.parse.quote(urllib.parse.unquote(active_key))
            kipris_url = (
                f"http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch"
                f"?applicant={enc_applicant}&numOfRows={max_rows}&pageNo=1&ServiceKey={enc_key}"
            )
            resp = requests.get(kipris_url, timeout=10)
            if resp.status_code == 200 and "<item>" in resp.text:
                root = ET.fromstring(resp.content)
                items = []
                for el in root.findall(".//item"):
                    app_no = (el.findtext("applicationNumber") or "").strip()
                    title = (el.findtext("inventionTitle") or "").strip()
                    if not app_no or not title:
                        continue
                    app_dt = (el.findtext("applicationDate") or "").strip()
                    if len(app_dt) == 8:
                        app_dt = f"{app_dt[:4]}-{app_dt[4:6]}-{app_dt[6:8]}"
                    items.append({
                        "applicant_name": (el.findtext("applicantName") or cname).strip(),
                        "application_number": app_no,
                        "invention_title": title,
                        "ipc_code": (el.findtext("ipcNumber") or "").strip(),
                        "application_date": app_dt,
                        "registration_number": (el.findtext("registerNumber") or "").strip(),
                        "registration_status": (el.findtext("registerStatus") or "공개").strip(),
                        "abstract_text": (el.findtext("astrtCont") or "").strip()[:500],
                        "source_name": "KIPRISPlus OpenAPI"
                    })
                if items:
                    return {"source": "KIPRISPlus OpenAPI", "items": items, "kipris_active": True}
        except Exception as e:
            print(f"KIPRIS API lookup notice: {e}")

    # 2. KIPRIS 미개통 시 Google Patents XHR / 특허 뉴스 시그널 폴백 제공
    fallback_items = []
    try:
        gp_xhr = "https://patents.google.com/xhr/query"
        q_param = f"assignee={urllib.parse.quote(cname)}&country=KR&num={min(max_rows, 10)}"
        r_gp = requests.get(
            gp_xhr,
            params={"url": q_param, "exp": ""},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"},
            timeout=10
        )
        if r_gp.status_code == 200 and "results" in r_gp.text:
            data = r_gp.json()
            clusters = data.get("results", {}).get("cluster", [])
            for cl in clusters:
                for res in cl.get("result", []):
                    pat = res.get("patent", {})
                    pub_no = pat.get("publication_number") or ""
                    title_html = pat.get("title") or ""
                    clean_title = BeautifulSoup(title_html, "html.parser").get_text(" ", strip=True)
                    snippet_html = pat.get("snippet") or ""
                    clean_snip = BeautifulSoup(snippet_html, "html.parser").get_text(" ", strip=True)
                    if pub_no and clean_title:
                        fallback_items.append({
                            "applicant_name": pat.get("assignee") or cname,
                            "application_number": pub_no,
                            "invention_title": clean_title,
                            "ipc_code": "",
                            "application_date": pat.get("filing_date") or pat.get("publication_date") or "",
                            "registration_number": pub_no if pub_no.endswith("B1") or pub_no.endswith("B2") else "",
                            "registration_status": "등록" if ("B1" in pub_no or "B2" in pub_no) else "공개",
                            "abstract_text": clean_snip[:500],
                            "source_name": "Google Patents (KR)"
                        })
    except Exception:
        pass

    return {
        "source": "Google Patents (KR)" if fallback_items else "KIPRIS 키 대기중",
        "items": fallback_items,
        "kipris_active": bool(keys["kipris_key"])
    }

