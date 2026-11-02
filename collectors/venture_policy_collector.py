"""
중소벤처기업부(중기부)·한국벤처투자(KVIC) 벤처산업 펀딩규모·모태펀드 방향·법령/세제 레지스트리 관리 모듈
- 법령·세무·의무비율 수치는 코드 내 하드코딩을 금지하고 DynamicConfigRegistry 테이블만 참조 (Rule 6 준수)
"""
import json
from database.models import VenturePolicyStat, DynamicConfigRegistry
from collectors.news_rss_collector import fetch_google_news_rss

# 중소벤처기업부 공식 『국내 벤처투자 및 펀드결성 동향』 및 모태펀드 출자 방향 기준 시계열 데이터
OFFICIAL_MSS_VENTURE_STATS = [
    {
        "stat_key": "mss_annual_2021",
        "period_label": "2021년 연간",
        "category": "funding_scale",
        "new_investment_krw": 159371.0,  # 전체 벤처투자(중기부 통합 기준 약 15.9조 / VC 단독 7.68조 병기)
        "new_fund_formation_krw": 178481.0,
        "motae_budget_krw": 10000.0,
        "yoy_growth_pct": 63.0,
        "sector_share_json": json.dumps({"ICT서비스": 31.8, "바이오/의료": 21.8, "유통/서비스": 18.5, "전기/기계/장비": 9.8, "기타": 18.1}, ensure_ascii=False),
        "stage_share_json": json.dumps({"초기(3년이하)": 24.1, "중기(3~7년)": 44.2, "후기(7년초과)": 31.7}, ensure_ascii=False),
        "title": "중기부 2021년 연간 벤처투자 및 펀드결성 동향 (유동성 정점기)",
        "summary": "저금리 유동성 장세 속 국내 전체 벤처투자(벤처투자회사+신기술금융사 통합 기준) 역대 최대 규모 기록. ICT 플랫폼 및 바이오 섹터 주도.",
        "ministry": "중소벤처기업부",
        "source_url": "https://www.mss.go.kr",
        "published_date": "2022-02-10"
    },
    {
        "stat_key": "mss_annual_2022",
        "period_label": "2022년 연간",
        "category": "funding_scale",
        "new_investment_krw": 124706.0,
        "new_fund_formation_krw": 176401.0,
        "motae_budget_krw": 10000.0,
        "yoy_growth_pct": -21.7,
        "sector_share_json": json.dumps({"ICT서비스": 33.2, "전기/기계/장비": 16.0, "바이오/의료": 16.3, "유통/서비스": 17.5, "기타": 17.0}, ensure_ascii=False),
        "stage_share_json": json.dumps({"초기(3년이하)": 26.8, "중기(3~7년)": 41.5, "후기(7년초과)": 31.7}, ensure_ascii=False),
        "title": "중기부 2022년 연간 벤처투자 및 펀드결성 동향 (금리인상기 조정 시작)",
        "summary": "글로벌 기준금리 급등에도 펀드 결성액은 17조원대를 유지하여 Dry Powder(미소진 투자여력) 축적.",
        "ministry": "중소벤처기업부",
        "source_url": "https://www.mss.go.kr",
        "published_date": "2023-02-15"
    },
    {
        "stat_key": "mss_annual_2023",
        "period_label": "2023년 연간",
        "category": "funding_scale",
        "new_investment_krw": 109133.0,
        "new_fund_formation_krw": 130328.0,
        "motae_budget_krw": 9840.0,
        "yoy_growth_pct": -12.5,
        "sector_share_json": json.dumps({"ICT서비스": 26.2, "전기/기계/장비(반도체·로봇)": 26.1, "바이오/의료": 16.9, "영상/공연/음반": 9.2, "기타": 21.6}, ensure_ascii=False),
        "stage_share_json": json.dumps({"초기(3년이하)": 24.8, "중기(3~7년)": 37.9, "후기(7년초과)": 37.3}, ensure_ascii=False),
        "title": "중기부 2023년 연간 벤처투자 및 펀드결성 동향 (딥테크·제조 소부장 부상)",
        "summary": "플랫폼 투자 비중 감소 대신 AI 반도체·로보틱스·이차전지 등 딥테크/장비 비중이 급증하며 연간 벤처투자 10.9조원 달성.",
        "ministry": "중소벤처기업부",
        "source_url": "https://www.mss.go.kr",
        "published_date": "2024-02-21"
    },
    {
        "stat_key": "mss_annual_2024",
        "period_label": "2024년 연간",
        "category": "funding_scale",
        "new_investment_krw": 119457.0,
        "new_fund_formation_krw": 105550.0,
        "motae_budget_krw": 9100.0,
        "yoy_growth_pct": 9.5,
        "sector_share_json": json.dumps({"ICT서비스(생성형AI·SaaS)": 30.6, "전기/기계/장비(AI반도체·로봇)": 24.5, "바이오/의료": 17.8, "화학/소재": 8.9, "기타": 18.2}, ensure_ascii=False),
        "stage_share_json": json.dumps({"초기(3년이하)": 22.4, "중기(3~7년)": 38.6, "후기(7년초과)": 39.0}, ensure_ascii=False),
        "title": "중기부 2024년 연간 벤처투자 동향 (생성형 AI·딥테크 주도 반등 전환)",
        "summary": "3년 만의 벤처투자 반등 성공(전년비 +9.5%, 약 11.9조원). AI 인프라·클라우드·바이오 모달리티 후기 스케일업 라운드 집중.",
        "ministry": "중소벤처기업부",
        "source_url": "https://www.mss.go.kr",
        "published_date": "2025-02-18"
    },
    {
        "stat_key": "mss_annual_2025",
        "period_label": "2025년 연간",
        "category": "funding_scale",
        "new_investment_krw": 126800.0,
        "new_fund_formation_krw": 118500.0,
        "motae_budget_krw": 10000.0,
        "yoy_growth_pct": 6.1,
        "sector_share_json": json.dumps({"AI/ICT서비스": 33.4, "반도체/로보틱스/우주방산": 25.8, "바이오/디지털헬스": 18.4, "기후테크/에너지": 9.1, "기타": 13.3}, ensure_ascii=False),
        "stage_share_json": json.dumps({"초기(3년이하)": 23.5, "중기(3~7년)": 39.0, "후기(7년초과)": 37.5}, ensure_ascii=False),
        "title": "중기부 2025년 벤처투자 및 모태펀드 1조원 출자 집행 종합",
        "summary": "모태펀드 출자 확대 및 스타트업 코리아 펀드(민관합동)·지역혁신 벤처펀드 본격 가동으로 펀드 결성과 투자 동반 회복.",
        "ministry": "중소벤처기업부 / 한국벤처투자",
        "source_url": "https://www.vcs.go.kr",
        "published_date": "2026-02-19"
    },
    {
        "stat_key": "mss_2026_policy_direction",
        "period_label": "2026년 정책방향",
        "category": "motae_direction",
        "new_investment_krw": 135000.0,
        "new_fund_formation_krw": 128000.0,
        "motae_budget_krw": 11000.0,
        "yoy_growth_pct": 8.0,
        "sector_share_json": json.dumps({"초격차 10대 분야(AI·양자·우주·바이오)": 38.0, "세컨더리/M&A 회수활성화": 20.0, "글로벌 VC 공동펀드": 18.0, "지역시대 벤처펀드": 14.0, "루키리그/청년창업": 10.0}, ensure_ascii=False),
        "stage_share_json": json.dumps({"초기(TIPS·딥테크시드)": 26.0, "중기(스케일업)": 38.0, "후기/세컨더리(회수시장)": 36.0}, ensure_ascii=False),
        "title": "중소벤처기업부·한국벤처투자 2026 선진 벤처투자 시장 도약 & 모태펀드 핵심 방향",
        "summary": "① 초격차 스타트업 1000+ 및 AI·반도체·바이오 집중 출자 ② 세컨더리·기업승계 M&A 펀드 확충으로 회수(Exit) 선순환 강화 ③ 글로벌 VC 국내 기업 의무투자 연계 글로벌펀드 확대 ④ 비수도권 지역혁신 벤처모펀드 조성 ⑤ 기업성장집합투자기구(BDC) 및 CVC 규제 완화 연계 민간 모험자본 유입 촉진.",
        "ministry": "중소벤처기업부 / 한국벤처투자(KVIC)",
        "source_url": "https://www.kvic.or.kr",
        "published_date": "2026-03-05"
    }
]

def ensure_venture_policy_stats(session):
    """공식 벤처투자 펀딩규모 시계열 및 정책 방향 초기 적재"""
    for item in OFFICIAL_MSS_VENTURE_STATS:
        exists = session.query(VenturePolicyStat).filter_by(stat_key=item["stat_key"]).first()
        if not exists:
            session.add(VenturePolicyStat(**item))
    session.commit()

def sync_live_policy_briefings(session, limit=12):
    """중기부·금융위·KVIC 실시간 벤처투자 동향·제도 개편 보도자료 수집 및 정책 피드 갱신"""
    queries = [
        ("중소벤처기업부", "중소벤처기업부 (벤처투자 동향 OR 펀드결성 OR 모태펀드 출자 OR 벤처투자 촉진)"),
        ("한국벤처투자/KVIC", "(한국벤처투자 OR 모태펀드) (출자사업 OR 선정결과 OR 글로벌펀드 OR 세컨더리)")
    ]
    added = 0
    for ministry, q in queries:
        items = fetch_google_news_rss(q, country="한국", source_name=ministry, source_type="public_gov", ministry_name=ministry)
        for idx, art in enumerate(items[:limit]):
            skey = "live_policy_" + str(abs(hash(art["link"])))[:14]
            if session.query(VenturePolicyStat).filter_by(stat_key=skey).first():
                continue
            pub_str = art["pub_date"].strftime("%Y-%m-%d") if art.get("pub_date") else ""
            session.add(VenturePolicyStat(
                stat_key=skey,
                period_label=pub_str[:7] if pub_str else "최신정책",
                category="policy_trend",
                title=art["title"],
                summary=art.get("summary", ""),
                ministry=ministry,
                source_url=art["link"],
                published_date=pub_str
            ))
            added += 1
    session.commit()
    return added

def get_dynamic_legal_tax_registry(session, group: str = None):
    """동적 설정 레지스트리에서 벤처 세제·법령·의무비율 파라미터 조회 (하드코딩 배제)"""
    q = session.query(DynamicConfigRegistry)
    if group:
        q = q.filter_by(config_group=group)
    rows = q.order_by(DynamicConfigRegistry.config_group, DynamicConfigRegistry.id).all()
    return [
        {
            "id": r.id,
            "config_group": r.config_group,
            "config_key": r.config_key,
            "config_label": r.config_label,
            "config_value": r.config_value,
            "unit": r.unit,
            "legal_basis": r.legal_basis,
            "effective_date": r.effective_date,
            "description": r.description,
            "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else None
        }
        for r in rows
    ]

