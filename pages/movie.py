import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="시네마 컨시어지", page_icon="🎬", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-latest')

st.title("🎬 우리 가족 무비 나이트")
st.caption("가족들의 요구사항을 모두 적어주세요. 교집합을 찾아냅니다.")

c1, c2 = st.columns(2)
dad = c1.text_input("아빠 취향", "역사물, 너무 가벼운 건 싫음")
mom = c2.text_input("엄마 취향", "잔인한 거 질색, 따뜻한 거")
son = c1.text_input("아들 취향", "액션, SF")
daughter = c2.text_input("딸 취향", "영상미 좋은 거, 티모시 샬라메")

if st.button("영화 골라줘 🍿"):
    with st.spinner("OTT를 뒤지는 중..."):
        prompt = f"""
        우리 가족 4명이 같이 볼 영화를 추천해줘.
        [취향]
        아빠: {dad}
        엄마: {mom}
        아들: {son}
        딸: {daughter}
        
        이 모든 조건을 최대한 만족하는 영화 3편을 추천하고,
        각 영화가 어느 OTT(넷플릭스, 디즈니+, 왓챠 등)에 있는지 한국 기준으로 알려줘.
        """
        st.markdown(model.generate_content(prompt).text)
