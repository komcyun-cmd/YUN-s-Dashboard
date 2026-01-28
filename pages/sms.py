import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="다정한 닥터", page_icon="📨", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-latest')

st.title("📨 환자 안부 문자 생성기")
st.caption("진료 후, 환자의 마음까지 챙기는 따뜻한 문자 한 통.")

diagnosis = st.text_input("진단명/상황", placeholder="예: 독감 확진, 약 처방함")
patient_info = st.text_input("환자 특이사항", placeholder="예: 30대 직장인, 빨리 낫고 싶어함")

if st.button("문자 작성하기 💌"):
    with st.spinner("다정함을 담는 중..."):
        prompt = f"""
        나는 병원 원장이다. 환자에게 보낼 안부 문자(SMS/카톡)를 작성해줘.
        상황: {diagnosis}
        환자 특징: {patient_info}
        
        [요청사항]
        1. 너무 기계적이지 않고, 따뜻하고 신뢰감 있는 말투.
        2. 주의사항(물 많이 드세요 등)을 자연스럽게 포함.
        3. 길이: 3~4문장 내외.
        """
        st.info(model.generate_content(prompt).text)
        st.caption("👆 복사해서 전송하세요.")
