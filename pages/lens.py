import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="닥터의 만물 도감", page_icon="🔍", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash') # 이미지 인식 가능한 모델

st.title("🔍 무엇이든 물어보세요")
st.caption("꽃, 와인 라벨, 처음 보는 물건... 사진을 찍어 올리세요.")

# 카메라 입력 또는 파일 업로드
img_file = st.file_uploader("사진 찍기/올리기", type=["jpg", "png", "jpeg"])

if img_file:
    image = Image.open(img_file)
    st.image(image, caption="분석할 사진", use_container_width=True)
    
    if st.button("이게 뭐야? 🤔"):
        with st.spinner("AI가 눈을 크게 뜨고 보는 중..."):
            try:
                # 이미지와 프롬프트를 함께 보냄
                response = model.generate_content(["이 사진 속 물체가 뭔지 백과사전처럼 설명해줘. 이름, 특징, 유래나 재미있는 사실 포함.", image])
                st.markdown(response.text)
            except Exception as e:
                st.error(f"분석 오류: {e}")
