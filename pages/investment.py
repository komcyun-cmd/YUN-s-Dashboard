import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="투자 청문회", page_icon="📈", layout="centered")

# API 설정 (비밀 금고에서 가져오기)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    # pages/family.py 등 다른 파일에서 쓰던 키 로직이 있다면 그대로 적용됩니다.
    # 만약 에러가 나면 secrets.toml 설정을 확인하세요.
    pass

model = genai.GenerativeModel('gemini-flash-latest')

st.title("📈 워렌 버핏의 투자 청문회")
st.caption("당신의 보유 종목을 3명의 거장이 냉철하게 해부합니다.")

ticker = st.text_input("분석할 종목명 또는 티커 (예: 테슬라, SCHD, 삼성전자)")

if st.button("이사회 소집 🔔"):
    if ticker:
        with st.spinner("거장들이 회의실에 입장하고 있습니다..."):
            prompt = f"""
            너는 지금부터 전설적인 투자자 3명의 페르소나를 연기해야 한다.
            주제: '{ticker}' 주식에 대한 투자 가치 토론.
            
            1. **워렌 버핏**: 가치투자, 해자(Moat), 현금흐름 중시. 보수적.
            2. **피터 린치**: 생활 속 발견, 성장성, 이해하기 쉬운 사업 중시.
            3. **레이 달리오**: 거시경제, 리스크 분산(올웨더), 사이클 중시.
            
            [형식]
            대화체로 서로 논쟁하듯이 작성해라.
            마지막에 3명의 투표 결과(매수/보류/매도)를 요약해라.
            """
            try:
                response = model.generate_content(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"오류: {e}")
