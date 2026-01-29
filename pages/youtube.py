import streamlit as st
import google.generativeai as genai
import yt_dlp
import requests
import json
import re

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="유튜브 인사이트 채굴기 (Pro)", page_icon="⛏️", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 강력한 자막 추출 함수 (yt-dlp 사용)
# ------------------------------------------------------------------
def get_transcript_with_ytdlp(video_url):
    """
    yt-dlp를 사용하여 유튜브의 자동생성 자막(스크립트)을 강제로 추출합니다.
    IP 차단을 우회하고 더 강력하게 데이터를 가져옵니다.
    """
    ydl_opts = {
        'skip_download': True,      # 영상은 다운로드 안 함
        'writeautomaticsub': True,  # 자동 생성 자막 가져오기
        'writesubtitles': True,     # 수동 자막도 가져오기
        'subtitleslangs': ['ko', 'en'], # 한국어 우선, 없으면 영어
        'quiet': True,              # 로그 출력 끄기
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. 영상 정보 추출
            info = ydl.extract_info(video_url, download=False)
            
            # 2. 자막 데이터 찾기 (수동 -> 자동 순서)
            subs = info.get('subtitles', {})
            auto_subs = info.get('automatic_captions', {})
            
            # 우선순위: 한국어(수동) > 한국어(자동) > 영어(수동) > 영어(자동)
            target_sub = None
            
            # (1) 한국어 찾기
            if 'ko' in subs: target_sub = subs['ko']
            elif 'ko' in auto_subs: target_sub = auto_subs['ko']
            # (2) 영어 찾기
            elif 'en' in subs: target_sub = subs['en']
            elif 'en' in auto_subs: target_sub = auto_subs['en']
            
            # (3) 아무거나 찾기 (위에서 못 찾았을 경우)
            if not target_sub:
                # 사용 가능한 첫 번째 언어라도 가져옴
                if auto_subs:
                    first_lang = list(auto_subs.keys())[0]
                    target_sub = auto_subs[first_lang]

            if not target_sub:
                return None, "자막 트랙을 찾을 수 없습니다."

            # 3. JSON3 포맷의 자막 URL 찾기 (가장 파싱하기 좋음)
            json3_url = None
            for fmt in target_sub:
                if fmt.get('ext') == 'json3':
                    json3_url = fmt['url']
                    break
            
            if not json3_url:
                # JSON3가 없으면 첫 번째 포맷 사용
                json3_url = target_sub[0]['url']

            # 4. 자막 내용 다운로드 및 파싱
            response = requests.get(json3_url)
            caption_data = response.json()
            
            full_text = ""
            events = caption_data.get('events', [])
            
            for event in events:
                # 시간 정보 (밀리초 -> 분:초)
                start_ms = event.get('tStartMs', 0)
                start_sec = int(start_ms / 1000)
                m, s = divmod(start_sec, 60)
                time_str = f"[{m:02d}:{s:02d}]"
                
                # 텍스트 합치기
                segs = event.get('segs', [])
                text = "".join([seg.get('utf8', '') for seg in segs]).strip()
                
                if text:
                    full_text += f"{time_str} {text} "
            
            return full_text, None

    except Exception as e:
        return None, str(e)

# ------------------------------------------------------------------
# [3] 메인 화면
# ------------------------------------------------------------------
st.title("⛏️ 유튜브 인사이트 채굴기 (Pro)")
st.caption("기존 방식이 안 될 때 사용하는 강력한 버전입니다.")

url = st.text_input("유튜브 링크 입력 (공유 버튼 -> 링크 복사)")

if st.button("분석 시작 🚀", type="primary"):
    if url:
        # 영상 ID 추출 (썸네일용)
        video_id = None
        if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be" in url: video_id = url.split("/")[-1].split("?")[0]
        
        if video_id:
            st.image(f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg", width=300)
        
        with st.spinner("⛏️ 영상의 스크립트를 강제로 채굴 중입니다... (약간의 시간이 걸립니다)"):
            script, error = get_transcript_with_ytdlp(url)
            
            if script:
                # 너무 길면 자르기 (AI 토큰 한계 고려)
                final_script = script[:30000]
                
                prompt = f"""
                다음은 유튜브 영상의 자막 스크립트야. 내용을 완벽하게 분석해줘.
                
                [스크립트 데이터]
                {final_script}
                
                [요청사항]
                1. **3줄 요약**: 바쁜 나를 위해 핵심만 딱 요약해.
                2. **챕터별 요약**: 타임스탬프([00:00])를 포함해서 주요 내용을 정리해.
                3. **핵심 인사이트**: 이 영상에서 배울 수 있는 점이나 결론.
                """
                
                try:
                    st.success("자막 추출 성공! AI 분석을 시작합니다... 🧠")
                    res = model.generate_content(prompt)
                    st.markdown("### 📊 분석 결과")
                    st.markdown(res.text)
                    
                    with st.expander("📜 원본 스크립트 보기"):
                        st.text(script)
                        
                except Exception as e:
                    st.error(f"AI 분석 오류: {e}")
            else:
                st.error("분석 실패 😭")
                st.warning(f"이유: {error}")
                st.info("Tip: 링크가 정확한지, 혹은 유료 멤버십 영상인지 확인해주세요.")
    else:
        st.warning("링크를 입력해주세요.")
