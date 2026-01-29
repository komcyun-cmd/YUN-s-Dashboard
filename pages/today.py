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

# [핵심] 한국 시간 구하는 함수
def get_korea_today():
    korea_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    return korea_now.date()

# 날씨 함수
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
today_obj = get_korea_today()

st.title(f"📅 {today_obj.strftime('%m월 %d일')} 아침")

col1, col2 = st.columns([1, 2])
with col1:
    st.metric("대전 날씨", get_weather())
with col2:
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
# [탭 1] 스마트 할 일
# ==================================================================
with tab1:
    with st.expander("➕ 새 일정 추가하기", expanded=False):
        with st.form("todo_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            target_date = c1.date_input("날짜", today_obj)
            task = c2.text_input("내용", placeholder="예: 치과 예약")
            repeat = c3.selectbox("반복", ["없음", "매일", "매주", "매월"])
            
            if st.form_submit_button("추가"):
                sheet = get_sheet()
                if sheet:
                    sheet.append_row([str(target_date), "일정", task, "FALSE", repeat])
                    st.toast("일정이 추가되었습니다!")
                    st.rerun()

    sheet = get_sheet()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            df['날짜_dt'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
            
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
                    # 데이터프레임 인덱스(idx)는 0부터 시작, 구글 시트는 헤더(1행) 제외 데이터가 2행부터 시작
                    # get_all_records()로 가져왔으므로 idx + 2 가 실제 시트 행 번호
                    is_checked = st.checkbox(f"{row['내용']} ({row['반복']})", key=f"chk_{idx}")
                    if is_checked:
                        try:
                            sheet.update_cell(idx + 2, 4, "TRUE") 
                            st.toast("완료 처리되었습니다! 🎉")
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류 발생: {e}")
            else:
                st.caption("오늘 예정된 할 일이 없습니다. ☕")

# ==================================================================
# [탭 2] 빠른 메모 (수정 기능 추가됨)
# ==================================================================
with tab2:
    # 1. 메모 입력
    st.subheader("🖊️ 메모 기록")
    with st.form("memo_form", clear_on_submit=True):
        note = st.text_area("내용", height=80, placeholder="아이디어를 적어두세요.")
        if st.form_submit_button("저장"):
            if note:
                sheet = get_sheet()
                sheet.append_row([str(today_obj), "메모", note, "", "없음"])
                st.toast("메모 저장됨")
                st.rerun()
    
    st.divider()

    # 2. 최근 메모 리스트 & 수정 기능
    st.subheader("📜 최근 메모")
    
    if not df.empty:
        # '메모' 유형만 필터링하고 최신순 정렬
        # 원본 행 번호(row_idx)를 보존하기 위해 인덱스를 컬럼으로 만듦
        df_memo = df[df['유형'] == '메모'].copy()
        df_memo['original_row'] = df_memo.index + 2 # 시트 행 번호 계산 (헤더=1행 이므로 +2)
        df_memo = df_memo.sort_values(by='날짜', ascending=False).head(5) # 최근 5개만

        if not df_memo.empty:
            # 2-1. 보기 모드
            for _, row in df_memo.iterrows():
                st.text(f"[{row['날짜']}] {row['내용']}")

            # 2-2. 수정 모드 (Expander)
            with st.expander("📝 지난 메모 수정하기 (오타 수정)", expanded=False):
                # 선택 박스를 위한 라벨 만들기
                memo_options = {f"[{r['날짜']}] {r['내용'][:15]}...": r['original_row'] for _, r in df_memo.iterrows()}
                
                selected_label = st.selectbox("수정할 메모 선택", list(memo_options.keys()))
                
                if selected_label:
                    target_row_idx = memo_options[selected_label]
                    # 현재 선택된 메모의 전체 내용 찾기
                    current_content = df.loc[target_row_idx - 2, '내용'] # df 인덱스는 row_idx - 2
                    
                    new_content = st.text_area("수정할 내용", value=current_content, height=100)
                    
                    if st.button("수정 완료 💾"):
                        sheet = get_sheet()
                        # 3번째 컬럼이 '내용' 컬럼임
                        sheet.update_cell(target_row_idx, 3, new_content)
                        st.toast("수정되었습니다! ✨")
                        st.rerun()
        else:
            st.caption("저장된 메모가 없습니다.")

# ==================================================================
# [탭 3] 데이터 관리
# ==================================================================
with tab3:
    st.markdown("### 📋 전체 데이터 편집기")
    if sheet:
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("💾 변경사항 전체 저장", type="primary"):
            with st.spinner("저장 중..."):
                sheet.clear()
                sheet.append_row(edited_df.columns.tolist())
                sheet.append_rows(edited_df.values.tolist())
                st.success("저장 완료! ✅")
                st.rerun()