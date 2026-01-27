import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --------------------------------------------------------------------------
# 1. 설정 및 상수 정의
# --------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="오늘의 오피니언", page_icon="📰")

# 네이버 뉴스 '리스트 페이지' 접근을 위한 상수
PRESS_MAP = {
    '조선일보': '023',
    '중앙일보': '025',
    '한국일보': '469'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

# --------------------------------------------------------------------------
# 2. 날짜 및 파싱 헬퍼 함수
# --------------------------------------------------------------------------

def is_today(date_text):
    if not date_text: return False
    date_text = date_text.strip()
    
    if '전' in date_text: # 1시간전, 50분전 등
        return True
        
    today_str = datetime.now().strftime('%Y.%m.%d')
    if today_str in date_text:
        return True
        
    # 날짜 없이 시간만 있는 경우 (오전 10:30 등)도 오늘로 간주
    if ':' in date_text and '.' not in date_text: 
        return True
        
    return False

def fetch_opinion_list(press_name, press_code):
    url = f"https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&oid={press_code}&sid1=110"
    
    debug_info = {
        "url": url,
        "status": None,
        "error": None,
        "html_preview": ""
    }
    
    news_items = []
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        debug_info["status"] = response.status_code
        
        if response.status_code != 200:
            debug_info["error"] = f"Status Code: {response.status_code}"
            return [], debug_info

        soup = BeautifulSoup(response.content, 'html.parser')
        debug_info["html_preview"] = soup.prettify()[:1000]

        groups = soup.select('ul.type06_headline') + soup.select('ul.type06')
        
        for group in groups:
            items = group.select('li')
            for item in items:
                try:
                    dts = item.select('dt')
                    if not dts: continue
                    
                    title_tag = dts[-1].select_one('a')
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    
                    dd = item.select_one('dd')
                    if dd:
                        date_tag = dd.select_one('span.date')
                        if date_tag:
                            date_text = date_tag.get_text(strip=True)
                            
                            if is_today(date_text):
                                news_items.append({
                                    'title': title,
                                    'link': link,
                                    'date': date_text
                                })
                except:
                    continue

    except Exception as e:
        debug_info["error"] = str(e)
        return [], debug_info

    return news_items, debug_info

# --------------------------------------------------------------------------
# 3. UI 구성 (디자인 자동 적응형으로 수정)
# --------------------------------------------------------------------------

# CSS: 폰트 조정 및 링크 색상 자동화
st.markdown("""
<style>
    /* 전체 폰트 크기 조정 */
    .stMarkdown p {
        font-size: 16px;
    }
    /* 링크 호버 효과 및 색상 변수 사용 */
    a.headline-link {
        color: var(--text-color) !important; /* 다크모드에선 흰색, 라이트모드에선 검은색 자동 적용 */
        text-decoration: none;
        font-weight: 700;
        font-size: 18px;
        line-height: 1.5;
        display: block;
        margin-bottom: 6px;
        letter-spacing: -0.5px;
    }
    a.headline-link:hover {
        text-decoration: underline !important;
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

st.title("🗞️ 오늘의 오피니언")
st.caption(f"기준: {datetime.now().strftime('%Y-%m-%d')} | 실시간 업데이트")

with st.sidebar:
    st.header("설정")
    if st.button("새로고침", use_container_width=True):
        st.rerun()
    st.markdown("---")
    show_debug = st.checkbox("디버깅 모드", value=False)

col1, col2, col3 = st.columns(3)
cols = [col1, col2, col3]

with st.spinner('헤드라인을 가져오는 중...'):
    for i, (name, code) in enumerate(PRESS_MAP.items()):
        with cols[i]:
            # 신문사 이름 스타일링
            st.markdown(f"<h3 style='border-bottom: 2px solid var(--text-color); padding-bottom: 10px; margin-bottom: 20px;'>{name}</h3>", unsafe_allow_html=True)
            
            items, debug = fetch_opinion_list(name, code)
            
            if items:
                for item in items:
                    # [수정됨] 하드코딩된 색상을 제거하고 CSS 클래스(headline-link)를 사용
                    st.markdown(f"""
                    <div style="padding: 12px 0; border-bottom: 1px solid #777;">
                        <a href="{item['link']}" target="_blank" class="headline-link">
                            {item['title']}
                        </a>
                        <div style="
                            font-size: 13px; 
                            color: #999; 
                            font-weight: 400;
                        ">
                            🕒 {item['date']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("오늘의 기사가 없습니다.")
                
            if show_debug:
                with st.expander(f"데이터 확인"):
                    st.write(f"URL: {debug['url']}")
                    st.text_area("HTML", debug['html_preview'], height=200, key=f"debug_{name}")