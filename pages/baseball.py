import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import datetime

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="최강 야구 비서 (Live)", page_icon="⚾", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 검색 및 크롤링 함수들 (최신성 강화)
# ------------------------------------------------------------------

def search_web_fresh(query, max_results=3, time_limit='d'):
    """
    DuckDuckGo 검색 (시간 제한 옵션 추가)
    time_limit: 'd' (하루), 'w' (일주일), 'm' (한달)
    """
    results = []
    try:
        with DDGS() as ddgs:
            # timelimit='d'를 통해 지난 24시간 내 글만 가져옴
            gen = ddgs.text(query, max_results=max_results, timelimit=time_limit)
            results = list(gen)
    except Exception as e:
        # st.error(f"검색 오류: {e}") # 사용자에게 에러 보여주지 않음
        pass
    return results

def get_video_id(url):
    """유튜브 URL에서 ID 추출"""
    if not url: return None
    try:
        query = urlparse(url)
        if query.hostname == 'youtu.be': return query.path[1:]
        if query.hostname in ('www.youtube.com', 'youtube.com'):
            if query.path == '/watch': return parse_qs(query.query)['v'][0]
            if query.path[:7] == '/embed/': return query.path.split('/')[2]
            if query.path[:3] == '/v/': return query.path.split('/')[2]
    except:
        return None
    return None

def get_latest_youtube_summary(team_name):
    """팀의 최신 영상 검색 (일주일 내) 및 요약 시도"""
    # 1. 최신 영상 검색 (timelimit='w' : 최근 일주일)
    search_query = f"site:youtube.com {team_name} 공식 하이라이트"
    results = search_web_fresh(search_query, max_results=1, time_limit='w')
    
    if not results:
        return None, None, "최근 1주일 내 올라온 공식 영상을 찾지 못했습니다."
        
    video_title = results[0]['title']
    video_url = results[0]['href']
    video_desc = results[0]['body']
    video_id = get_video_id(video_url)
    
    # 2. 자막 추출 시도
    transcript_text = ""
    has_transcript = False
    
    if video_id:
        try:
            # 한국어 자막 우선 시도
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
            for entry in transcript_list:
                transcript_text += entry['text'] + " "
            has_transcript = True
        except:
            # 자막이 없으면 제목과 검색된 설명(body)만 사용
            transcript_text = f"자막 없음. 제목: {video_title}, 설명: {video_desc}"
            has_transcript = False

    # 3. AI 요약
    prompt = f"""
    아래 유튜브 영상 정보를 바탕으로 요약해줘.
    자막이 없다면 제목과 설명을 바탕으로 추론해.
    
    [영상 정보]
    - 팀: {team_name}
    - 제목: {video_title}
    - 자막/내용: {transcript_text[:3000]}
    
    [요청사항]
    1. 이 영상이 언제/누구와의 경기인지 파악해줘. (정보가 없으면 '알 수 없음' 표기)
    2. 3줄 요약해줘.
    3. {'(자막이 없어 정확도가 낮을 수 있음)' if not has_transcript else ''}
    """
    try:
        summary = model.generate_content(prompt).text
        return video_url, video_title, summary
    except Exception as e:
        return video_url, video_title, f"AI 요약 실패: {e}"

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.title("⚾ 최강 야구 비서 (Live)")
st.caption("지난 24시간 이내의 살아있는 데이터만 가져옵니다.")

tab1, tab2, tab3 = st.tabs(["🔮 오늘 승부예측", "📺 최신 유튜브", "🔥 실시간 커뮤니티"])

# === [탭 1] 승부 예측 (오늘 데이터 강제) ===
with tab1:
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    st.header(f"오늘({today_str})의 승부 🏆")
    
    if st.button("라인업 확인 & 승률 분석 🚀", type="primary"):
        with st.spinner("오늘자 기사 검색 중 (지난 24시간)..."):
            # 'd' 옵션으로 오늘 기사만 검색
            q1 = f"기아 타이거즈 한화 이글스 오늘 선발 라인업 {today_str}"
            q2 = f"기아 한화 오늘 경기 프리뷰 {today_str}"
            
            # 검색 결과 수집
            res1 = search_web_fresh(q1, 3, 'd')
            res2 = search_web_fresh(q2, 3, 'd')
            
            combined_text = ""
            for r in res1 + res2:
                combined_text += f"- 제목: {r['title']}\n- 내용: {r['body']}\n"
            
            if not combined_text:
                st.warning("오늘자 관련 기사를 찾지 못했습니다. 경기가 없는 날일 수 있습니다.")
            else:
                # AI 분석
                st.divider()
                prompt = f"""
                너는 야구 전문 분석가다. 아래 '오늘자 검색 결과'를 바탕으로 분석해라.
                
                [검색된 최신 기사/정보]
                {combined_text}
                
                [분석 요청]
                1. 오늘 선발 투수와 주요 타자 라인업을 정리해라. (정보가 없으면 '확인되지 않음'이라고 말해)
                2. 양 팀의 최근 분위기와 투수 전력을 비교해라.
                3. **기아 승리 확률 vs 한화 승리 확률**을 %로 예측하고 그 근거를 대라.
                """
                try:
                    analysis = model.generate_content(prompt).text
                    st.markdown(analysis)
                    
                    with st.expander("참고한 최신 기사"):
                        for r in res1 + res2:
                            st.markdown(f"- [{r['title']}]({r['href']})")
                except:
                    st.error("AI 분석 중 오류가 발생했습니다.")

# === [탭 2] 유튜브 (예외처리 강화) ===
with tab2:
    st.header("공식 채널 최신 업데이트 🎬")
    st.caption("최근 1주일 내 올라온 영상을 찾습니다.")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🐯 갸티비 (KIA)")
        if st.button("갸티비 조회"):
            with st.spinner("영상 찾는 중..."):
                url, title, summary = get_latest_youtube_summary("기아 타이거즈 갸티비")
                if url:
                    st.video(url)
                    st.markdown(f"**{title}**")
                    st.info(summary)
                else:
                    st.warning(summary) # 에러 메시지 출력

    with c2:
        st.subheader("🦅 이글스TV (Hanwha)")
        if st.button("이글스TV 조회"):
            with st.spinner("영상 찾는 중..."):
                url, title, summary = get_latest_youtube_summary("한화 이글스 이글스TV")
                if url:
                    st.video(url)
                    st.markdown(f"**{title}**")
                    st.info(summary)
                else:
                    st.warning(summary)

# === [탭 3] 커뮤니티 (시간 제한 'd' 적용) ===
with tab3:
    st.header("실시간 팬 민심 (24시간 이내) 🔥")
    
    if st.button("🔥 실시간 이슈 스캔"):
        with st.spinner("펨코, 엠팍, 디시 등 주요 커뮤니티 스캔 중..."):
            # 검색어에 '오늘', '실시간' 등을 포함하고 timelimit='d' 적용
            queries = [
                "기아 타이거즈 펨코 포텐 오늘",
                "한화 이글스 갤러리 개념글 오늘",
                "엠팍 한국야구 오늘 경기 반응",
                "야구부장 크보 핵인싸 오늘"
            ]
            
            raw_data = ""
            valid_sources = []
            
            for q in queries:
                # timelimit='d' (Day) 핵심!
                results = search_web_fresh(q, max_results=2, time_limit='d')
                for r in results:
                    raw_data += f"[{r['title']}] - {r['body']}\n"
                    valid_sources.append(r)
            
            if not raw_data:
                st.warning("최근 24시간 내 화제가 된 글을 찾기 어렵습니다.")
            else:
                prompt = f"""
                아래는 '오늘' 올라온 야구 팬 커뮤니티 글들이다.
                옛날 이야기는 무시하고, **지금 당장** 팬들이 이야기하는 주제를 뽑아라.
                
                [검색 데이터]
                {raw_data}
                
                [출력]
                1. 🐯 **기아 팬들 주요 반응 3가지**
                2. 🦅 **한화 팬들 주요 반응 3가지**
                3. ⚡ **오늘의 핫 이슈** (트레이드, 부상, 경기 결과 등)
                """
                try:
                    summary = model.generate_content(prompt).text
                    st.markdown(summary)
                    
                    with st.expander("출처 (지난 24시간 게시물)"):
                        for s in valid_sources:
                            st.markdown(f"- [{s['title']}]({s['href']})")
                except:
                    st.error("요약 실패")
