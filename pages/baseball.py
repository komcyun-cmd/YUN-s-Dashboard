import streamlit as st
import feedparser
import pandas as pd
import datetime

# ------------------------------------------------------------------
# [1] 페이지 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="KBO 프로야구 브리핑", page_icon="⚾", layout="centered")

st.title("⚾ KBO 프로야구 Daily")
st.caption(f"오늘({datetime.date.today().strftime('%m월 %d일')})의 그라운드 소식입니다.")

# ------------------------------------------------------------------
# [2] 뉴스 가져오기 함수 (RSS)
# ------------------------------------------------------------------
def get_kbo_news():
    # 구글 뉴스에서 'KBO 프로야구' 키워드로 검색된 RSS 피드
    rss_url = "https://news.google.com/rss/search?q=KBO+프로야구&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    
    news_list = []
    for entry in feed.entries[:10]: # 최신 10개만
        news_list.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published
        })
    return news_list

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------

# 상단: 퀵 링크 (네이버 스포츠 연동)
st.info("👇 경기 일정 및 실시간 순위는 아래 버튼으로 확인하세요!")
c1, c2, c3 = st.columns(3)
with c1:
    st.link_button("📅 오늘 경기 일정", "https://m.sports.naver.com/kbaseball/schedule/index", use_container_width=True)
with c2:
    st.link_button("🏆 실시간 순위", "https://m.sports.naver.com/kbaseball/record/index", use_container_width=True)
with c3:
    st.link_button("📺 하이라이트 영상", "https://m.sports.naver.com/kbaseball/video/index", use_container_width=True)

st.divider()

# 메인: 뉴스 브리핑
st.subheader("📰 실시간 헤드라인")

if st.button("뉴스 새로고침 🔄"):
    st.rerun()

with st.spinner("덕아웃에서 소식을 가져오는 중..."):
    try:
        news_items = get_kbo_news()
        
        if news_items:
            for item in news_items:
                with st.container(border=True):
                    # 뉴스 제목 및 링크
                    st.markdown(f"### [{item['title']}]({item['link']})")
                    # 날짜 정리 (복잡한 포맷을 간단하게)
                    try:
                        parsed_date = datetime.datetime.strptime(item['published'], "%a, %d %b %Y %H:%M:%S %Z")
                        date_str = parsed_date.strftime("%m월 %d일 %H:%M")
                    except:
                        date_str = "방금 전"
                        
                    st.caption(f"🕒 {date_str} | Google News")
        else:
            st.warning("현재 가져올 뉴스가 없습니다.")
            
    except Exception as e:
        st.error(f"뉴스 로딩 실패: {e}")
        st.info("Tip: `requirements.txt`에 `feedparser`가 설치되어 있는지 확인해주세요.")
