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

# [수정됨] 날씨 함수 (Open-Meteo 정식 API 사용 -> 훨씬 안정적)
def get_weather():
    try:
        # 대전 시청 근처 좌표 (위도 36.35, 경도 127.38)
        url = "https://api.open-meteo.com/v1/forecast?latitude=36.35&longitude=127.38&current_weather=true&timezone=Asia%2FSeoul"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        temp = data['current_weather']['temperature']
        code = data['current_weather']['weathercode']
        
        # WMO 날씨 코드 변환 (숫자 -> 한글)
        w_text = "맑음 ☀️"
        if code in [1, 2, 3]: w_text = "구름 조금 ⛅"
        elif code in [45, 48]: w_text = "안개 🌫️"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: w_text = "비 🌧️"
        elif code in [71, 73, 75, 77, 85, 86]: w_text = "눈 ❄️"
        elif code >= 95: w_text = "뇌우 ⚡"
        
        return f"{w_text} {temp}°C"
    except Exception as e:
        return f"날씨 오류 ({e})"

# 오늘의 역사/명언 캐싱 (12시간 유지)
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

# 섹션 1: 날씨 & 영감
col1, col2 = st.columns([1, 2])
with col1:
    st.metric("대전 날씨", get_weather()) # 함수 호출 시 인자 필요 없음 (좌표 고정됨)
with col2:
    today_obj = datetime.date.today()
    info = get_daily_content(today_obj.strftime("%Y년 %m월 %d일"))
    if info:
        st.info(f"📜 **오늘의 역사**\n\n{info['history']}")

st.divider()

# 섹션 2: 오늘의 명언
if info:
    st.markdown(f"""
    <div style="padding:15px; border-left:4px solid #aaa; background-color:#f9f9f9;">
        <em style="color:#555; font-size:1.1em;">"{info['quote']}"</em>
        <p style="text-align:right; color:#888; margin-top:5px;">- {info['author']}</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 탭 구성: 보기 / 관리(수정) ---
tab1, tab2, tab3 = st.tabs(["✅ 할 일 (Smart)", "📝 빠른 메모", "🛠️ 데이터 수정/관리"])

# ==================================================================
# [탭 1] 스마트 할 일 (반복 일정 포함)
# ==================================================================
with tab1:
    # 1. 입력 폼 (반복 선택 추가)
    with st.expander("➕ 새 일정 추가하기", expanded=False):
        with st.form("todo_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            task = c1.text_input("내용", placeholder="예: 매주 수요일 컨퍼런스")
            repeat = c2.selectbox("반복", ["없음", "매일", "매주", "매월"])
            
            if st.form_submit_button("추가"):
                sheet = get_sheet()
                if sheet:
                    # 날짜, 유형, 내용, 완료, 반복
                    sheet.append_row([str(today_obj), "일정", task, "FALSE", repeat])
                    st.toast("일정이 추가되었습니다!")
                    st.rerun()

    # 2. 스마트 리스트 보여주기
    sheet = get_sheet()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # 날짜 형식 변환
            df['날짜_dt'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
            
            # 조건 필터링
            cond_today = (df['날짜_dt'] == today_obj)
            cond_daily = (df['반복'] == '매일')
            cond_weekly = (df['반복'] == '매주') & (pd.to_datetime(df['날짜'], errors='coerce').dt.weekday == today_obj.weekday())
            cond_monthly = (df['반복'] == '매월') & (pd.to_datetime(df['날짜'], errors='coerce').dt.day == today_obj.day)
            
            today_tasks = df[ 
                (df['유형'] == '일정') & 
                (df['완료'] != 'TRUE') & 
                (cond_today | cond_daily | cond_weekly | cond_monthly) 
            ]
            
            if not today_tasks.empty:
                st.write(f"오늘 할 일: **{len(today_tasks)}개**")
                for idx, row in today_tasks.iterrows():
                    chk = st.checkbox(f"{row['내용']} ({row['반복']})", key=f"task_{idx}")
                    if chk:
                        st.caption("✅ 완료! (삭제하려면 '데이터 수정' 탭 이용)")
            else:
                st.caption("오늘 예정된 할 일이 없습니다. ☕")

# ==================================================================
# [탭 2] 빠른 메모 (단순 입력)
# ==================================================================
with tab2:
    with st.form("memo_form", clear_on_submit=True):
        note = st.text_area("메모 입력", height=80, placeholder="아이디어를 적어두세요.")
        if st.form_submit_button("저장"):
            if note:
                sheet = get_sheet()
                sheet.append_row([str(today_obj), "메모", note, "", "없음"])
                st.toast("저장됨")
                st.rerun()
    
    if not df.empty:
        memos = df[df['유형'] == '메모'].sort_values(by='날짜', ascending=False).head(3)
        for _, row in memos.iterrows():
            st.text(f"[{row['날짜']}] {row['내용']}")

# ==================================================================
# [탭 3] 🛠️ 데이터 수정/관리
# ==================================================================
with tab3:
    st.markdown("### 📋 전체 데이터 편집기")
    st.caption("수정 후 아래 '저장' 버튼을 꼭 눌러주세요.")
    
    if sheet:
        raw_data = sheet.get_all_records()
        edit_df = pd.DataFrame(raw_data)
        
        edited_df = st.data_editor(
            edit_df,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor"
        )
        
        if st.button("💾 변경사항 클라우드에 저장 (주의!)", type="primary"):
            with st.spinner("동기화 중..."):
                try:
                    sheet.clear()
                    sheet.append_row(edited_df.columns.tolist())
                    sheet.append_rows(edited_df.values.tolist())
                    st.success("완벽하게 저장되었습니다! ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 중 오류: {e}")
