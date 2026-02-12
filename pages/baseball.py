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
st.caption(f"AI 편집국장이 엄선한 오늘({datetime.date.today().strftime('%m월 %d일')})의 핵심 뉴스입니다.")

# ------------------------------------------------------------------
# [2] 기능 함수
# ------------------------------------------------------------------
def get_raw_news():
    """RSS에서 원본 뉴스 30개를 긁어옵니다."""
    # 검색어를 조금 더 구체적으로 변경
    rss_url = "https://news.google.com/rss/search?q=KBO+프로야구+경기+결과+트레이드&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    
    news_pool = []
    for i, entry in enumerate(feed.entries[:30]): # 30개나 가져와서 AI에게 판단시킴
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
    
    # AI에게 보낼 뉴스 리스트 (ID와 제목만)
    candidates = "\n".join([f"{item['id']}: {item['title']}" for item in news_pool])
    
    prompt = f"""
    당신은 까다로운 '프로야구 뉴스 편집장'입니다. 
    아래 뉴스 목록(ID: 제목)을 보고, 가장 중요한 기사 5~7개를 엄선하세요.

    [목록]
    {candidates}

    [선별 원칙]
    1. **중복 제거 필수:** 같은 주제(예: 컴투스 게임 출시, 특정 경기 결과)의 기사가 여러 개면 그 중 가장 제목이 깔끔한 것 **하나만** 선택하세요.
    2. **광고/보도자료 필터링:** '사전 예약', '게임 출시', '이벤트' 같은 홍보성 기사는 가급적 제외하고, 경기 결과, 선수 영입, 부상 등 **'진짜 야구 뉴스'**를 우선하세요.
    3. **다양성:** 특정 팀 이야기만 하지 말고 다양한 이슈를 섞으세요.

    [출력 형식]
    선택한 기사의 ID 리스트만 JSON으로 주세요.
    예시: [0, 5, 12, 15, 22]
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        # 숫자 리스트 추출 (정규식 사용)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            selected_ids = json.loads(match.group())
            # 선택된 ID에 해당하는 뉴스만 필터링
            final_list = [news for news in news_pool if news['id'] in selected_ids]
            return final_list
        else:
            return news_pool[:5] # 실패하면 그냥 앞 5개 리턴
    except:
        return news_pool[:5]

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------

# 상단: 퀵 링크 (HTML 방식 - 오류 없음)
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
    st.subheader("📰 AI 큐레이션 뉴스")
with col_btn:
    if st.button("새로고침 🔄"):
        st.rerun()

# 로딩 중 표시
with st.spinner("AI 편집장이 30개의 기사를 읽고 '진짜 뉴스'만 골라내는 중입니다... 🤖"):
    try:
        # 1. 원본 30개 가져오기
        raw_news = get_raw_news()
        
        if raw_news:
            # 2. AI가 선별하기
            curated_news = curate_news_with_ai(raw_news)
            
            if curated_news:
                for item in curated_news:
                    with st.container(border=True):
                        st.markdown(f"##### [{item['title']}]({item['link']})")
                        
                        # 날짜 포맷팅
                        try:
                            parsed_date = datetime.datetime.strptime(item['published'], "%a, %d %b %Y %H:%M:%S %Z")
                            date_str = parsed_date.strftime("%m월 %d일 %H:%M")
                        except:
                            date_str = "오늘"
                        
                        st.caption(f"🗞️ {item['source']} | 🕒 {date_str}")
            else:
                st.info("AI가 선별할 뉴스가 부족합니다. 잠시 후 다시 시도해주세요.")
        else:
            st.warning("뉴스 피드를 가져오지 못했습니다.")
            
    except Exception as e:
        st.error(f"시스템 오류: {e}")
