import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import datetime

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="최강 야구 비서 (KIA vs Hanwha)", page_icon="⚾", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 검색 및 크롤링 함수들
# ------------------------------------------------------------------

def search_web(query, max_results=3):
    """DuckDuckGo를 통해 웹 검색 결과를 가져옵니다."""
    results = []
    try:
        with DDGS() as ddgs:
            # 안전하게 리스트로 변환
            gen = ddgs.text(query, max_results=max_results)
            results = list(gen)
    except Exception as e:
        st.error(f"검색 오류: {e}")
    return results

def get_video_id(url):
    """유튜브 URL에서 ID 추출"""
    query = urlparse(url)
    if query.hostname == 'youtu.be': return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch': return parse_qs(query.query)['v'][0]
        if query.path[:7] == '/embed/': return query.path.split('/')[2]
        if query.path[:3] == '/v/': return query.path.split('/')[2]
    return None

def get_latest_youtube_summary(team_name):
    """특정 팀의 최신 유튜브 영상을 검색하고 요약합니다."""
    # 1. 최신 영상 검색
    search_query = f"{team_name} 공식 유튜브 최신 하이라이트"
    results = search_web(search_query, max_results=1)
    
    if not results:
        return None, "영상을 찾을 수 없습니다."
        
    video_title = results[0]['title']
    video_url = results[0]['href']
    video_id = get_video_id(video_url)
    
    # 2. 자막 추출
    transcript_text = ""
    try:
        if video_id:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
            for entry in transcript_list:
                transcript_text += entry['text'] + " "
    except:
        transcript_text = "(자막이 없는 영상이거나 접근 불가입니다. 제목과 맥락으로 요약합니다.)"

    # 3. AI 요약
    prompt = f"""
    아래 유튜브 영상에 대한 정보를 바탕으로 3줄 요약을 해줘.
    팀: {team_name}
    영상 제목: {video_title}
    자막 내용: {transcript_text[:5000]}
    
    [형식]
    1. 🎥 **제목**: (제목)
    2. 📝 **핵심 내용**: (내용 요약)
    3. 👀 **관전 포인트**: (팬들이 주목할 부분)
    """
    try:
        summary = model.generate_content(prompt).text
        return video_url, summary
    except Exception as e:
        return video_url, f"AI 요약 실패: {e}"

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.title("⚾ 최강 야구 비서 (KIA & Hanwha)")
st.caption("승부 예측부터 팬 반응까지, 데이터로 즐기는 야구")

tab1, tab2, tab3 = st.tabs(["🔮 오늘 경기 승부예측", "📺 유튜브 최신 요약", "🔥 커뮤니티 이슈"])

# === [탭 1] 승부 예측 ===
with tab1:
    st.header("오늘의 승자는? 🏆")
    
    today = datetime.date.today().strftime("%Y년 %m월 %d일")
    st.info(f"📅 기준일: {today}")
    
    if st.button("라인업 검색 및 승률 분석 🚀", type="primary"):
        with st.spinner("네이버 스포츠와 기사들을 뒤져서 라인업을 찾는 중..."):
            # 1. 정보 수집
            lineup_query = f"{today} 프로야구 기아 한화 선발 라인업 예상"
            pitcher_query = f"{today} 프로야구 기아 한화 선발 투수 전적"
            
            lineup_data = search_web(lineup_query, 3)
            pitcher_data = search_web(pitcher_query, 3)
            
            combined_info = f"[라인업 정보]\n{lineup_data}\n\n[선발투수 정보]\n{pitcher_data}"
            
            # 2. AI 분석
            st.markdown("---")
            prompt = f"""
            너는 20년 경력의 베테랑 야구 분석가다.
            오늘({today}) 기아 타이거즈와 한화 이글스의 경기가 있다고 가정하고(혹은 검색된 정보 바탕으로),
            아래 수집된 정보를 분석해서 승리 확률을 예측해라.
            
            [수집된 웹 정보]
            {combined_info}
            
            만약 정확한 라인업 정보가 없다면, 최근 팀 분위기와 일반적인 주전 선수를 가정해서 시뮬레이션해라.
            
            [출력 양식]
            ## 📊 AI 승부 예측
            
            ### 1. ⚔️ 선발 매치업 평가
            (투수 이름 언급하며 비교)
            
            ### 2. ⚾ 타선 및 변수
            (핵심 타자 컨디션 등)
            
            ### 3. 📈 승리 확률
            * **기아 승리 확률**: OO%
            * **한화 승리 확률**: OO%
            
            ### 4. 🗣️ 한줄 평
            (팬심을 자극하는 멘트)
            """
            try:
                analysis = model.generate_content(prompt).text
                st.markdown(analysis)
                
                # 근거 자료(링크) 표시
                with st.expander("참고한 웹 문서 보기"):
                    for item in lineup_data + pitcher_data:
                        st.markdown(f"- [{item['title']}]({item['href']})")
                        
            except Exception as e:
                st.error("분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

# === [탭 2] 유튜브 요약 ===
with tab2:
    st.header("공식 유튜브 최신 업데이트 🎬")
    
    col_kia, col_hanwha = st.columns(2)
    
    with col_kia:
        st.subheader("🐯 갸티비 (KIA)")
        if st.button("갸티비 요약하기"):
            with st.spinner("영상 찾아오는 중..."):
                url, summary = get_latest_youtube_summary("기아 타이거즈 갸티비")
                if url:
                    st.video(url)
                    st.info(summary)
                else:
                    st.error(summary)
                    
    with col_hanwha:
        st.subheader("🦅 이글스TV (Hanwha)")
        if st.button("이글스TV 요약하기"):
            with st.spinner("영상 찾아오는 중..."):
                url, summary = get_latest_youtube_summary("한화 이글스 이글스TV")
                if url:
                    st.video(url)
                    st.info(summary)
                else:
                    st.error(summary)

# === [탭 3] 커뮤니티 이슈 ===
with tab3:
    st.header("팬 커뮤니티 민심 🔥")
    st.caption("펨코, 엠팍, 디시인사이드 등의 최신 반응을 모아봅니다.")
    
    if st.button("🔥 실시간 이슈 스캔"):
        with st.spinner("야구 팬들의 키보드 배틀 현장을 염탐 중..."):
            # 검색어 설정
            queries = [
                "기아 타이거즈 펨코 포텐",
                "한화 이글스 갤러리 개념글",
                "엠팍 한국야구 타임라인",
                "기아 한화 오늘 경기 반응"
            ]
            
            community_data = ""
            sources = []
            
            for q in queries:
                results = search_web(q, 2)
                for r in results:
                    community_data += f"- {r['title']}: {r['body']}\n"
                    sources.append(r)
            
            # AI 요약
            prompt = f"""
            아래는 야구 팬 커뮤니티의 최신 검색 결과다.
            기아(KIA)와 한화(Hanwha) 각각의 주요 이슈 5가지씩을 요약해라.
            욕설이나 비하 발언은 순화하고, 팬들의 '주요 여론'이 무엇인지 파악해라.
            
            [검색 데이터]
            {community_data}
            
            [출력 양식]
            ### 🐯 기아 타이거즈 이슈 Top 5
            1. 
            2. ...
            
            ### 🦅 한화 이글스 이슈 Top 5
            1.
            2. ...
            
            ### 💡 3줄 요약 (민심 총평)
            """
            try:
                summary = model.generate_content(prompt).text
                st.markdown(summary)
                
                with st.expander("출처 원문 링크"):
                    for s in sources:
                        st.markdown(f"- [{s['title']}]({s['href']})")
            except Exception as e:
                st.error("이슈 요약 실패")
