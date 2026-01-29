import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

st.set_page_config(page_title="유튜브 인사이트 채굴기", page_icon="⛏️", layout="centered")

# API 키 설정
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

# [핵심 수정] 자막 가져오기 기능 강화 (번역 기능 추가)
def get_transcript_text(video_id):
    try:
        # 1. 해당 영상의 모든 자막 리스트를 가져옵니다.
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        transcript = None
        
        # 2. 우선순위: 한국어(수동) -> 한국어(자동) -> 영어 -> 아무거나
        try:
            # 한국어 자막이 있는지 시도 (수동/자동 포함)
            transcript = transcript_list.find_transcript(['ko'])
        except:
            # 한국어가 없으면, '번역 가능한' 아무 자막이나 가져옵니다.
            try:
                # 영어 자막 시도
                transcript = transcript_list.find_transcript(['en'])
            except:
                # 영여도 없으면, 리스트의 첫 번째 자막(보통 자동생성)을 가져옴
                for t in transcript_list:
                    transcript = t
                    break
            
            # 3. 가져온 자막을 한국어로 번역합니다. (이게 핵심!)
            if transcript:
                transcript = transcript.translate('ko')

        # 4. 자막 텍스트 추출 및 포맷팅
        if transcript:
            result = transcript.fetch()
            full_text = ""
            for entry in result:
                start_min = int(entry['start'] // 60)
                start_sec = int(entry['start'] % 60)
                full_text += f"[{start_min:02d}:{start_sec:02d}] {entry['text']} "
            return full_text
            
        return None

    except Exception as e:
        # st.error(f"자막 추출 실패 상세: {e}") # 디버깅용
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
                    # 너무 긴 자막 자르기 (토큰 제한 방지)
                    truncated_script = script[:25000] 
                    
                    prompt = f"""
                    다음 유튜브 자막을 분석해줘. 시간 정보 [분:초]를 활용해.
                    [자막 데이터]
                    {truncated_script}
                    
                    [요청사항]
                    1. 3줄 요약 (명확하게)
                    2. 핵심 챕터 (타임스탬프 필수 포함)
                    3. 이 영상에서 얻을 수 있는 인사이트
                    """
                    try:
                        res = model.generate_content(prompt)
                        st.markdown(res.text)
                    except Exception as e:
                        st.error(f"AI 분석 중 오류 발생: {e}")
                else:
                    st.error("이 영상은 자막(자동생성 포함)을 지원하지 않아 분석할 수 없습니다. 😭")
                    st.info("Tip: '동영상' 탭이 아닌 'Shorts'나 자막이 아예 없는 뮤직비디오는 안 될 수 있습니다.")
        else:
            st.error("올바른 유튜브 링크가 아닙니다.")
