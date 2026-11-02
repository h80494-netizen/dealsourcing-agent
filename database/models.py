from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class DealArticle(Base):
    __tablename__ = 'deal_articles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(100))  # e.g. "GoogleNews", "NaverNews", "정책브리핑(중소벤처기업부)"
    source_type = Column(String(30), default='private_media')  # 'private_media' | 'public_gov'
    ministry_name = Column(String(100), nullable=True)  # e.g. "중소벤처기업부", "금융위원회"
    title = Column(String(300))
    link = Column(String(500), unique=True)  # 중복 수집 방지
    pub_date = Column(DateTime)
    summary = Column(Text, nullable=True)

    # 분석된 메타데이터
    matched_industry = Column(String(100), nullable=True)
    matched_signal = Column(String(100), nullable=True)
    matched_financial = Column(String(100), nullable=True)  # 수익성/매출 키워드

    company_name = Column(String(100), nullable=True)
    deal_stage = Column(String(50), nullable=True)  # 딜소싱, 실사, 투자, 밸류업, Exit
    growth_impact_score = Column(Float, nullable=True)  # 기존 사용
    impact_score = Column(Float, nullable=True)  # 기업/산업 직접 영향력 1주일 스코어 (0~100)

    country = Column(String(20), nullable=True)  # 미국, 한국 등
    news_grade = Column(String(10), nullable=True)  # A, B, C, D, E
    promising_industry = Column(String(100), nullable=True)  # 유망산업
    compressed_summary = Column(Text, nullable=True)  # 본문 압축 요약

    created_at = Column(DateTime, default=datetime.utcnow)
    is_notified = Column(Boolean, default=False)


class ResearchDomain(Base):
    __tablename__ = 'research_domains'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    url = Column(String(500), unique=True)
    rss_url = Column(String(500), nullable=True)
    purpose = Column(String(200), nullable=True)
    country = Column(String(20))
    category = Column(String(100))
    is_active = Column(Boolean, default=True)


class SearchKeyword(Base):
    __tablename__ = 'search_keywords'

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(100), unique=True)
    type = Column(String(20))  # '기존', '추가'
    category = Column(String(50))  # 'industry', 'deal_signal', 'profitability_revenue'
    is_active = Column(Boolean, default=True)


class CompanyProfile(Base):
    """기업·재무 인텔리전스 DB (DART OpenAPI, 금융위 공공데이터, 국민연금, NICE 업로드 통합)"""
    __tablename__ = 'company_profiles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    corp_name = Column(String(150), index=True, nullable=False)
    corp_code = Column(String(20), nullable=True, index=True)  # DART 8자리 고유번호
    biz_reg_no = Column(String(30), nullable=True, index=True)  # 사업자등록번호
    corp_reg_no = Column(String(30), nullable=True)  # 법인등록번호
    stock_code = Column(String(20), nullable=True)  # 종목코드 (상장사)
    corp_cls = Column(String(30), nullable=True)  # 유가증권 / 코스닥 / 코넥스 / 비상장(외감) / 비상장
    ceo_name = Column(String(100), nullable=True)
    est_dt = Column(String(20), nullable=True)  # 설립일 (YYYY-MM-DD)
    industry_code = Column(String(50), nullable=True)
    industry_name = Column(String(150), nullable=True)
    address = Column(String(300), nullable=True)
    homepage_url = Column(String(300), nullable=True)

    # 벤처/고용/신용 지표
    venture_cert_type = Column(String(80), nullable=True)  # 벤처투자유형 / 연구개발유형 / 혁신성장유형 등
    employee_count = Column(Integer, nullable=True)
    avg_salary_est_krw = Column(Float, nullable=True)  # 추정 평균연봉(만원)
    credit_grade = Column(String(40), nullable=True)  # NICE 신용등급 또는 재무건전성 산출등급

    # 최근 결산 핵심 재무수치 (단위: 억원)
    latest_bsns_year = Column(String(10), nullable=True)
    revenue_krw = Column(Float, nullable=True)  # 매출액(억원)
    op_profit_krw = Column(Float, nullable=True)  # 영업이익(억원)
    net_income_krw = Column(Float, nullable=True)  # 당기순이익(억원)
    total_assets_krw = Column(Float, nullable=True)  # 자산총계(억원)
    total_liab_krw = Column(Float, nullable=True)  # 부채총계(억원)
    total_equity_krw = Column(Float, nullable=True)  # 자본총계(억원)

    # 투자/증자 요약 및 3개년 상세 JSON
    capital_increase_summary = Column(Text, nullable=True)  # 유상증자·RCPS·CB 발행 요약
    financial_history_json = Column(Text, nullable=True)  # 3개년 재무 배열 JSON
    data_source = Column(String(100), default='DART')  # DART / FSC / NPS / NICE_UPLOAD
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VentureFund(Base):
    """벤처펀드 결성·운용 현황 DB (DIVA 전자공시, 벤처투자종합포털, 한국벤처투자 KVIC)"""
    __tablename__ = 'venture_funds'

    id = Column(Integer, primary_key=True, autoincrement=True)
    asct_id = Column(String(40), unique=True, nullable=True)  # DIVA 조합 고유 ID 또는 해시 키
    fund_name = Column(String(200), nullable=False, index=True)
    gp_name = Column(String(150), nullable=False, index=True)  # 운용사(GP)명
    reg_date = Column(String(20), nullable=True, index=True)  # 등록/결성일 (YYYY-MM-DD)
    maturity_date = Column(String(20), nullable=True)  # 만기일 (YYYY-MM-DD)
    commitment_krw = Column(Float, nullable=True)  # 결성총액(억원)
    invest_field = Column(String(100), nullable=True)  # 투자분야 구분 (일반/바이오/ICT/세컨더리 등)
    purpose_type = Column(String(100), nullable=True)  # 목적구분
    support_type = Column(String(100), nullable=True)  # 지원구분 (창업초기/청년창업/초격차/지역 등)
    motae_backed = Column(Boolean, default=False)  # 모태펀드 출자 여부
    source_name = Column(String(60), default='DIVA 전자공시')
    source_url = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class VenturePolicyStat(Base):
    """중소벤처기업부(중기부)·KVIC 벤처산업 펀딩규모 통계 및 출자·제도 방향 DB"""
    __tablename__ = 'venture_policy_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    stat_key = Column(String(80), unique=True, nullable=False)
    period_label = Column(String(40), nullable=False, index=True)  # 예: "2025년 연간", "2026년 상반기"
    category = Column(String(40), nullable=False)  # 'funding_scale' | 'motae_direction' | 'policy_trend'
    new_investment_krw = Column(Float, nullable=True)  # 신규 벤처투자 규모 (억원)
    new_fund_formation_krw = Column(Float, nullable=True)  # 신규 벤처펀드 결성 규모 (억원)
    motae_budget_krw = Column(Float, nullable=True)  # 모태펀드 출자예산/공고 규모 (억원)
    yoy_growth_pct = Column(Float, nullable=True)  # 전년 동기 대비 증감률(%)
    sector_share_json = Column(Text, nullable=True)  # 업종별 투자 비중 JSON
    stage_share_json = Column(Text, nullable=True)  # 업력별(초기/중기/후기) 비중 JSON
    title = Column(String(250), nullable=False)
    summary = Column(Text, nullable=True)
    ministry = Column(String(80), default='중소벤처기업부')
    source_url = Column(String(400), nullable=True)
    published_date = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GovGrantNotice(Base):
    """정부 창업·벤처·R&D 지원사업 공고 DB (기업마당 bizinfo, K-Startup OpenAPI)"""
    __tablename__ = 'gov_grant_notices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    notice_uid = Column(String(100), unique=True, nullable=False)
    category = Column(String(50), nullable=True, index=True)  # 창업, 기술(R&D), 금융, 수출, 인력 등
    title = Column(String(300), nullable=False, index=True)
    ministry = Column(String(100), nullable=True)  # 소관부처/지자체 (중소벤처기업부 등)
    executor = Column(String(120), nullable=True)  # 수행기관 (창업진흥원, 중진공 등)
    apply_period = Column(String(80), nullable=True)  # YYYY-MM-DD ~ YYYY-MM-DD
    end_date = Column(String(20), nullable=True, index=True)  # 마감일 (YYYY-MM-DD)
    reg_date = Column(String(20), nullable=True)
    detail_url = Column(String(400), nullable=True)
    source_name = Column(String(50), default='기업마당(중기부)')
    created_at = Column(DateTime, default=datetime.utcnow)


class CompanyPatent(Base):
    """기업 특허·지식재산권(IP) DB (KIPRISPlus OpenAPI 및 특허 검색 연동)"""
    __tablename__ = 'company_patents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    applicant_name = Column(String(150), index=True, nullable=False)
    application_number = Column(String(60), unique=True, nullable=False)
    invention_title = Column(String(300), nullable=False)
    ipc_code = Column(String(100), nullable=True)
    application_date = Column(String(20), nullable=True)
    registration_number = Column(String(60), nullable=True)
    registration_status = Column(String(40), nullable=True)  # 등록 / 공개 / 심사중
    abstract_text = Column(Text, nullable=True)
    source_name = Column(String(50), default='KIPRIS')
    created_at = Column(DateTime, default=datetime.utcnow)


class DynamicConfigRegistry(Base):
    """벤처투자 법령·세무·제도 파라미터 동적 설정 레지스트리 (하드코딩 배제 원칙 준수)"""
    __tablename__ = 'dynamic_config_registry'

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_group = Column(String(80), index=True, nullable=False)
    config_key = Column(String(120), unique=True, nullable=False)
    config_label = Column(String(200), nullable=False)
    config_value = Column(String(100), nullable=False)
    unit = Column(String(30), nullable=True)
    legal_basis = Column(String(200), nullable=True)
    effective_date = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
