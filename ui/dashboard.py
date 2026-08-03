import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(page_title="VC 딜소싱 대시보드", layout="wide")

st.title("🚀 VC 딜소싱 실시간 모니터링 대시보드")
st.markdown("수익성, 매출, 주요 투자 시그널이 포함된 뉴스 및 웹 데이터를 필터링하여 보여줍니다.")

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'dealsourcing.db')

def load_data():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM deal_articles ORDER BY created_at DESC", conn)
    conn.close()
    return df

df = load_data()

if df.empty:
    st.info("아직 수집된 데이터가 없습니다. `main_pipeline.py`를 실행하여 데이터를 수집해주세요.")
else:
    # 사이드바 필터
    st.sidebar.header("필터 설정")
    
    # 산업 필터
    industries = df['matched_industry'].dropna().unique().tolist()
    # 콤마로 구분된 텍스트들을 평탄화
    flat_industries = list(set([i.strip() for sublist in industries for i in sublist.split(',') if i.strip()]))
    selected_ind = st.sidebar.multiselect("산업 분류", flat_industries)
    
    # 시그널 필터
    signals = df['matched_signal'].dropna().unique().tolist()
    flat_signals = list(set([i.strip() for sublist in signals for i in sublist.split(',') if i.strip()]))
    selected_sig = st.sidebar.multiselect("투자 시그널", flat_signals)
    
    # 최소 임팩트 스코어
    min_score = st.sidebar.slider("최소 Growth Impact Score", 1.0, 5.0, 1.0)
    
    # 데이터 필터링 로직
    filtered_df = df.copy()
    
    if selected_ind:
        # 하나라도 포함되면 표시
        filtered_df = filtered_df[filtered_df['matched_industry'].apply(
            lambda x: any(ind in str(x) for ind in selected_ind) if pd.notnull(x) else False
        )]
        
    if selected_sig:
        filtered_df = filtered_df[filtered_df['matched_signal'].apply(
            lambda x: any(sig in str(x) for sig in selected_sig) if pd.notnull(x) else False
        )]
        
    filtered_df = filtered_df[filtered_df['growth_impact_score'] >= min_score]
    
    # 주요 지표 (KPI)
    col1, col2, col3 = st.columns(3)
    col1.metric("전체 수집 건수", f"{len(df)}건")
    col2.metric("필터링된 건수", f"{len(filtered_df)}건")
    col3.metric("고득점(4점이상) 건수", f"{len(df[df['growth_impact_score'] >= 4.0])}건")
    
    st.markdown("---")
    
    # 데이터 표시
    for _, row in filtered_df.iterrows():
        with st.expander(f"[{row['source_name']}] {row['title']} (Score: {row['growth_impact_score']})"):
            st.markdown(f"**매칭된 산업**: {row['matched_industry'] or '없음'}")
            st.markdown(f"**매칭된 시그널**: {row['matched_signal'] or '없음'}")
            st.markdown(f"**매칭된 재무/매출**: {row['matched_financial'] or '없음'}")
            st.markdown(f"**요약**: {row['summary']}")
            st.markdown(f"[기사 원문 보기]({row['link']})")
            st.caption(f"수집일시: {row['created_at']}")
