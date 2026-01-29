import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import plotly.graph_objects as go
import plotly.express as px

# ------------------------------------------------------------------
# [1] 설정 & API
# ------------------------------------------------------------------
st.set_page_config(page_title="🇺🇸 월스트리트 인사이드 (Special)", page_icon="🗽", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# --- 데이터 정의 ---
# 1. 주요 지수
INDICES = {
    "^GSPC": "S&P 500",
    "^IXIC": "나스닥",
    "^SOX": "반도체",
    "^VIX": "공포지수(VIX)",
    "KRW=X": "원/달러 환율"
}

# 2. 집중 분석 대상
SPECIALS = {
    "TSLA": "테슬라 (Tesla)",
    "BTC-USD": "비트코인 (Bitcoin)",
    "GOOGL": "구글 (Alphabet)"
}

# 3. 히트맵용
SECTOR_MAP = {
    "Big Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"],
    "Semi & AI": ["NVDA", "AMD", "AVGO", "TSM", "INTC"],
    "Auto": ["TSLA", "RIVN", "F", "GM"],
    "Finance": ["JPM", "V", "MA", "BAC"],
    "Health": ["LLY", "JNJ", "PFE"]
}

# ------------------------------------------------------------------
# [2] 데이터 수집
# ------------------------------------------------------------------
@st.cache_data(ttl=1800)
def get_all_market_data():
    all_tickers = list(INDICES.keys()) + list(SPECIALS.keys()) + [t for cat in SECTOR_MAP.values() for t in cat]
    all_tickers = list(set(all_tickers))
    
    data = yf.download(all_tickers, period="5d", progress=False)['Close']
    
    summary = {}
    for t in all_tickers:
        if t in data.columns:
            series = data[t].dropna()
            if len(series) >= 2:
                curr = series.iloc[-1]
                prev = series.iloc[-2]
                pct = ((curr - prev) / prev) * 100
                summary[t] = {"price": curr, "change": pct}
            else:
                summary[t] = {"price": 0, "change": 0}
        else:
            summary[t] = {"price": 0, "change": 0}
            
    heatmap_data = []
    for sector, symbols in SECTOR_MAP.items():
        for s in symbols:
            if s in summary:
                heatmap_data.append({
                    "Sector": sector,
                    "Ticker": s,
                    "Change": summary[s]['change'],
                    "Price": summary[s]['price']
                })
    
    return summary, pd.DataFrame(heatmap_data)

def get_special_news():
    news_dict = {}
    for ticker in SPECIALS.keys():
        try:
            items = yf.Ticker(ticker).news[:1]
            if items:
                news_dict[ticker] = items[0]['title']
            else:
                news_dict[ticker] = "뉴스 없음"
        except:
            news_dict[ticker] = "로딩 실패"
    return news_dict

# ------------------------------------------------------------------
# [3] AI 브리핑
# ------------------------------------------------------------------
def generate_combined_brief(summary, news_map):
    vix = summary.get("^VIX", {}).get('price', 0)
    usd = summary.get("KRW=X", {}).get('price', 0)
    
    tsla = summary.get("TSLA", {})
    btc = summary.get("BTC-USD", {})
    googl = summary.get("GOOGL", {})
    
    prompt = f"""
    당신은 월스트리트 수석 전략가입니다. 
    한국 투자자를 위해 [미국 증시 마감 시황]과 [3대 관심 종목]을 브리핑하세요.
    
    [1. 시장 지표]
    - 나스닥 등락: {summary.get('^IXIC', {}).get('change', 0):.2f}%
    - 공포지수(VIX): {vix:.2f} (높으면 공포)
    - 환율: {usd:.1f}원
    
    [2. Special 3 종목]
    - 테슬라: {tsla.get('change', 0):.2f}% (뉴스: {news_map.get('TSLA')})
    - 비트코인: {btc.get('change', 0):.2f}% (뉴스: {news_map.get('BTC-USD')})
    - 구글: {googl.get('change', 0):.2f}% (뉴스: {news_map.get('GOOGL')})
    
    [작성 요청]
    1. **시장 총평**: 거시경제/금리 관점에서 시장 분위기 요약 (국장 영향 포함).
    2. **테슬라 & 2차전지**: 주가 원인 분석 + 한국 2차전지주(에코프로 등) 영향.
    3. **구글 & AI**: 빅테크 AI 흐름 분석 + 한국 반도체/SW주 영향.
    4. **비트코인**: 가상자산 시장 분위기.
    """
    try:
        return model.generate_content(prompt).text
    except:
        return "브리핑 생성 실패"

# ------------------------------------------------------------------
# [4] 메인 화면
# ------------------------------------------------------------------
st.title("🇺🇸 월스트리트 인사이드 (V2 + Special)")
st.caption("시장 전체 흐름(V2)과 테슬라·비트코인·구글을 집중 분석합니다.")

with st.spinner("뉴욕 증시 및 3대장 데이터 분석 중... 🔍"):
    summary, heat_df = get_all_market_data()
    special_news = get_special_news()

if not summary:
    st.error("데이터 로딩 실패")
else:
    # 1. 핵심 지표
    st.header("1️⃣ 핵심 지표 (Key Metrics)")
    c1, c2, c3, c4, c5 = st.columns(5)
    keys = ["^GSPC", "^IXIC", "^SOX", "^VIX", "KRW=X"]
    
    for i, k in enumerate(keys):
        info = summary.get(k, {})
        with [c1, c2, c3, c4, c5][i]:
            inv = "inverse" if k in ["^VIX", "KRW=X"] else "normal"
            st.metric(INDICES[k], f"{info.get('price',0):.2f}", f"{info.get('change',0):.2f}%", delta_color=inv)
            
    st.divider()

    # 2. Special 3 집중 분석
    st.header("2️⃣ 🔥 오늘의 3대장 (Focus)")
    sc1, sc2, sc3 = st.columns(3)
    
    with sc1:
        t = summary.get("TSLA", {})
        st.subheader("🚗 Tesla")
        st.metric("등락률", f"${t.get('price',0):.2f}", f"{t.get('change',0):.2f}%")
        st.caption(special_news.get("TSLA", "-"))

    with sc2:
        b = summary.get("BTC-USD", {})
        st.subheader("🪙 Bitcoin")
        st.metric("현재가", f"${b.get('price',0):,.2f}", f"{b.get('change',0):.2f}%")
        st.caption(special_news.get("BTC-USD", "-"))
        
    with sc3:
        g = summary.get("GOOGL", {})
        st.subheader("🔎 Google")
        st.metric("등락률", f"${g.get('price',0):.2f}", f"{g.get('change',0):.2f}%")
        st.caption(special_news.get("GOOGL", "-"))

    st.markdown("##### 💡 AI 심층 브리핑")
    if "final_brief" not in st.session_state:
        st.session_state.final_brief = generate_combined_brief(summary, special_news)
        
    st.info(st.session_state.final_brief)
    
    if st.button("🔄 브리핑 새로고침"):
        del st.session_state.final_brief
        st.rerun()

    st.divider()

    # 3. 마켓 히트맵 (수정됨)
    st.header("3️⃣ 섹터별 히트맵")
    
    fig = px.treemap(
        heat_df, 
        path=[px.Constant("Market"), 'Sector', 'Ticker'], 
        values='Price', 
        color='Change',
        color_continuous_scale='RdYlGn', # 여기가 'RdGn'에서 'RdYlGn'으로 수정됨
        color_continuous_midpoint=0
    )
    fig.update_layout(height=450, margin=dict(t=0,l=0,r=0,b=0))
    st.plotly_chart(fig, use_container_width=True)
