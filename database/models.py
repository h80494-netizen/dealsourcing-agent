from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class DealArticle(Base):
    __tablename__ = 'deal_articles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(50)) # e.g. "GoogleNews", "NaverNews"
    title = Column(String(200))
    link = Column(String(500), unique=True) # 중복 수집 방지
    pub_date = Column(DateTime)
    summary = Column(Text, nullable=True)
    
    # 분석된 메타데이터
    matched_industry = Column(String(100), nullable=True)
    matched_signal = Column(String(100), nullable=True)
    matched_financial = Column(String(100), nullable=True) # 수익성/매출 키워드
    
    company_name = Column(String(100), nullable=True)
    deal_stage = Column(String(50), nullable=True) # 딜소싱, 실사, 투자, 밸류업, Exit
    growth_impact_score = Column(Float, nullable=True) # 기존 사용
    impact_score = Column(Float, nullable=True) # 기업/산업 직접 영향력 1주일 스코어 (0~100)
    
    country = Column(String(20), nullable=True) # 미국, 한국
    news_grade = Column(String(10), nullable=True) # S, A, B, C
    promising_industry = Column(String(100), nullable=True) # 유망산업
    compressed_summary = Column(Text, nullable=True) # 본문 압축 요약
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_notified = Column(Boolean, default=False)

class ResearchDomain(Base):
    __tablename__ = 'research_domains'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True)
    url = Column(String(500), unique=True)
    rss_url = Column(String(500), nullable=True)
    purpose = Column(String(200), nullable=True)
    country = Column(String(20)) # 미국, 한국
    category = Column(String(100)) # AI뉴스, AI바이오 등
    is_active = Column(Boolean, default=True)

class SearchKeyword(Base):
    __tablename__ = 'search_keywords'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(100), unique=True)
    type = Column(String(20)) # '기존', '추가'
    category = Column(String(50)) # 'industry', 'deal_signal', 'profitability_revenue'
    is_active = Column(Boolean, default=True)
