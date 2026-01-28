import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="유튜브 인사이트 채굴기", page_icon="⛏️", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
model = genai.GenerativeModel('gemini-flash-latest')

def get_video_id(url):
    query = urlparse(url)
    if query.hostname == 'youtu.be': return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch': return parse_qs(query.query)['v'][0]
        if query.path[:7] == '/embed/': return query.path.split('/')[2]
        if query.path[:3] == '/v/': return query.path.split('/')[2]
    return None

def get_transcript_text(video_id):
    try:
        # 한국어, 영어 순으로 자막 시도
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        full_text = ""
        for entry in transcript_list:
            start_min = int(entry['start'] // 60)
            start_sec = int(entry['start'] % 60)
            full_text += f"[{start_min:02d}:{start_sec:02d}] {entry['text']} "
        return full_text
    except:
        return None

st.title("⛏️ 유튜브 인사이트 채굴기")
url = st.text_input("유튜브 링크 입력")

if st.button("분석 시작 🚀"):
    if url:
        vid = get_video_id(url)
        if vid:
            st.image(f"https://img.youtube.com/vi/{vid}/hqdefault.jpg")
            with st.spinner("자막 추출 및 분석 중..."):
                script = get_transcript_text(vid)
                if script:
                    prompt = f"""
                    다음 유튜브 자막을 분석해줘. 시간 정보 [분:초]를 활용해.
                    [자막] {script[:20000]}
                    
                    [요청]
                    1. 3줄 요약
                    2. 핵심 챕터 (시간 포함)
                    3. 인사이트
                    """
                    try:
                        res = model.generate_content(prompt)
                        st.markdown(res.text)
                    except Exception as e:
                        st.error(f"AI 오류: {e}")
                else:
                    st.error("자막이 없는 영상입니다.")
        else:
            st.error("링크를 확인해주세요.")
