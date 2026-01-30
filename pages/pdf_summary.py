import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import requests
import io

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="PDF 요약 비서", page_icon="📑", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 기능 함수
# ------------------------------------------------------------------
def extract_text_from_pdf(file_obj):
    """업로드된 PDF 파일에서 텍스트 추출"""
    try:
        reader = PdfReader(file_obj)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return None

def extract_text_from_url(url):
    """웹 링크(URL)에서 PDF 다운로드 후 텍스트 추출"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} # 로봇 아님을 증명
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        f = io.BytesIO(response.content)
        return extract_text_from_pdf(f)
    except Exception as e:
        st.error(f"링크 오류: {e}")
        return None

def summarize_pdf(text):
    """AI에게 요약 요청"""
    # 텍스트가 너무 길면(토큰 제한) 앞부분 30,000자만 자름 (Gemini Flash는 넉넉하긴 함)
    truncated_text = text[:50000]
    
    prompt = f"""
    당신은 전문적인 '연구 보조원'이자 '비즈니스 분석가'입니다.
    아래 PDF 텍스트를 읽고 완벽하게 요약 보고서를 작성하세요.
    
    [PDF 내용]
    {truncated_text}
    
    [요청사항]
    1. **한 줄 요약**: 문서의 핵심 주제를 한 문장으로 정의.
    2. **3대 핵심 포인트**: 가장 중요한 내용 3가지.
    3. **상세 요약**: 주요 챕터나 논거를 구조적으로 정리 (불렛포인트 활용).
    4. **인사이트/결론**: 이 문서가 시사하는 바.
    
    톤앤매너: 전문적이고 명료하게. 한국어로 작성.
    """
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"AI 분석 실패: {e}"

# ------------------------------------------------------------------
# [3] 메인 화면
# ------------------------------------------------------------------
st.title("📑 문서(PDF) 3초 요약기")
st.caption("논문, 보고서, 계약서 등 긴 문서를 AI가 대신 읽어드립니다.")

tab1, tab2 = st.tabs(["📂 파일 업로드", "🔗 PDF 링크"])

# [탭 1] 파일 업로드 방식
with tab1:
    uploaded_file = st.file_uploader("PDF 파일을 드래그하거나 선택하세요", type="pdf")
    
    if st.button("파일 분석 시작 🚀", key="btn_file"):
        if uploaded_file:
            with st.spinner("PDF를 읽고 내용을 파악 중입니다..."):
                raw_text = extract_text_from_pdf(uploaded_file)
                if raw_text:
                    st.success(f"텍스트 추출 완료! ({len(raw_text)}자)")
                    result = summarize_pdf(raw_text)
                    st.markdown("### 📝 AI 요약 보고서")
                    st.markdown(result)
                else:
                    st.error("텍스트를 추출할 수 없는 PDF입니다. (이미지 스캔본 등)")
        else:
            st.warning("파일을 먼저 업로드해주세요.")

# [탭 2] 링크 방식
with tab2:
    url_input = st.text_input("PDF가 있는 웹 주소(URL)를 입력하세요")
    st.caption("예: https://example.com/report.pdf")
    
    if st.button("링크 분석 시작 🚀", key="btn_url"):
        if url_input:
            with st.spinner("문서를 다운로드하고 분석 중입니다..."):
                raw_text = extract_text_from_url(url_input)
                if raw_text:
                    st.success(f"다운로드 및 텍스트 추출 완료! ({len(raw_text)}자)")
                    result = summarize_pdf(raw_text)
                    st.markdown("### 📝 AI 요약 보고서")
                    st.markdown(result)
                else:
                    st.error("해당 링크에서 PDF를 읽을 수 없습니다.")
        else:
            st.warning("주소를 입력해주세요.")

