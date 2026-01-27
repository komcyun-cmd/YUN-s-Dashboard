import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime
import os
import json
import re

# ------------------------------------------------------------------
# [1] 설정 및 연결
# ------------------------------------------------------------------
st.set_page_config(page_title="우리 가족 여행 본부", page_icon="👨‍👩‍👧‍👦", layout="wide")

# API 키 및 시트 연결 (Main.py와 동일한 로직)
if "gcp_service_account" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
else:
    # 로컬 테스트용
    GEMINI_API_KEY = "여기에_GEMINI_API_KEY_넣으세요_로컬테스트용"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # 경로 찾기 로직 생략 (기존 파일 참조)
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
    except:
        creds = None

# AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# 시트 연결 함수
def get_sheet():
    try:
        client = gspread.authorize(creds)
        return client.open("My_Dashboard_DB").worksheet("가족여행")
    except Exception as e:
        st.error(f"시트 연결 오류: {e}")
        return None

# JSON 추출 함수 (AI 답변 정리용)
def extract_json(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except: pass
    return None

# ------------------------------------------------------------------
# [2] 화면 구성
# ------------------------------------------------------------------
st.title("👨‍👩‍👧‍👦 우리 가족 여행 & 경비 본부")

tab1, tab2 = st.tabs(["✈️ AI 여행 플래너", "💰 공금 사용 내역"])

# ==================================================================
# [탭 1] AI 여행 코스 짜기
# ==================================================================
with tab1:
    st.markdown("### 🤖 무엇이든 던져보세요 (AI 비서)")
    st.info("💡 팁: 블로그 링크, 가고 싶은 장소, 먹고 싶은 메뉴 등을 막 적어도 됩니다.")
    
    user_input = st.text_area("입력 예시: 1월 25일에 오사카 가는데, 유니버셜 스튜디오랑 도톤보리 맛집 포함해서 2박 3일 코스 짜줘.", height=100)
    
    if st.button("✨ AI야, 일정표 만들어줘"):
        if user_input:
            with st.spinner("가족을 위한 최적의 동선을 계산 중입니다..."):
                try:
                    prompt = f"""
                    다음 요청을 바탕으로 여행 일정표를 짜줘.
                    내용: {user_input}
                    
                    [지시사항]
                    1. 일자별, 시간대별로 현실적인 동선을 고려해.
                    2. 맛집이나 명소는 구체적인 이름이 없으면 추천해줘.
                    3. 결과를 깔끔한 Markdown 표 형식으로 출력해줘.
                    4. 마지막에 '예상 1인당 경비'도 원화로 추산해줘.
                    """
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                    st.success("일정이 마음에 드시면 캡처해서 가족 단톡방에 공유하세요!")
                except Exception as e:
                    st.error(f"AI 호출 오류: {e}")
        else:
            st.warning("내용을 입력해주세요!")

# ==================================================================
# [탭 2] 공금 사용 내역 (가계부)
# ==================================================================
with tab2:
    st.markdown("### 💸 실시간 지출 기록")
    
    # 1. 입력 폼
    with st.expander("🖊️ 영수증 기록하기 (누르세요)", expanded=True):
        with st.form("expense_form", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                date = st.date_input("날짜", datetime.date.today())
            with col2:
                item = st.text_input("내용 (예: 편의점, 택시)")
            with col3:
                amount = st.number_input("금액 (원/엔)", min_value=0, step=100)
            with col4:
                payer = st.selectbox("결제자", ["아빠", "엄마", "아들", "딸"])
            
            note = st.text_input("비고 (환율 등)")
            
            submitted = st.form_submit_button("💾 저장하기")
            
            if submitted:
                sheet = get_sheet()
                if sheet:
                    sheet.append_row([str(date), item, amount, payer, note])
                    st.toast("저장되었습니다! 💸")
                    # 새로고침을 위해 rerun 대신 session state 활용 가능하나 일단 심플하게
                    st.rerun() 

    # 2. 통계 보여주기
    sheet = get_sheet()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # 금액 숫자 변환
            if '금액' in df.columns:
                df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',',''), errors='coerce').fillna(0)

            st.divider()
            
            # 요약 지표
            total_spent = df['금액'].sum()
            c1, c2 = st.columns(2)
            c1.metric("총 지출액", f"{total_spent:,.0f} 원")
            
            # 많이 쓴 사람 (결제자별)
            payer_group = df.groupby('결제자')['금액'].sum()
            c2.bar_chart(payer_group)
            
            # 상세 내역 (최신순)
            st.subheader("📋 상세 내역")
            st.dataframe(df.sort_values(by='날짜', ascending=False), use_container_width=True)
            
        else:
            st.info("아직 지출 내역이 없습니다. 위에서 입력해보세요!")
