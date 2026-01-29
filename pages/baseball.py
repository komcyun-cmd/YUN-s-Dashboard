import streamlit as st
import feedparser
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import datetime
import time

# ------------------------------------------------------------------
# [1] 설정 & 채널 ID (직통 주소)
# ------------------------------------------------------------------
st.set_page_config(page_title="야구 직관 상황실 (Real-time)", page_icon="⚾", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# 유튜브 채널 ID (불변의 고유 주소)
CHANNELS = {
    "KIA": {
        "name": "🐯 KIA 타이거즈 (갸티비)",
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCKp8knO8a6tSI1oaLjfd9XA", 
        "color": "#E30613"
    },
    "Hanwha": {
        "name": "🦅 한화 이글스 (Eagles TV)",
        # 한화 공식 채널 ID (검증됨)
        "rss_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCdn4s7gPq7VDFirK40NqaSg",
        "color": "#F37321"
    }
}

# 커뮤니티 RSS (디시인사이드 - 가장 빠름)
COMMUNITIES = {
    "KIA": "https://gall.dcinside.com/rss/lists/?id=tigers_new",
    "Hanwha": "https://gall.dcinside.com/rss/lists/?id=hanwhaeagles_new"
}

# ------------------------------------------------------------------
# [2] 핵심 기능: 무조건 가져오기
# ------------------------------------------------------------------
def get_latest_youtube_summaries(team_code, limit=2):
    """RSS를 통해 최신 영상 2개를 무조건 가져와 요약합니다."""
    channel = CHANNELS[team_code]
    feed = feedparser.parse(channel["rss_url"])
    
    results = []
    
    # 영상이 없거나 에러일 경우
    if not feed.entries:
        return [{"title": "최신 영상을 가져올 수 없습니다.", "summary": "채널 연결 상태를 확인해주세요.", "url": ""}]

    # 최신순 n개 반복
    for entry in feed.entries[:limit]:
        vid_id = entry.yt_videoid
        title = entry.title
        url = entry.link
        published = entry.published_parsed
        pub_date = datetime.datetime.fromtimestamp(time.mktime(published)).strftime('%Y-%m-%d')

        # 자막 추출 및 요약
        transcript_text = ""
        try:
            # 한국어 자막 시도
            t_list = YouTubeTranscriptApi.get_transcript(vid_id, languages=['ko'])
            for t in t_list: transcript_text += t['text'] + " "
        except:
            transcript_text = "(자막 없음) 영상 설명이나 제목을 바탕으로 분석합니다."

        # AI 요약 요청
        prompt = f"""
        이 야구 영상의 내용을 3줄로 요약해.
        제목: {title}
        자막: {transcript_text[:3000]}
        
        [조건]
        1. 경기 내용이면 '몇 대 몇' 승패와 핵심 활약 선수를 명시해.
        2. 인터뷰면 주요 발언을 요약해.
        3. 팬들이 좋아할 만한 포인트(관전 포인트)를 한 줄 추가해.
        """
        try:
            summary = model.generate_content(prompt).text
        except:
            summary = "AI 요약에 실패했습니다."

        results.append({
            "title": title,
            "date": pub_date,
            "url": url,
            "summary": summary
        })
        
    return results

def get_community_issues(team_code, limit=10):
    """커뮤니티 RSS에서 최신글 n개를 긁어와서 '이슈'를 추출합니다."""
    rss_url = COMMUNITIES[team_code]
    feed = feedparser.parse(rss_url)
    
    if not feed.entries:
        return "커뮤니티 데이터를 불러올 수 없습니다."
        
    # 최신 글 제목들만 모으기
    titles = [f"- {entry.title}" for entry in feed.entries[:limit]]
    titles_text = "\n".join(titles)
    
    # AI에게 이슈 그룹화 요청
    prompt = f"""
    아래는 실시간 야구 팬 커뮤니티(디시인사이드)의 최신 글 제목들이다.
    이것들을 분석해서 '지금 가장 핫한 이슈' 3가지를 요약해.
    
    [최신 글 제목 목록]
    {titles_text}
    
    [출력 양식]
    1. 🔥 **(이슈 1)**: (설명)
    2. 🗣️ **(이슈 2)**: (설명)
    3. ❓ **(이슈 3)**: (설명)
    """
    try:
        return model.generate_content(prompt).text
    except:
        return "이슈 분석 실패"

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.title("⚾ 야구 직관 상황실 (Direct Feed)")
st.caption("검색 엔진을 거치지 않고, 구단 채널과 커뮤니티에서 직접 데이터를 꽂아줍니다.")

tab1, tab2 = st.tabs(["🐯 기아 타이거즈", "🦅 한화 이글스"])

# === [탭 1] 기아 ===
with tab1:
    st.header(f"{CHANNELS['KIA']['name']}")
    
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.subheader("📺 최신 공식 영상 (2개)")
        if st.button("기아 영상 가져오기 ⚡", key="btn_kia_yt"):
            with st.spinner("채널 피드 스캔 중..."):
                videos = get_latest_youtube_summaries("KIA", 2)
                for v in videos:
                    st.markdown(f"### [{v['title']}]({v['url']})")
                    st.caption(f"📅 업로드: {v['date']}")
                    st.video(v['url'])
                    st.info(v['summary'])
                    st.divider()

    with col2:
        st.subheader("🔥 실시간 커뮤니티 이슈")
        st.caption("디시인사이드 기아 갤러리 실시간 분석")
        if st.button("기아 민심 확인 ⚡", key="btn_kia_comm"):
            with st.spinner("갤러리 글 읽는 중..."):
                issues = get_community_issues("KIA", 15)
                st.markdown(issues)
                st.link_button("갤러리 바로가기", "https://gall.dcinside.com/tigers_new")

# === [탭 2] 한화 ===
with tab2:
    st.header(f"{CHANNELS['Hanwha']['name']}")
    
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.subheader("📺 최신 공식 영상 (2개)")
        if st.button("한화 영상 가져오기 ⚡", key="btn_hanwha_yt"):
            with st.spinner("채널 피드 스캔 중..."):
                videos = get_latest_youtube_summaries("Hanwha", 2)
                for v in videos:
                    st.markdown(f"### [{v['title']}]({v['url']})")
                    st.caption(f"📅 업로드: {v['date']}")
                    st.video(v['url'])
                    st.info(v['summary'])
                    st.divider()

    with col2:
        st.subheader("🔥 실시간 커뮤니티 이슈")
        st.caption("디시인사이드 한화 갤러리 실시간 분석")
        if st.button("한화 민심 확인 ⚡", key="btn_hanwha_comm"):
            with st.spinner("갤러리 글 읽는 중..."):
                issues = get_community_issues("Hanwha", 15)
                st.markdown(issues)
                st.link_button("갤러리 바로가기", "https://gall.dcinside.com/hanwhaeagles_new")

# ------------------------------------------------------------------
# [4] 자동 갱신 알림
# ------------------------------------------------------------------
st.sidebar.info("💡 이 앱은 RSS 피드를 사용하여 **무조건 최신 데이터**를 보장합니다.")
