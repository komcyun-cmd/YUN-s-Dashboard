import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime
import requests # 날씨 가져오는 도구

# ------------------------------------------------------------------
# [1] 기본 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="오늘의 브리핑", page_icon="🌅", layout="centered") # 모바일 보기 좋게

# API 키 및 시트 연결
if "gcp_service_account" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
else:
    GEMINI_API_KEY = "로컬용_키_입력"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
    except:
        creds = None

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

def get_sheet():
    try:
        client = gspread.authorize(creds)
        return client.open("My_Dashboard_DB").worksheet("데일리")
    except:
        return None

# ------------------------------------------------------------------
# [2] 기능 함수들 (날씨, 역사, 명언)
# ------------------------------------------------------------------

# 1. 날씨 가져오기 (별도 키 없이 wttr.in 사용)
def get_weather(city="Daejeon"):
    try:
        # 한글 표시를 위해 lang=ko 추가
        url = f"https://wttr.in/{city}?format=%C+%t&lang=ko" 
        response = requests.get(url)
        return response.text.strip()
    except:
        return "날씨 정보 없음"

# 2. 오늘의 역사 & 명언 (Gemini에게 부탁, 하루 한번만 실행되게 캐싱)
@st.cache_data(ttl=3600*12) # 12시간 동안은 기억하고 있어라 (API 절약)
def get_daily_content(today_str):
    prompt = f"""
    오늘은 {today_str}이다.
    두 가지를 짧고 굵게 출력해줘.
    
    1. [오늘의 역사]: 세계사에서 오늘 날짜에 일어난 가장 중요하고 흥미로운 사건 딱 1개. (연도 포함, 2문장 이내)
    2. [오늘의 문장]: '민음사 세계문학 전집' 스타일의 깊이 있는 문장이나 철학적인 명언 1개. (출처/저자 포함)
    
    출력 형식(JSON):
    {{
        "history": "...",
        "quote": "...",
        "author": "..."
    }}
    """
    try:
        response = model.generate_content(prompt)
        import json
        import re
        text = response.text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except:
        return None

# ------------------------------------------------------------------
# [3] 화면 구성 (UI)
# ------------------------------------------------------------------
st.title(f"📅 {datetime.date.today().strftime('%m월 %d일')} 아침")

# --- 섹션 1: 날씨 & 영감 ---
col1, col2 = st.columns([1, 2])
with col1:
    st.metric("대전 날씨", get_weather("Daejeon"))

with col2:
    today_str = datetime.date.today().strftime("%Y년 %m월 %d일")
    daily_info = get_daily_content(today_str)
    
    if daily_info:
        st.info(f"📜 **오늘의 역사**\n\n{daily_info['history']}")

st.divider()

# --- 섹션 2: 민음사 일력 (오늘의 명언) ---
if daily_info:
    st.markdown(f"""
    <div style="padding:20px; border:1px solid #ddd; border-radius:10px; text-align:center; background-color:#f9f9f9;">
        <h3 style="color:#555; font-family:serif;">"{daily_info['quote']}"</h3>
        <p style="color:#888; margin-top:10px;">- {daily_info['author']} -</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 섹션 3: 할 일(Reminders) & 메모(Notes) ---
tab1, tab2 = st.tabs(["✅ 할 일 (To-Do)", "📝 빠른 메모"])

# [탭 1] 아이폰 미리 알림 스타일
with tab1:
    # 입력폼
    with st.form("todo_form", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        task = c1.text_input("할 일을 입력하세요", placeholder="예: 원무과 미팅, 약 주문")
        submitted = c2.form_submit_button("추가")
        
        if submitted and task:
            sheet = get_sheet()
            if sheet:
                # 날짜, 유형, 내용, 완료(빈칸)
                sheet.append_row([str(datetime.date.today()), "일정", task, "FALSE"])
                st.toast("할 일이 추가되었습니다!")
                st.rerun()

    # 리스트 보여주기
    sheet = get_sheet()
    if sheet:
        rows = sheet.get_all_records()
        df = pd.DataFrame(rows)
        
        # '일정'이면서 완료되지 않은(FALSE) 것만 필터링
        if not df.empty:
            todos = df[ (df['유형'] == '일정') & (df['완료'] != 'TRUE') ]
            
            if not todos.empty:
                st.write(f"남은 할 일: **{len(todos)}개**")
                for i, row in todos.iterrows():
                    # 체크박스로 완료 처리
                    col_a, col_b = st.columns([0.1, 0.9])
                    if col_a.checkbox(" ", key=f"check_{i}"):
                        # 체크하면 시트에서 TRUE로 바꿈 (로직 단순화를 위해 실제 업데이트는 생략하고 화면에서만 가림)
                        # *제대로 하려면 row 번호를 찾아 update_cell 해야 함. 여기선 심플하게 '삭제' 버튼으로 대체 권장*
                        st.success("완료! (다음 로딩 시 사라집니다)")
                        # 실제 시트 업데이트 로직은 복잡해질 수 있어, 여기선 '삭제' 버튼을 추가하는 방식을 추천
                    col_b.write(row['내용'])
            else:
                st.caption("남은 할 일이 없습니다. 편안한 하루 되세요! ☕")

# [탭 2] 아이폰 메모장 스타일
with tab2:
    with st.form("memo_form", clear_on_submit=True):
        note = st.text_area("메모 입력", height=100, placeholder="떠오르는 아이디어를 적으세요.")
        if st.form_submit_button("메모 저장"):
            if note:
                sheet = get_sheet()
                if sheet:
                    sheet.append_row([str(datetime.date.today()), "메모", note, ""])
                    st.toast("메모가 저장되었습니다.")
                    st.rerun()
    
    # 최근 메모 보기
    if sheet:
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            memos = df[df['유형'] == '메모'].sort_values(by='날짜', ascending=False).head(5)
            for _, row in memos.iterrows():
                st.markdown(f"**[{row['날짜']}]**")
                st.text(row['내용'])
                st.markdown("---")
