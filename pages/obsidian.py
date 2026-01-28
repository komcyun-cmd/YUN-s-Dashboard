import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="지식 수집기", page_icon="🧠", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-latest')

# 간단한 텍스트 추출기
def get_text_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 스크립트 제거
        for s in soup(['script', 'style']): s.decompose()
        return soup.get_text()[:10000] # 너무 길면 자름
    except Exception as e:
        return f"오류: {e}"

st.title("🧠 옵시디언 지식 수집기")
url = st.text_input("🔗 스크랩할 기사/칼럼 링크")

if st.button("변환 시작 ⚡"):
    if url:
        with st.spinner("읽고 요약 중..."):
            raw_text = get_text_from_url(url)
            prompt = f"""
            너는 지식 관리 전문가다. 아래 텍스트를 Obsidian 노트용 Markdown 형식으로 정리해라.
            
            [소스 텍스트]
            {raw_text}
            
            [출력 형식]
            # (제목)
            
            ## 📌 3줄 요약
            - 
            - 
            
            ## 💡 핵심 인사이트
            (본문 내용 요약)
            
            ## 🏷️ 태그
            #키워드1 #키워드2
            
            ---
            출처: {url}
            """
            result = model.generate_content(prompt).text
            st.markdown(result)
            st.code(result, language="markdown") # 복사하기 좋게 코드 블록 제공
            st.caption("👆 위 코드를 복사해서 옵시디언에 붙여넣으세요.")
