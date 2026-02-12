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
# [2] 뉴스 가져오기 (중복 제거 기능 추가)
# ------------------------------------------------------------------
def get_kbo_news():
    # 검색어 최적화: 'KBO'만 쓰면 너무 광범위해서 '프로야구' 조합
    rss_url = "https://news.google.com/rss/search?q=KBO+프로야구+news&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    
    unique_news = []
    seen_titles = set() # 이미 본 제목을 저장하는 집합
    
    for entry in feed.entries:
        # 1. 제목 전처리 (기사 끝에 붙는 언론사 이름 제거 등)
        clean_title = entry.title.split("-")[0].strip()
        
        # 2. 중복 검사 (비슷한 제목이면 패스)
        # 제목 앞 10글자가 같으면 같은 기사로 간주 (강력한 필터링)
        title_signature = clean_title[:10]
        
        if title_signature not in seen_titles:
            unique_news.append({
                "title": clean_title, # 깔끔해진 제목 사용
                "link": entry.link,
                "published": entry.published,
                "source": entry.source.title if 'source' in entry else "뉴스"
            })
            seen_titles.add(title_signature)
            
        if len(unique_news) >= 10: # 10개만 채우면 중단
            break
            
    return unique_news

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------

# 상단: 퀵 링크 (PC 버전 링크로 교체하여 오류 해결)
st.info("👇 경기 일정 및 하이라이트는 아래 버튼으로 확인하세요!")
c1, c2, c3 = st.columns(3)

with c1:
    # 네이버 스포츠 PC 버전 (모바일 버전보다 안정적)
    st.link_button("📅 경기 일정/결과", "https://sports.news.naver.com/kbaseball/schedule/index.nhn", use_container_width=True)
with c2:
    st.link_button("🏆 실시간 순위", "https://sports.news.naver.com/kbaseball/record/index.nhn", use_container_width=True)
with c3:
    # 하이라이트가 안 나오던 문제 해결 -> 유튜브 검색 결과로 직행 (가장 확실함)
    st.link_button("📺 하이라이트 (YouTube)", "https://www.youtube.com/results?search_query=KBO+하이라이트+오늘", use_container_width=True)

st.divider()

# 메인: 뉴스 브리핑
col_head, col_btn = st.columns([4, 1])
with col_head:
    st.subheader("📰 오늘의 헤드라인 (Clean Ver.)")
with col_btn:
    if st.button("새로고침 🔄"):
        st.rerun()

with st.spinner("중복된 기사를 걷어내고 핵심만 가져오는 중..."):
    try:
        news_items = get_kbo_news()
        
        if news_items:
            for item in news_items:
                with st.container(border=True):
                    # 제목 클릭 시 링크 이동
                    st.markdown(f"##### [{item['title']}]({item['link']})")
                    
                    # 날짜와 출처 표시
                    try:
                        parsed_date = datetime.datetime.strptime(item['published'], "%a, %d %b %Y %H:%M:%S %Z")
                        date_str = parsed_date.strftime("%m월 %d일 %H:%M")
                    except:
                        date_str = "최근"
                        
                    st.caption(f"🕒 {date_str} | 🗞️ {item['source']}")
        else:
            st.warning("지금은 새로운 뉴스가 없습니다. 잠시 후 다시 시도해주세요.")
            
    except Exception as e:
        st.error(f"뉴스 로딩 실패: {e}")
