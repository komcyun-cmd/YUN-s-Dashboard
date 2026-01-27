import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime
import requests

# ------------------------------------------------------------------
# [1] 기본 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="오늘의 브리핑", page_icon="🌅", layout="centered")

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

# 날씨 함수 (Open-Meteo)
def get_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=36.35&longitude=127.38&current_weather=true&timezone=Asia%2FSeoul"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        temp = data['current_weather']['temperature']
        code = data['current_weather']['weathercode']
        
        w_text = "맑음 ☀️"
        if code in [1, 2, 3]: w_text = "구름 조금 ⛅"
        elif code in [45, 48]: w_text = "안개 🌫️"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: w_text = "비 🌧️"
        elif code in [71, 73, 75, 77, 85, 86]: w_text = "눈 ❄️"
        elif code >= 95: w_text = "뇌우 ⚡"
        
        return f"{w_text} {temp}°C"
    except Exception as e:
        return f"날씨 오류 ({e})"

# 오늘의 역사/명언 캐싱
@st.cache_data(ttl=3600*12) 
def get_daily_content(today_str):
    prompt = f"""
    오늘은 {today_str}이다.
    1. [역사]: 오늘 날짜의 흥미로운 세계사 사건 1개 (연도 포함).
    2. [명언]: 민음사 세계문학 전집 스타일의 문장 1개 (출처 포함).
    JSON 포맷: {{"history": "...", "quote": "...", "author": "..."}}
    """
    try:
        response = model.generate_content(prompt)
        import json, re
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group()) if match else None
    except:
        return None

# ------------------------------------------------------------------
# [2] 화면 구성
# ------------------------------------------------------------------
st.title(f"📅 {datetime.date.today().strftime('%m월 %d일')} 아침")

col1, col2 = st.columns([1, 2])
with col1:
    st.metric("대전 날씨", get_weather())
with col2:
    today_obj = datetime.date.today()
    info = get_daily_content(today_obj.strftime("%Y년 %m월 %d일"))
    if info:
        st.info(f"📜 **오늘의 역사**\n\n{info['history']}")

st.divider()

if info:
    st.markdown(f"""
    <div style="padding:15px; border-left:4px solid #aaa; background-color:#f9f9f9;">
        <em style="color:#555; font-size:1.1em;">"{info['quote']}"</em>
        <p style="text-align:right; color:#888; margin-top:5px;">- {info['author']}</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 탭 구성 ---
tab1, tab2, tab3 = st.tabs(["✅ 할 일 (Smart)", "📝 빠른 메모", "🛠️ 데이터 수정/관리"])

# ==================================================================
# [탭 1] 스마트 할 일 (날짜 선택 추가됨)
# ==================================================================
with tab1:
    # 1. 입력 폼 (날짜, 내용, 반복)
    with st.expander("
