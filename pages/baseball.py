import streamlit as st
import feedparser
import google.generativeai as genai
import datetime
import json
import ast
import re

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="KBO 프로야구 브리핑", page_icon="⚾", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

st.title("⚾ KBO 프로야구 Daily")
st.caption(f"오늘({datetime.date.today().strftime('%m월 %d일')})의 따끈따끈한 소식만 모았습니다.")

# ------------------------------------------------------------------
# [2] 기능 함수
# ------------------------------------------------------------------
def get_raw_news():
    """RSS에서 '최근 48시간' 뉴스만 강제로 긁어옵니다."""
    
    # [핵심 수정] 
    # 1. q=KBO+리그 : 검색어 깔끔하게 변경
    # 2. when:2d : 무조건 최근 2일(48시간) 이내 기사만 검색 (옛날 기사 원천 차단)
    # 3. &scoring=n : 최신순(Newest) 정렬 강제
    rss_url = "https://news.google.com/rss/search?q=KBO+리그+when:2d&hl=ko&gl=KR&ceid=KR:ko&scoring=n"
    
    feed = feedparser.parse(rss_url)
    
    news_pool = []
    # 최신순으로 정렬된 것 중 상위 30개 가져옴
    for i, entry in enumerate(feed.entries[:30]): 
        news_pool.append({
            "id": i,
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "source": entry.source.title if 'source' in entry else "뉴스"
        })
    return news_pool

def curate_news_with_ai(news_pool):
    """Gemini가 뉴스 제목을 보고 중복을 제거하고 중요 기사만 뽑습니다."""
    
    candidates = "\n".join([f"{item['id']}: {item['title']}" for item in news_pool])
    
    prompt = f"""
    당신은 까다로운 '프로야구 뉴스 편집장'입니다. 
    아래는 방금 들어온 최신 뉴스 속보들입니다. 가장 중요한 기사 5~7개를 엄선하세요.

    [목록]
    {candidates}

    [선별 원칙]
    1. **중복 삭제:** '컴투스 프로야구' 같은 게임 홍보나, 똑같은 내용의 기사는 하나만 남기고 다 버리세요.
    2. **최신성:** 경기 결과, 선수 영입, 부상 소식 등 '지금 발생한 일' 위주로 뽑으세요.
    3. **다양성:** 특정 팀 이야기만 하지 말고 골고루 섞으세요.

    [출력 형식]
    선택한 기사의 ID 리스트만 JSON으로 주세요.
    예시: [0, 5, 12, 15, 22]
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        # 숫자 리스트 추출
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            selected_ids = json.loads(match.group())
            final_list = [news for news in news_pool if news['id'] in selected_ids]
            return final_list
        else:
            return news_pool[:5]
    except:
        return news_pool[:5]

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------

# 상단: 퀵 링크
st.info("👇 경기 일정 및 하이라이트는 아래 버튼으로 확인하세요!")

st.markdown("""
<style>
    .kbo-btn {
        display: inline-block;
        width: 32%;
        padding: 10px 0;
        text-align: center;
        background-color: #f0f2f6;
        border-radius: 8px;
        text-decoration: none;
        color: #333;
        font-weight: bold;
        font-size: 0.9em;
        border: 1px solid #ddd;
    }
    .kbo-btn:hover { background-color: #e0e2e6; color: #007bff; }
</style>
<div style="display:flex; justify-content:space-between;">
    <a href="https://sports.news.naver.com/kbaseball/schedule/index.nhn" target="_blank" class="kbo-btn">📅 경기 일정/결과</a>
    <a href="https://sports.news.naver.com/kbaseball/record/index.nhn" target="_blank" class="kbo-btn">🏆 실시간 순위</a>
    <a href="https://www.youtube.com/results?search_query=KBO+하이라이트+오늘" target="_blank" class="kbo-btn">📺 하이라이트</a>
</div>
""", unsafe_allow_html=True)

st.divider()

# 메인: AI 뉴스 브리핑
col_head, col_btn = st.columns([4, 1])
with col_head:
    st.subheader("📰 AI 큐레이션 뉴스 (최신순)")
with col_btn:
    if st.button("새로고침 🔄"):
        st.rerun()

with st.spinner("최근 48시간 이내의 뉴스만 샅샅이 뒤지는 중... 🕵️"):
    try:
        raw_news = get_raw_news()
        
        if raw_news:
            curated_news = curate_news_with_ai(raw_news)
            
            if curated_news:
                for item in curated_news:
                    with st.container(border=True):
                        st.markdown(f"##### [{item['title']}]({item['link']})")
                        
                        # 날짜 포맷팅 (시차 고려)
                        try:
                            # 구글 뉴스는 GMT 기준일 수 있어 한국 시간(+9) 보정
                            dt = datetime.datetime.strptime(item['published'], "%a, %d %b %Y %H:%M:%S %Z")
                            # 단순화를 위해 시간만 표시하거나 날짜 표시
                            date_str = dt.strftime("%m월 %d일")
                        except:
                            date_str = "오늘"
                        
                        st.caption(f"🗞️ {item['source']} | 🕒 {date_str}")
            else:
                st.info("최근 48시간 내에 중요한 뉴스가 없거나, AI가 선별하지 못했습니다.")
        else:
            st.warning("최근 2일간 KBO 관련 뉴스가 없습니다. (비시즌이거나 검색 오류)")
            
    except Exception as e:
        st.error(f"시스템 오류: {e}")
