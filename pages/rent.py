import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime

# ------------------------------------------------------------------
# [1] 설정 및 연결
# ------------------------------------------------------------------
st.set_page_config(page_title="병원 관리비 매니저", page_icon="🏢", layout="centered")

# [수정된 부분] API 키 및 구글 시트 연결 (클라우드/로컬 자동 감지)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    if "gcp_service_account" in st.secrets:
        # 1. Streamlit Cloud 환경
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        # Gemini 키도 Secrets에서 가져옴
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        # 2. 로컬 개발 환경 (secrets.json 파일이 있을 때)
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        # 로컬 테스트용 키 (필요시 직접 입력)
        # genai.configure(api_key="YOUR_LOCAL_API_KEY")

except Exception as e:
    st.error(f"⚠️ 인증 오류: {e}")
    st.stop()

model = genai.GenerativeModel('gemini-flash-latest')

def get_sheet():
    try:
        client = gspread.authorize(creds)
        # 시트 이름이 맞는지 꼭 확인하세요! (기본값: My_Dashboard_DB)
        return client.open("My_Dashboard_DB").worksheet("관리비") 
    except Exception as e:
        return None

# ------------------------------------------------------------------
# [2] 화면 구성
# ------------------------------------------------------------------
st.title("🏢 병원 관리비 매니저")

tab1, tab2 = st.tabs(["📸 고지서 스캔 (입력)", "📊 통계 대시보드"])

# [탭 1] 고지서 입력
with tab1:
    st.info("관리비 고지서 내용을 입력하거나 사진 내용을 요약해 넣으세요.")
    
    with st.form("rent_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        date = col1.date_input("납부일", datetime.date.today())
        category = col2.selectbox("항목", ["월세", "전기세", "수도세", "관리비(일반)", "기타"])
        
        amount = st.number_input("금액 (원)", step=1000)
        memo = st.text_input("메모 (예: 1월분, 연체료 포함 등)")
        
        if st.form_submit_button("💾 저장하기"):
            sheet = get_sheet()
            if sheet:
                try:
                    sheet.append_row([str(date), category, amount, memo])
                    st.success("저장되었습니다! 🎉")
                except Exception as e:
                    st.error(f"저장 실패: {e}")
            else:
                st.error("구글 시트 '관리비' 탭을 찾을 수 없습니다. (시트에 탭을 만드셨나요?)")

# [탭 2] 통계
with tab2:
    st.subheader("📊 관리비 추세")
    
    if st.button("🔄 데이터 새로고침"):
        st.rerun()
        
    sheet = get_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            if not df.empty:
                # 금액 컬럼 숫자 변환 (콤마 제거)
                if '금액' in df.columns:
                    df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                
                # 차트 그리기
                st.bar_chart(df, x="날짜", y="금액", color="항목")
                
                # 표 보여주기
                st.dataframe(df, use_container_width=True)
            else:
                st.info("아직 데이터가 없습니다. 옆 탭에서 입력해주세요.")
        except Exception as e:
            st.error(f"데이터 불러오기 오류: {e}")
    else:
        st.warning("구글 시트 연결에 실패했습니다. (My_Dashboard_DB 시트에 '관리비' 탭이 있는지 확인하세요)")
