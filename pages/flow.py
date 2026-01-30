import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ------------------------------------------------------------------
# [1] 페이지 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="머니 플로우 추적기", page_icon="🐋", layout="wide")

st.title("🐋 머니 플로우(Money Flow) 추적기")
st.caption("차트는 속일 수 있어도, 거래량과 내부자 거래는 속일 수 없습니다.")

# ------------------------------------------------------------------
# [2] 핵심 분석 함수 (Smart Money Logic)
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def analyze_smart_money(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    
    # 1. 기본 데이터 (1년치)
    hist = stock.history(period="1y")
    if hist.empty:
        return None, "데이터 부족"

    # 2. 내부자 거래 (Insider Trading)
    try:
        # 최근 6개월 내부자 거래 내역
        insider = stock.insider_transactions
        if insider is not None and not insider.empty:
            # 매수(Purchase)만 필터링 (Text 컬럼 등에 'Purchase'나 'Buy'가 포함된 경우)
            # yfinance 데이터 구조가 가변적이라 안전하게 처리
            insider = insider.sort_index(ascending=False).head(10)
        else:
            insider = pd.DataFrame()
    except:
        insider = pd.DataFrame()

    # 3. 기관 보유 비중 (Institutional Holders)
    try:
        major = stock.major_holders
        # 데이터프레임 구조에 따라 처리 (0: Value, 1: Description 인 경우)
        if major is not None:
            insider_pct = major[0].iloc[0] # 내부자 보유율
            inst_pct = major[0].iloc[1]    # 기관 보유율
        else:
            insider_pct = "N/A"
            inst_pct = "N/A"
    except:
        insider_pct = "-"
        inst_pct = "-"

    # 4. 스마트 머니 점수 계산 (알고리즘)
    # 로직: 가격은 횡보/하락인데 거래량(OBV)이 늘거나, MFI(자금흐름)가 높으면 매집
    
    # OBV 계산
    hist['OBV'] = (pd.Series(1, index=hist.index).where(hist['Close'] > hist['Close'].shift(1), -1)
                   .where(hist['Close'] != hist['Close'].shift(1), 0) * hist['Volume']).cumsum()
    
    # 최근 20일 기준 분석
    recent = hist.tail(20)
    price_change = (recent['Close'].iloc[-1] - recent['Close'].iloc[0]) / recent['Close'].iloc[0] * 100
    obv_change = (recent['OBV'].iloc[-1] - recent['OBV'].iloc[0])
    
    # 점수 산정 (0~100)
    score = 50
    reason = []
    
    # 시나리오 1: 가격은 떨어졌는데 OBV(매집)는 올랐다 -> 강력 매수 신호 (다이버전스)
    if price_change < 0 and obv_change > 0:
        score += 30
        reason.append("📉 가격 하락 중 매집 발생 (다이버전스)")
    # 시나리오 2: 거래량이 평균 대비 폭증
    vol_ratio = recent['Volume'].mean() / hist['Volume'].mean()
    if vol_ratio > 1.5:
        score += 20
        reason.append("🔥 평소 대비 거래량 1.5배 급증 (손바뀜)")
        
    return {
        "hist": hist,
        "insider": insider,
        "holders": {"insider": insider_pct, "institution": inst_pct},
        "score": score,
        "reasons": reason,
        "price_change": price_change,
        "last_price": recent['Close'].iloc[-1]
    }, None

# ------------------------------------------------------------------
# [3] UI 구성
# ------------------------------------------------------------------

# 사이드바: 종목 입력
with st.sidebar:
    st.header("🔍 종목 탐색")
    ticker = st.text_input("티커 입력 (예: TSLA, NVDA, AAPL)", value="TSLA").upper()
    if st.button("추적 시작 🚀", type="primary"):
        st.session_state['analyze'] = True

if 'analyze' in st.session_state:
    with st.spinner(f"{ticker}의 자금 흐름을 추적 중입니다..."):
        data, err = analyze_smart_money(ticker)
        
    if err:
        st.error(f"데이터를 가져올 수 없습니다: {err}")
    else:
        # [섹션 1] 스마트 머니 스코어
        st.subheader(f"📊 {ticker} 스마트 머니 진단")
        
        c1, c2, c3 = st.columns([1, 1, 2])
        
        with c1:
            st.metric("현재 주가", f"${data['last_price']:.2f}", f"{data['price_change']:.2f}% (20일)")
            
        with c2:
            score = data['score']
            color = "normal"
            if score >= 80: color = "normal" # 초록(Streamlit 기본)
            elif score <= 40: color = "inverse" # 빨강
            
            st.metric("💰 유입 점수", f"{score}점", delta="매집 징후" if score >= 70 else "관망/매도", delta_color=color)
            
        with c3:
            if data['reasons']:
                st.success("💡 탐지된 신호: " + ", ".join(data['reasons']))
            else:
                st.info("특이한 매집 징후는 발견되지 않았습니다.")

        st.divider()

        # [섹션 2] 누가 들고 있나? (파이차트)
        st.subheader("👥 보유 주체 분석")
        h_col1, h_col2 = st.columns(2)
        
        with h_col1:
            # 보유 비중 시각화
            # yfinance 데이터가 문자열(%)로 올 수 있어 처리
            try:
                inst_val = float(data['holders']['institution'].strip('%')) if isinstance(data['holders']['institution'], str) else 0
                insider_val = float(data['holders']['insider'].strip('%')) if isinstance(data['holders']['insider'], str) else 0
                retail_val = 100 - inst_val - insider_val
                
                labels = ['기관(Smart Money)', '내부자(Owner)', '개인/기타']
                values = [inst_val, insider_val, retail_val]
                
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
                fig.update_layout(height=300, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.warning("보유 비중 데이터를 시각화할 수 없습니다.")
                st.write(f"기관: {data['holders']['institution']}, 내부자: {data['holders']['insider']}")

        with h_col2:
            st.markdown("""
            **🧐 해석 가이드**
            - **기관 비중 > 70%**: 메이저들이 주도하는 안정적인 주식입니다.
            - **내부자 비중 높음**: 오너가 회사를 믿고 있다는 강력한 신호입니다.
            - **내부자 매수 발생**: 경영진이 주가가 저평가되었다고 판단한 것입니다. (강력 호재)
            """)

        st.divider()

        # [섹션 3] 🚨 내부자 거래 알림 (Insider Trading)
        st.subheader("🕵️‍♀️ 내부자(임원/대주주) 거래 내역")
        
        insider_df = data['insider']
        if not insider_df.empty:
            # 보기 좋게 컬럼 정리
            st.dataframe(
                insider_df[['Shares', 'Value', 'Text', 'Start Date']].style.highlight_max(axis=0),
                use_container_width=True
            )
            st.caption("최근 내부자가 주식을 팔았다면 'Sale', 샀다면 'Purchase'로 표시됩니다.")
        else:
            st.info("최근 6개월간 보고된 내부자 거래가 없습니다.")

        st.divider()

        # [섹션 4] 매집 패턴 스캐너 (OBV 차트)
        st.subheader("📈 가격 vs 거래량(OBV) 다이버전스")
        st.caption("주가는 횡보/하락하는데 노란선(OBV)이 올라간다면, 누군가 몰래 사고 있는 것입니다.")
        
        # 차트 그리기
        hist_df = data['hist']
        fig2 = go.Figure()
        
        # 주가 (캔들) - 축 1
        fig2.add_trace(go.Scatter(
            x=hist_df.index, y=hist_df['Close'], name='주가',
            line=dict(color='gray', width=1)
        ))
        
        # OBV (선) - 축 2
        fig2.add_trace(go.Scatter(
            x=hist_df.index, y=hist_df['OBV'], name='자금 흐름(OBV)',
            line=dict(color='#FFD700', width=2), # 금색
            yaxis='y2'
        ))
        
        fig2.update_layout(
            height=400,
            yaxis=dict(title="주가"),
            yaxis2=dict(title="자금 흐름", overlaying='y', side='right'),
            margin=dict(t=30, b=0, l=0, r=0),
            legend=dict(x=0, y=1.2, orientation="h")
        )
        st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------
# [보너스] 횡보 중 매집 종목 자동 탐색 (예시 리스트)
# ------------------------------------------------------------------
st.divider()
st.subheader("🕵️‍♂️ '횡보 중 매집' 의심 종목 (Beta)")
st.caption("최근 주가는 잠잠한데 거래량이 수상하게 늘어난 종목을 스캔합니다.")

if st.button("스캔 시작 (주요 빅테크 대상)"):
    targets = ["TSLA", "NVDA", "AAPL", "MSFT", "AMD", "PLTR", "SOFI", "IONQ"]
    results = []
    
    progress = st.progress(0)
    for i, t in enumerate(targets):
        try:
            # 간단 분석
            d, _ = analyze_smart_money(t)
            if d and d['score'] >= 60: # 60점 이상만
                results.append({
                    "종목": t, 
                    "점수": d['score'], 
                    "현재가": f"${d['last_price']:.2f}",
                    "이유": ", ".join(d['reasons']) if d['reasons'] else "수급 양호"
                })
        except:
            pass
        progress.progress((i + 1) / len(targets))
        
    if results:
        res_df = pd.DataFrame(results)
        st.dataframe(res_df, use_container_width=True)
    else:
        st.write("현재 기준 포착된 종목이 없습니다.")
