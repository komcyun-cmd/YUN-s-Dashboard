import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="꿈 분석실", page_icon="🔮", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-latest')

st.title("🔮 심리학적 꿈 분석")
st.caption("단순한 미신이 아닌, 당신의 무의식을 읽어드립니다.")

dream_content = st.text_area("어젯밤 꾼 꿈 내용을 적어주세요.", height=100)

if st.button("해석하기 🧠"):
    if dream_content:
        with st.spinner("무의식의 심연을 들여다보는 중..."):
            prompt = f"""
            너는 심리학자(프로이트 및 융 학파)이다. 
            사용자의 꿈 내용을 분석해서 그 내면에 숨겨진 욕망, 불안, 혹은 현재의 심리 상태를 설명해줘.
            (점쟁이처럼 말하지 말고, 상담가처럼 통찰력 있게 말해라.)
            
            꿈 내용: {dream_content}
            """
            st.markdown(model.generate_content(prompt).text)
