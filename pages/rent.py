import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
from PIL import Image
import datetime
import json
import re

# ------------------------------------------------------------------
# [1] 설정 및 연결 (클라우드 호환성 수정 완료)
# ------------------------------------------------------------------
st.set_page_config(page_title="병원 관리비 매니저", page_icon="🏢", layout="centered")

# API 키 및 구글 시트 연결
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # 1. Streamlit Cloud 환경 (Secrets 우선 확인)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            
    # 2. 로컬 개발 환경 (secrets.json 파일이 있을 때 - 백업용)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        # 로컬용 API 키는 별도 설정 필요
        
except Exception as e:
    st.error(f"⚠️ 인증 설정 오류: {e}")
    st.stop() # 인증 실패시 여기서 멈춤

model = genai.GenerativeModel('gemini-flash-latest')

def get_sheet():
    try:
        client = gspread.authorize(creds)
        # 시트 이름과 탭 이름이 정확한지 확인하세요!
        return client.open("My_Dashboard_DB").worksheet("관리비") 
    except Exception as e:
        return None

# ------------------------------------------------------------------
# [2] 화면 구성
# ------------------------------------------------------------------
st.title("🏢 병원 관리비 매니저 (AI Vision)")

tab1, tab2 = st.tabs(["📸 고지서 자동 분석", "📊 통계 대시보드"])

# [탭 1] AI 고지서 분석기
with tab1:
    st.info("관리비 고지서 사진을 찍거나 올려주세요. AI가 내용을 읽어냅니다.")
    
    # 1. 사진 업로드
    img_file = st.file_uploader("고지서 사진 업로드", type=["png", "jpg", "jpeg"])
    
    # 분석 결과를 저장할 세션 상태 초기화
    if "analyzed_data" not in st.session_state:
        st.session_state.analyzed_data = None

    if img_file:
        image = Image.open(img_file)
        st.image(image, caption="업로드된 고지서", use_container_width=True)
        
        # 2. 분석 버튼
        if st.button("🔍 AI 분석 시작 (내용 추출)"):
            with st.spinner("AI가 고지서를 읽고 있습니다..."):
                try:
                    prompt = """
                    이 고지서 이미지에서 다음 정보를 추출해서 JSON 형식으로 출력해줘.
                    1. date: 납부일 또는 작성일 (YYYY-MM-DD 형식). 날짜가 없으면 오늘 날짜.
                    2. category: 항목 (월세, 전기세, 수도세, 관리비, 기타 중 하나 선택)
                    3. amount: 청구 금액 (숫자만, 콤마 제외)
                    4. memo: 어떤 고지서인지 한 줄 요약 (예: 1월분 전기요금)
                    
                    출력 예시:
                    {"date": "2024-02-25", "category": "전기세", "amount": 150000, "memo": "2월분 전기료"}
                    """
                    response = model.generate_content([prompt, image])
                    
                    # JSON 추출 (가끔 마크다운 ```json ... ``` 으로 감싸서 줄 때가 있어서 파싱)
                    text = response.text
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    
                    if json_match:
                        st.session_state.analyzed_data = json.loads(json_match.group())
                        st.toast("분석 성공! 아래 내용을 확인하고 저장하세요.")
                    else:
                        st.error("AI가 정보를 찾지 못했습니다. 직접 입력해주세요.")
                except Exception as e:
                    st.error(f"분석 오류: {e}")

    st.divider()

    # 3. 결과 확인 및 저장 (분석된 데이터가 있으면 자동 입력됨)
    with st.form("rent_form", clear_on_submit=True):
        st.subheader("📝 입력 내용 확인")
        
        # 기본값 설정 (분석된 게 있으면 그걸 쓰고, 없으면 빈칸)
        default_date = datetime.date.today()
        default_cat = "관리비"
        default_amt = 0
        default_memo = ""
        
        if st.session_state.analyzed_data:
            d = st.session_state.analyzed_data
            try:
                default_date = datetime.datetime.strptime(d.get("date"), "%Y-%m-%d").date()
            except: pass
            default_cat = d.get("category", "관리비")
            default_amt = int(d.get("amount", 0))
            default_memo = d.get("memo", "")

        # 입력 필드 (수정 가능)
        col1, col2 = st.columns(2)
        date = col1.date_input("납부일", default_date)
        category = col2.selectbox("항목", ["월세", "전기세", "수도세", "관리비", "기타"], index=["월세", "전기세", "수도세", "관리비", "기타"].index(default_cat) if default_cat in ["월세", "전기세", "수도세", "관리비", "기타"] else 3)
        
        amount = st.number_input("금액 (원)", value=default_amt, step=1000)
        memo = st.text_input("메모", value=default_memo)
        
        # 저장 버튼
        if st.form_submit_button("💾 구글 시트에 저장"):
            sheet = get_sheet()
            if sheet:
                try:
                    sheet.append_row([str(date), category, amount, memo])
                    st.success(f"저장되었습니다! ({category} {amount:,}원)")
                    # 저장 후 세션 초기화
                    st.session_state.analyzed_data = None
                except Exception as e:
                    st.error(f"저장 실패: {e}")
            else:
                st.error("구글 시트 연결 실패. 'My_Dashboard_DB' 시트에 '관리비' 탭이 있는지 확인해주세요.")

# [탭 2] 통계 대시보드
with tab2:
    st.subheader("📊 관리비 추세")
    if st.button("🔄 새로고침"):
        st.rerun()
        
    sheet = get_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                if '금액' in df.columns:
                    # 금액 콤마 제거 및 숫자 변환
                    df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                
                # 차트와 표
                st.bar_chart(df, x="날짜", y="금액", color="항목")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("데이터가 없습니다. 고지서를 찍어 올려주세요!")
        except Exception as e:
            st.warning("데이터를 불러오는 중입니다 (또는 데이터가 없음).")
