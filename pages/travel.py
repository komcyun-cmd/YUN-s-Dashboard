
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime
import os
import json
import re
import requests
from bs4 import BeautifulSoup

# ------------------------------------------------------------------
# [1] 설정 및 연결
# ------------------------------------------------------------------
st.set_page_config(page_title="우리 가족 여행 본부", page_icon="👨‍👩‍👧‍👦", layout="wide")

# API 키 및 시트 연결
if "gcp_service_account" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
else:
    # 로컬 테스트용
    GEMINI_API_KEY = "여기에_GEMINI_API_KEY_넣으세요_로컬테스트용"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
    except:
        creds = None

# AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# 시트 연결 함수 (탭별로 구분)
def get_sheet(worksheet_name):
    try:
        client = gspread.authorize(creds)
        # 시트가 없으면 에러가 날 수 있으니 주의 (미리 만들어두세요!)
        return client.open("My_Dashboard_DB").worksheet(worksheet_name)
    except Exception as e:
        st.error(f"'{worksheet_name}' 시트 연결 오류: {e}")
        return None

# 웹사이트 텍스트 긁어오기 (크롤링)
def fetch_url_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 텍스트만 깔끔하게 추출 (너무 길면 자름)
        text = soup.get_text(separator=' ', strip=True)
        return text[:10000] # AI에게 보낼 거라 너무 길면 안됨
    except Exception as e:
        return f"내용을 가져올 수 없음: {e}"

# JSON 추출 함수
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

# 탭 3개로 확장!
tab1, tab2, tab3 = st.tabs(["✈️ AI 여행 플래너", "🔗 링크 분석기 (NEW)", "💰 공금 사용 내역"])

# ==================================================================
# [탭 1] AI 여행 플래너 (기존 동일)
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
                    1. 일자별, 시간대별로 현실적인 동선 고려.
                    2. 맛집/명소 구체적 추천.
                    3. Markdown 표 형식 출력.
                    4. '예상 1인당 경비' 원화 추산.
                    """
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"오류: {e}")

# ==================================================================
# [탭 2] 🔗 맛집/숙소 링크 분석기 (★새로 추가된 기능★)
# ==================================================================
with tab2:
    st.markdown("### 🔍 링크만 주면 정보가 쏙!")
    st.caption("블로그나 구글맵 링크를 넣으면 AI가 [상호명 / 평점 / 특징 / 위치]를 정리해줍니다.")

    url_input = st.text_input("🔗 링크 붙여넣기 (네이버 블로그, 타베로그, 구글맵 등)")
    
    if st.button("봇, 분석해줘! 🕵️‍♂️"):
        if url_input:
            with st.spinner("링크에 들어가서 정보를 읽어오는 중..."):
                # 1. 링크 내용 긁어오기
                page_text = fetch_url_content(url_input)
                
                # 2. AI에게 분석 시키기
                prompt = f"""
                아래 웹페이지 텍스트를 읽고 핵심 정보를 JSON으로 정리해줘.
                
                [웹페이지 내용]
                {page_text}
                
                [추출 항목]
                1. name: 상호명 (또는 장소명)
                2. category: 카테고리 (맛집, 숙소, 명소 등)
                3. rating: 평점 (없으면 '정보없음')
                4. summary: 한줄 특징 요약 (어떤 메뉴가 유명한지 등)
                5. location: 위치/주소 (대략적으로)
                
                출력 포맷: {{"name": "...", "category": "...", "rating": "...", "summary": "...", "location": "..."}}
                오직 JSON만 출력해.
                """
                
                try:
                    response = model.generate_content(prompt)
                    data = extract_json(response.text)
                    
                    if data:
                        st.success("분석 완료!")
                        
                        # 예쁜 카드 형태로 보여주기
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.metric("⭐ 평점", data.get('rating', '-'))
                            st.markdown(f"**📍 위치:** {data.get('location', '-')}")
                        with c2:
                            st.subheader(data.get('name', '이름 모름'))
                            st.markdown(f"🏷️ **{data.get('category', '-')}**")
                            st.info(data.get('summary', '-'))
                            
                        # (선택) 시트에 저장 버튼
                        if st.button("💾 이 장소 저장하기"):
                            sheet = get_sheet("여행장소") # ★ 시트 탭 이름 주의!
                            if sheet:
                                sheet.append_row([
                                    datetime.date.today().strftime("%Y-%m-%d"),
                                    data.get('category'),
                                    data.get('name'),
                                    data.get('rating'),
                                    data.get('summary'),
                                    url_input
                                ])
                                st.toast("저장되었습니다!")
                    else:
                        st.error("정보를 찾지 못했습니다. (AI 응답 오류)")
                        
                except Exception as e:
                    st.error(f"분석 중 오류: {e}")
        else:
            st.warning("링크를 입력해주세요.")

    # 저장된 장소 리스트 보여주기
    st.divider()
    st.markdown("### 📂 우리가 찜한 장소들")
    try:
        sheet = get_sheet("여행장소")
        if sheet:
            data = sheet.get_all_records()
            if data:
                st.dataframe(pd.DataFrame(data))
            else:
                st.info("아직 찜한 장소가 없습니다.")
    except:
        st.caption("※ 구글 시트에 '여행장소' 탭을 만들어주세요.")


# ==================================================================
# [탭 3] 공금 사용 내역 (가계부 - 기존 동일)
# ==================================================================
with tab3:
    st.markdown("### 💸 실시간 지출 기록")
    # ... (아까 코드와 동일한 가계부 로직) ...
    # 코드가 길어지니 중략하지 않고 전체 다 넣으려면
    # 아까 family.py의 tab2 내용을 여기에 그대로 붙여넣으시면 됩니다.
    
    # [아래 내용을 tab3에 채워주세요]
    with st.expander("🖊️ 영수증 기록하기", expanded=True):
        with st.form("expense_form", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1: date = st.date_input("날짜", datetime.date.today())
            with col2: item = st.text_input("내용")
            with col3: amount = st.number_input("금액", min_value=0, step=100)
            with col4: payer = st.selectbox("결제자", ["아빠", "엄마", "아들", "딸"])
            note = st.text_input("비고")
            if st.form_submit_button("💾 저장하기"):
                sheet = get_sheet("가족여행") # 여기는 '가족여행' 탭
                if sheet:
                    sheet.append_row([str(date), item, amount, payer, note])
                    st.toast("저장되었습니다!")
                    st.rerun()

    sheet = get_sheet("가족여행")
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            if '금액' in df.columns:
                df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',',''), errors='coerce').fillna(0)
            st.divider()
            c1, c2 = st.columns(2)
            c1.metric("총 지출액", f"{df['금액'].sum():,.0f} 원")
            c2.bar_chart(df.groupby('결제자')['금액'].sum())
            st.dataframe(df.sort_values(by='날짜', ascending=False), use_container_width=True)
