import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="글로벌 젠틀맨", page_icon="👔", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-latest')

st.title("👔 품격 있는 영어 변환기")
raw_text = st.text_area("하고 싶은 말 (대충 한국어나 콩글리시로 적으세요)", height=100)

if st.button("변환 시작 🇺🇸"):
    if raw_text:
        with st.spinner("Translating..."):
            prompt = f"""
            아래 텍스트를 두 가지 스타일의 완벽한 영어로 바꿔줘.
            원문: {raw_text}
            
            ### 1. 🤵 Professional (비즈니스/격식)
            - 매우 정중하고 세련된 표현 사용.
            
            ### 2. 🍺 Casual (친구/편안함)
            - 자연스러운 구어체와 슬랭 사용.
            """
            st.markdown(model.generate_content(prompt).text)
