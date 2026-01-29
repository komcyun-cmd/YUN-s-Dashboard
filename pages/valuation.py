import streamlit as st
import google.generativeai as genai
import yfinance as yf

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="성장주 가치 판독기", page_icon="🚀", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 데이터 수집 및 계산 함수
# ------------------------------------------------------------------
def get_growth_data(ticker):
    """yfinance에서 EPS와 PEG, 성장률 추정치를 가져옵니다."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 1. 현재 주가
        current_price = info.get('currentPrice', 0)
        if current_price == 0:
            current_price = info.get('regularMarketPreviousClose', 0)
            
        # 2. EPS (주당 순이익) - 미래 실적 기준(Forward)이 더 정확함
        eps = info.get('forwardEps', info.get('trailingEps', 0))
        
        # 3. PEG Ratio (주가수익비율 / 성장률)
        # PEG가 있으면 역산해서 시장이 생각하는 성장률을 추정할 수 있음
        peg = info.get('pegRatio', 0)
        
        # 4. 성장률 (Growth Rate) 찾기
        # 애널리스트들의 향후 5년 성장률 추정치가 있으면 베스트
        # 없으면 PEG를 통해 역산하거나 기본값 사용
        growth_rate = 0
        if 'earningsGrowth' in info and info['earningsGrowth']:
             growth_rate = info['earningsGrowth'] * 100 # %로 변환
        
        # 만약 성장률 데이터가 없으면 PEG를 이용해 역산 (PEG = PER / Growth)
        # Growth = PER / PEG
        if growth_rate == 0 and peg > 0 and eps > 0:
            per = current_price / eps
            growth_rate = per / peg

        name = info.get('longName', ticker)
        currency = info.get('currency', 'Unknown')
        
        return {
            "name": name,
            "price": current_price,
            "eps": eps,
            "peg": peg,
            "growth": growth_rate,
            "currency": currency
        }
    except Exception as e:
        return None

def calculate_graham(eps, growth_rate):
    """
    벤자민 그레이엄의 성장주 공식 (수정판)
    V = EPS * (8.5 + 2g)
    * 8.5: 성장이 없는 기업의 기본 PER
    * g: 향후 5-10년 기대 성장률 (%)
    """
    # 보수적인 계산을 위해 성장률 상한선을 둠 (예: 50% 이상은 거품일 가능성)
    adjusted_growth = min(growth_rate, 50) 
    fair_value = eps * (8.5 + (2 * adjusted_growth))
    return fair_value

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.title("🚀 성장주 가치 판독기")
st.caption("벤자민 그레이엄 공식과 PEG 모델을 사용합니다. (테슬라, 엔비디아 추천)")

# 세션 초기화
if "growth_val" not in st.session_state:
    st.session_state.growth_val = {"name": "", "price": 0.0, "eps": 0.0, "growth": 15.0}

# 1. 종목 검색
with st.expander("🔍 종목 데이터 가져오기", expanded=True):
    c1, c2 = st.columns([3, 1])
    ticker = c1.text_input("티커 입력 (예: TSLA, NVDA)", placeholder="TSLA")
    if c2.button("데이터 수신"):
        if ticker:
            with st.spinner("월스트리트 데이터 스캔 중..."):
                d = get_growth_data(ticker)
                if d:
                    st.session_state.growth_val["name"] = d["name"]
                    st.session_state.growth_val["price"] = d["price"]
                    st.session_state.growth_val["eps"] = d["eps"]
                    # 성장률이 너무 터무니없으면(마이너스거나 0) 15% 기본값
                    if d["growth"] > 0:
                        st.session_state.growth_val["growth"] = round(d["growth"], 2)
                    
                    st.success(f"{d['name']} 데이터 로드 완료! (PEG: {d['peg']})")
                else:
                    st.error("데이터를 찾을 수 없습니다.")

# 2. 분석 폼
st.divider()
with st.form("calc_form"):
    st.subheader("📊 변수 확인 (자동 입력됨)")
    st.caption("AI가 가져온 수치입니다. 본인이 생각하는 성장률로 수정해도 됩니다.")
    
    name = st.text_input("종목명", value=st.session_state.growth_val["name"])
    
    col1, col2, col3 = st.columns(3)
    current_price = col1.number_input("현재 주가 ($)", value=float(st.session_state.growth_val["price"]))
    
    # EPS
    eps = col2.number_input("주당 순이익 (EPS)", 
                            value=float(st.session_state.growth_val["eps"]),
                            help="기업이 1주당 버는 돈입니다. (Forward EPS 권장)")
    
    # 성장률
    growth = col3.number_input("연간 성장률 (%)", 
                               value=float(st.session_state.growth_val["growth"]), 
                               step=1.0,
                               help="향후 5년간 매년 몇 %씩 성장할까요? (테슬라는 보통 15~30% 사이)")
    
    submitted = st.form_submit_button("적정 주가 계산하기 🧮", type="primary")

# 3. 결과 리포트
if submitted:
    if eps > 0:
        # 그레이엄 공식 계산
        fair_value = calculate_graham(eps, growth)
        upside = ((fair_value - current_price) / current_price) * 100
        
        # PER 계산
        per = current_price / eps if eps > 0 else 0
        
        st.divider()
        st.subheader(f"🏷️ {name} 판독 결과")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("현재 주가", f"${current_price:,.2f}")
        m2.metric("적정 주가 (그레이엄)", f"${fair_value:,.2f}", 
                  delta=f"{fair_value-current_price:.2f}", delta_color="normal")
        m3.metric("안전 마진 / 괴리율", f"{upside:.2f}%", 
                  delta="저평가 매수 기회" if upside > 0 else "고평가 주의",
                  delta_color="normal" if upside > 0 else "inverse")
        
        # 시각화
        ratio = current_price / fair_value
        st.progress(min(max(0.5 + (0.5 * (1 - ratio)), 0.0), 1.0))
        st.caption(f"비쌈 ◀ ────────── 적정가 (${fair_value:.0f}) ────────── ▶ 쌈")

        # PEG 평가 (피터 린치 스타일)
        # PEG = PER / Growth Rate
        # 1 미만: 저평가, 1.5 적정, 2 초과: 고평가
        implied_peg = per / growth if growth > 0 else 0
        
        st.info(f"""
        💡 **피터 린치의 PEG 진단**
        * 현재 PEG: **{implied_peg:.2f}** (PER {per:.1f} / 성장률 {growth}%)
        * 판정: **{'🟢 저평가 (강력 매수)' if implied_peg < 1 else '🟡 적정 구간' if implied_peg < 2 else '🔴 고평가 (프리미엄 구간)'}**
        """)

        # AI 종합 의견
        st.divider()
        with st.spinner("AI 분석관이 의견을 정리 중입니다..."):
            prompt = f"""
            종목: {name}
            현재가: {current_price}, 적정가(그레이엄 공식): {fair_value:.2f}
            EPS: {eps}, 성장률 가정: {growth}%
            PEG 비율: {implied_peg:.2f}
            
            이 결과에 대해 투자자에게 조언해줘.
            1. 그레이엄 공식과 PEG 관점에서 지금이 매수 타이밍인가?
            2. 이 기업의 리스크는 무엇인가?
            3. 3줄 요약 결론.
            """
            try:
                st.markdown(model.generate_content(prompt).text)
            except:
                pass
    else:
        st.error("EPS가 마이너스인 적자 기업은 이 공식으로 평가할 수 없습니다.")
