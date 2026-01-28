import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="결정의 신", page_icon="⚖️", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-latest')

st.title("⚖️ A vs B: 결정의 신")
st.caption("AI가 이성적이고 논리적인 판단을 내려드립니다.")

col1, col2 = st.columns(2)
option_a = col1.text_input("선택지 A", placeholder="예: 테슬라 모델Y 구매")
option_b = col2.text_input("선택지 B", placeholder="예: 그냥 타던 차 계속 타기")
context = st.text_area("고민되는 상황/배경 (예: 현재 차 5년 됨, 현금 여유 조금 있음)")

if st.button("판결을 내려주세요 👨‍⚖️"):
    if option_a and option_b:
        with st.spinner("양측의 입장을 분석 중..."):
            prompt = f"""
            사용자가 두 가지 선택지 중 고민하고 있다. 냉철한 분석가 입장에서 비교해라.
            상황: {context}
            A: {option_a}
            B: {option_b}
            
            [출력 형식]
            1. 🥊 **장단점 비교** (표 형식 추천)
            2. 💯 **점수 매기기** (각 100점 만점)
            3. 🏆 **최종 판결**: 어느 쪽이 더 합리적인 선택인지 단호하게 말해라.
            """
            st.markdown(model.generate_content(prompt).text)
