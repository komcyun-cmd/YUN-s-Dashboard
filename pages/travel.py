import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime
import requests
from bs4 import BeautifulSoup
import json
import re

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
    GEMINI_API_KEY = "여기에_키를_적지_마세요" # 로컬용
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
    except:
        creds = None

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

def get_sheet(worksheet_name):
    try:
        client = gspread.authorize(creds)
        return client.open("My_Dashboard_DB").worksheet(worksheet_name)
    except:
        return None

# [핵심] 네이버 블로그까지 뚫어버리는 텍스트 수집기
def fetch_url_content(url):
    try:
        # 1. 네이버 블로그라면? -> '진짜 주소(PostView)'로 변환
        if "blog.naver.com" in url:
            # 주소에서 아이디와 글번호 추출 (예: blog.naver.com/id/1234 -> id, 1234)
            match = re.search(r'blog.naver.com/([^/]+)/([0-9]+)', url)
            if match:
                blog_id, log_no = match.groups()
                # iframe을 벗겨낸 진짜 주소
                url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"

        # 2. 구글 지도 링크 거절 (보안 문제)
        if "google.com" in url and "maps" in url:
             return "구글 지도 링크는 읽을 수 없습니다. 블로그나 식당 소개 페이지 링크를 주세요."

        # 3. 접속 시도
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        
        # 4. 텍스트 추출
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 스크립트 등 불필요한 태그 제거
        for script in soup(["script", "style", "header", "footer", "nav", "iframe"]):
            script.extract()
            
        # 본문 텍스트만 깔끔하게
        text = soup.get_text(separator=' ', strip=True)
        
        # 내용이 너무 없으면 실패로 간주
        if len(text) < 50:
            return "오류: 내용을 읽을 수 없습니다. (텍스트가 너무 짧음)"
            
        return text[:15000] # AI에게 너무 긴 글은 잘라서 줌

    except Exception as e:
        return f"읽기 실패: {e}"

# ------------------------------------------------------------------
# [2] 화면 구성
# ------------------------------------------------------------------
st.title("👨‍👩‍👧‍👦 우리 가족 여행 & 경비 본부")

tab1, tab2, tab3 = st.tabs(["✈️ AI 여행 플래너", "🍽️ 주변 맛집 추천/비교", "💰 공금 사용 내역"])

# [탭 1] 여행 플래너
with tab1:
    st.markdown("### 🤖 여행 코스 짜기")
    user_input = st.text_area("예: 오사카 2박 3일, 유니버셜 포함 코스 짜줘", height=80)
    if st.button("일정표 생성"):
        with st.spinner("생성 중..."):
            try:
                st.markdown(model.generate_content(f"여행 일정 짜줘: {user_input}").text)
            except: st.error("AI 오류")

# ==================================================================
# [탭 2] 🍽️ 주변 맛집 추천 & 함정 피하기 (업그레이드 완료)
# ==================================================================
with tab2:
    st.markdown("### 🔍 이 식당 어때? (주변 대안 추천)")
    st.caption("블로그 링크를 주시면, 그 식당의 **위치**를 파악해서 **더 나은 곳**과 **피해야 할 곳**을 알려드립니다.")

    url_input = st.text_input("🔗 블로그/리뷰 링크 입력")
    
    if st.button("주변 맛집지도 분석 시작 🧭"):
        if url_input:
            with st.spinner("위치 파악 및 현지 데이터 대조 중..."):
                # 1. 텍스트 추출 (네이버 블로그 뚫기 적용됨)
                page_text = fetch_url_content(url_input)
                
                # 2. AI에게 '현지 가이드' 역할 부여
                prompt = f"""
                너는 현지 사정에 정통한 로컬 가이드다.
                사용자가 아래 블로그 링크(텍스트)에 나온 식당에 관심을 갖고 있다.
                
                [블로그 텍스트]
                {page_text}
                
                [지시사항]
                1. 먼저 이 식당의 **이름**과 **정확한 위치(지역/동네)**, **메뉴**를 파악해라.
                2. 그 **위치 주변**에 있는 식당들을 기준으로 아래 3가지 리스트를 추천해라.
                
                **A. [비슷한 스타일]** (Similar): 링크의 식당과 가격/분위기가 비슷한 대안 2곳.
                **B. [업그레이드 추천]** (Better/Local): 관광객보다 현지인이 많이 가거나, 평점이 더 높은 '진짜 맛집' 2곳.
                **C. [절대 비추천/주의]** (Avoid): 그 동네에서 '관광객 바가지'로 유명하거나 맛이 변해서 평이 안 좋은 곳 1~2곳 (이유 포함).
                
                [출력 형식 - Markdown]
                ## 📍 기준 장소: [식당이름] ([지역명])
                
                ### 1. 비슷한 느낌의 대안 (웨이팅 길면 여기로)
                * **[식당명]**: [특징 한줄 요약]
                * **[식당명]**: [특징 한줄 요약]
                
                ### 2. 🌟 현지인 추천 (여기가 더 맛있어요)
                * **[식당명]**: [추천 이유]
                * **[식당명]**: [추천 이유]
                
                ### 3. 🚨 여긴 가지 마세요 (비추천)
                * **[식당명]**: [비추천 이유 - 예: 너무 비쌈, 불친절, 냉동 사용 등]
                
                마지막에 종합 의견 한 줄.
                """
                
                try:
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                    
                    # 저장 버튼
                    st.divider()
                    if st.button("💾 이 분석 결과 저장"):
                        sheet = get_sheet("여행장소")
                        if sheet:
                            # 텍스트에서 식당 이름만 대략 추출 (첫줄)
                            name_match = response.text.split('\n')[0].replace('#', '').strip()
                            sheet.append_row([
                                datetime.date.today().strftime("%Y-%m-%d"),
                                "맛집분석",
                                name_match,
                                "AI추천완료",
                                "링크 참조",
                                url_input
                            ])
                            st.toast("저장되었습니다!")
                except Exception as e:
                    st.error(f"분석 실패: {e}")
        else:
            st.warning("링크를 넣어주세요!")

# [탭 3] 가계부
with tab3:
    st.markdown("### 💸 지출 기록")
    with st.expander("입력창 열기", expanded=True):
        with st.form("expense"):
            c1, c2 = st.columns(2)
            item = c1.text_input("내용")
            amount = c2.number_input("금액", step=100)
            if st.form_submit_button("저장"):
                sheet = get_sheet("가족여행")
                if sheet:
                    sheet.append_row([str(datetime.date.today()), item, amount, "가족", ""])
                    st.toast("저장됨")
    
    # 내역 표시
    sheet = get_sheet("가족여행")
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and '금액' in df.columns:
            # 금액 콤마 제거 안전장치
            df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',',''), errors='coerce').fillna(0)
            st.dataframe(df)
