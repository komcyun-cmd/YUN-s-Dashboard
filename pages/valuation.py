import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="월가 컨센서스 판독기", page_icon="📡", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 데이터 수집 함수 (애널리스트 데이터)
# ------------------------------------------------------------------
def get_analyst_data(ticker):
    """월가 애널리스트들의 목표주가와 투자의견을 가져옵니다."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 1. 현재 정보
        current_price = info.get('currentPrice', 0)
        if current_price == 0:
            current_price = info.get('regularMarketPreviousClose', 0)
            
        name = info.get('longName', ticker)
        currency = info.get('currency', 'USD')
        
        # 2. 애널리스트 목표 주가 (핵심!)
        target_mean = info.get('targetMeanPrice', 0)  # 평균 목표가
        target_high = info.get('targetHighPrice', 0)  # 최고 목표가
        target_low = info.get('targetLowPrice', 0)    # 최저 목표가
        num_analysts = info.get('numberOfAnalystOpinions', 0) # 참여한 애널리스트 수
        recommendation = info.get('recommendationKey', 'none').upper() # BUY, HOLD, SELL
        
        return {
            "name": name,
            "current": current_price,
            "target_mean": target_mean,
            "target_high": target_high,
            "target_low": target_low,
            "analysts": num_analysts,
            "rec": recommendation,
            "currency": currency,
            "summary": info.get('longBusinessSummary', '')
        }
    except Exception as e:
        return None

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.title("📡 월가 컨센서스 판독기")
st.caption("수학 공식 대신, 전 세계 애널리스트들의 '목표 주가'와 비교합니다.")

# 종목 검색
with st.container(border=True):
    col1, col2 = st.columns([3, 1])
    ticker = col1.text_input("티커 입력 (예: TSLA, NVDA, 005930.KS)", placeholder="TSLA")
    btn = col2.button("분석 시작 🔍", type="primary")

if btn and ticker:
    with st.spinner(f"월가 리포트 분석 중... ({ticker})"):
        data = get_analyst_data(ticker)
        
        if data and data['current'] > 0:
            # 1. 핵심 지표 카드
            st.divider()
            st.subheader(f"📊 {data['name']} 분석 결과")
            
            # 괴리율 계산 (목표가 vs 현재가)
            if data['target_mean'] > 0:
                upside = ((data['target_mean'] - data['current']) / data['current']) * 100
            else:
                upside = 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("현재 주가", f"{data['current']:,.0f} {data['currency']}")
            c2.metric("월가 목표가 (평균)", f"{data['target_mean']:,.0f} {data['currency']}",
                      delta=f"{data['target_mean']-data['current']:,.0f} (괴리율)", delta_color="normal")
            
            # 투자의견 색상 매핑
            rec_color = "off"
            if "BUY" in data['rec']: rec_color = "normal" # 초록
            elif "SELL" in data['rec']: rec_color = "inverse" # 빨강
            
            c3.metric("투자 의견 (Consensus)", data['rec'].replace('_', ' '), 
                      delta=f"{data['analysts']}명 참여", delta_color=rec_color)
            
            # 2. 시각화 (게이지 바)
            st.write("")
            st.caption("🔻 최저가 의견 ────────── 현재가 vs 평균 ────────── 최고가 의견 🔺")
            
            # 현재가가 범위 내 어디에 있는지 표시
            if data['target_high'] > data['target_low']:
                progress = (data['current'] - data['target_low']) / (data['target_high'] - data['target_low'])
                progress = min(max(progress, 0.0), 1.0) # 0~1 사이로 제한
                st.progress(progress)
                
                c_low, c_curr, c_high = st.columns([1, 2, 1])
                c_low.markdown(f"📉 최저: **{data['target_low']}**")
                c_curr.markdown(f"<div style='text-align:center; color:blue; font-weight:bold;'>📍 현재: {data['current']}</div>", unsafe_allow_html=True)
                c_high.markdown(f"<div style='text-align:right;'>📈 최고: **{data['target_high']}**</div>", unsafe_allow_html=True)
            
            # 3. AI의 종합 코멘트
            st.divider()
            with st.spinner("AI가 월가 의견을 해석 중입니다..."):
                prompt = f"""
                너는 베테랑 펀드매니저다. 다음 데이터를 보고 브리핑해라.
                
                [종목: {data['name']}]
                - 현재가: {data['current']}
                - 월가 평균 목표가: {data['target_mean']} (괴리율: {upside:.2f}%)
                - 의견 분포: {data['target_low']} (최저) ~ {data['target_high']} (최고)
                - 투자의견: {data['rec']} (참여 애널리스트: {data['analysts']}명)
                
                [질문]
                1. 현재 주가가 월가 기대치 대비 어떤 수준인가? (저평가/적정/과열)
                2. '최고 목표가'를 부른 애널리스트는 어떤 근거일지 추론해봐.
                3. 지금 진입해도 되는지 안전마진 관점에서 조언해줘. (3줄 요약)
                """
                try:
                    analysis = model.generate_content(prompt).text
                    st.info(analysis)
                except:
                    st.warning("AI 분석을 가져오지 못했습니다.")
                    
        else:
            st.error("데이터를 가져올 수 없습니다. 티커를 확인해주세요. (한국 주식은 005930.KS 형식)")
