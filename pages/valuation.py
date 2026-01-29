import streamlit as st
import google.generativeai as genai
import yfinance as yf

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="적정 주가 판독기", page_icon="🧮", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 함수: S-RIM 계산 & 데이터 가져오기
# ------------------------------------------------------------------
def get_stock_data(ticker):
    """yfinance를 통해 주가, BPS, ROE 정보를 가져옵니다."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 데이터 추출 (없으면 0 처리)
        current_price = info.get('currentPrice', 0)
        # 한국 주식은 regularMarketPrice에 있을 수 있음
        if current_price == 0:
            current_price = info.get('regularMarketPreviousClose', 0)
            
        bps = info.get('bookValue', 0)
        
        # ROE는 보통 0.15 (15%) 형태로 들어옴 -> 100 곱해서 %로 변환
        roe = info.get('returnOnEquity', 0) 
        if roe:
            roe = roe * 100
            
        name = info.get('longName', ticker)
        currency = info.get('currency', 'Unknown')
        
        return {
            "name": name,
            "price": current_price,
            "bps": bps,
            "roe": roe,
            "currency": currency
        }
    except Exception as e:
        return None

def calculate_srim(bps, roe, ke):
    """S-RIM 공식: V = BPS + (BPS * (ROE - Ke) / Ke)"""
    try:
        excess_return = roe - ke
        if excess_return <= 0:
            fair_value = bps * (roe / ke) # 보수적 접근
        else:
            fair_value = bps + (bps * excess_return / ke)
        return fair_value
    except:
        return 0

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.title("🧮 적정 주가 판독기 (Auto)")
st.caption("티커만 넣으면 BPS와 ROE를 자동으로 찾아 계산합니다.")

# 세션 상태 초기화 (값 유지를 위해)
if "val_data" not in st.session_state:
    st.session_state.val_data = {"name": "", "price": 0.0, "bps": 0.0, "roe": 10.0}

# 1. 종목 검색 섹션
with st.expander("🔍 종목 데이터 가져오기 (클릭)", expanded=True):
    col_search, col_btn = st.columns([3, 1])
    ticker_input = col_search.text_input("티커 입력 (예: NVDA, 005930.KS)", placeholder="미국: AAPL, 한국: 005930.KS")
    
    if col_btn.button("데이터 수신 📡"):
        if ticker_input:
            with st.spinner(f"{ticker_input} 재무제표 스캔 중..."):
                data = get_stock_data(ticker_input)
                if data:
                    st.session_state.val_data["name"] = data["name"]
                    st.session_state.val_data["price"] = data["price"]
                    st.session_state.val_data["bps"] = data["bps"]
                    # ROE가 None이거나 0이면 기본값 10 유지, 아니면 가져온 값
                    if data["roe"]:
                        st.session_state.val_data["roe"] = round(data["roe"], 2)
                    
                    st.success(f"성공! {data['name']} ({data['currency']}) 데이터를 불러왔습니다.")
                    st.toast("데이터가 입력폼에 채워졌습니다.")
                else:
                    st.error("데이터를 찾을 수 없습니다. 티커를 확인해주세요.")

# 2. 계산 폼 (자동으로 채워지지만 수정 가능)
st.divider()
with st.form("valuation_form"):
    st.subheader("📝 변수 확인 및 조정")
    
    col1, col2 = st.columns(2)
    name = col1.text_input("종목명", value=st.session_state.val_data["name"])
    current_price = col2.number_input("현재 주가", value=float(st.session_state.val_data["price"]), step=10.0)
    
    c1, c2, c3 = st.columns(3)
    # BPS
    bps = c1.number_input("BPS (주당 순자산)", value=float(st.session_state.val_data["bps"]), help="자동 입력됨 (수정 가능)")
    # ROE
    roe = c2.number_input("예상 ROE (%)", value=float(st.session_state.val_data["roe"]), step=0.1, help="AI 예측치 또는 12개월 선행 ROE")
    # 요구수익률 (이건 주관적이라 기본값 8~10%)
    ke = c3.number_input("요구 수익률 (%)", value=8.0, step=0.5, help="최소 이 정도는 벌어야 한다 (보통 8~10%)")
    
    submitted = st.form_submit_button("판독 시작 ⚖️", type="primary")

# 3. 결과 리포트
if submitted:
    if bps > 0 and current_price > 0:
        roe_val = roe / 100
        ke_val = ke / 100
        
        fair_value = calculate_srim(bps, roe_val, ke_val)
        upside = ((fair_value - current_price) / current_price) * 100
        
        st.divider()
        st.subheader(f"📊 {name} 판독 결과")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("현재 주가", f"{current_price:,.0f}")
        m2.metric("적정 가치", f"{fair_value:,.0f}", delta=f"{fair_value-current_price:,.0f}")
        m3.metric("기대 수익률", f"{upside:.2f}%", delta_color="normal" if upside > 0 else "inverse")
        
        # 게이지 바
        ratio = current_price / fair_value if fair_value else 1
        st.progress(min(max(0.5 + (0.5 * (1 - ratio)), 0.0), 1.0))
        st.caption("◀ 고평가 (비쌈) ────────── 적정가 ────────── 저평가 (쌈) ▶")

        # AI 코멘트
        st.divider()
        with st.spinner("투자 의견 작성 중..."):
            prompt = f"""
            종목: {name}
            현재가: {current_price}, 적정가(S-RIM): {fair_value:.2f}
            ROE: {roe}%, 요구수익률: {ke}%
            
            이 결과에 대해 가치투자자 관점에서 3줄로 조언해줘.
            특히 안전마진이 확보되었는지, ROE가 적절한지 평가해줘.
            """
            try:
                st.info(model.generate_content(prompt).text)
            except:
                st.warning("AI 의견을 가져오지 못했습니다.")
    else:
        st.warning("주가와 BPS 정보를 확인해주세요.")
