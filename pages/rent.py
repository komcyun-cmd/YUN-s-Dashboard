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
# [1] 설정 및 연결 (잘 되던 today.py 방식 그대로 적용)
# ------------------------------------------------------------------
st.set_page_config(page_title="병원 관리비 매니저", page_icon="🏢", layout="centered")

# API 키 및 구글 시트 연결
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# [핵심] today.py와 동일한 연결 로직 (안전장치 포함)
try:
    if "gcp_service_account" in st.secrets:
        # 1. Streamlit Cloud 환경
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    else:
        # 2. 로컬 환경 (파일이 없으면 넘어가도록 try-except 처리)
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        except:
            creds = None

    # Gemini API 키 연결
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

except Exception as e:
    st.error(f"연결 설정 중 오류가 발생했습니다: {e}")
    creds = None

model = genai.GenerativeModel('gemini-flash-latest')

def get_sheet():
    if not creds:
        return None
    try:
        client = gspread.authorize(creds)
        # 'My_Dashboard_DB' 시트의 '관리비' 탭을 엽니다.
        return client.open("My_Dashboard_DB").worksheet("관리비") 
    except Exception as e:
        # 연결은 됐는데 시트나 탭 이름이 틀린 경우
        st.error(f"구글 시트를 찾을 수 없습니다: {e}")
        return None

# ------------------------------------------------------------------
# [2] 화면 구성
# ------------------------------------------------------------------
st.title("🏢 병원 관리비 매니저")

tab1, tab2 = st.tabs(["📸 고지서 스캔", "📊 통계 대시보드"])

# [탭 1] 고지서 입력 및 AI 분석
with tab1:
    st.info("고지서 사진을 올리면 AI가 자동으로 읽어줍니다.")
    
    img_file = st.file_uploader("고지서 사진 업로드", type=["png", "jpg", "jpeg"])
    
    if "rent_data" not in st.session_state:
        st.session_state.rent_data = None

    # 1. 사진 분석
    if img_file:
        image = Image.open(img_file)
        st.image(image, caption="고지서 미리보기", use_container_width=True)
        
        if st.button("🔍 내용 추출하기"):
            with st.spinner("AI가 분석 중입니다..."):
                try:
                    prompt = """
                    이 이미지에서 다음 정보를 JSON으로 추출해.
                    {"date": "YYYY-MM-DD", "category": "항목(월세/전기세/수도세/관리비/기타)", "amount": 숫자만, "memo": "한줄요약"}
                    날짜가 없으면 오늘 날짜로 해.
                    """
                    response = model.generate_content([prompt, image])
                    match = re.search(r'\{.*\}', response.text, re.DOTALL)
                    if match:
                        st.session_state.rent_data = json.loads(match.group())
                        st.toast("분석 성공!")
                    else:
                        st.warning("내용을 찾지 못했습니다. 직접 입력해주세요.")
                except Exception as e:
                    st.error(f"AI 분석 오류: {e}")

    st.divider()

    # 2. 저장 폼
    with st.form("rent_save_form"):
        st.subheader("📝 내용 확인 및 저장")
        
        # 데이터 채우기
        data = st.session_state.rent_data or {}
        
        # 날짜 처리
        val_date = datetime.date.today()
        if data.get("date"):
            try: val_date = datetime.datetime.strptime(data["date"], "%Y-%m-%d").date()
            except: pass
            
        # 항목 처리
        opts = ["월세", "전기세", "수도세", "관리비", "기타"]
        val_cat = data.get("category", "관리비")
        idx_cat = opts.index(val_cat) if val_cat in opts else 3
        
        c1, c2 = st.columns(2)
        date_in = c1.date_input("납부일", val_date)
        cat_in = c2.selectbox("항목", opts, index=idx_cat)
        
        # 금액 처리 (콤마 제거 등)
        raw_amt = str(data.get("amount", 0)).replace(',', '')
        try: val_amt = int(raw_amt)
        except: val_amt = 0
            
        amt_in = st.number_input("금액 (원)", value=val_amt, step=1000)
        memo_in = st.text_input("메모", value=data.get("memo", ""))
        
        if st.form_submit_button("💾 시트에 저장"):
            sheet = get_sheet()
            if sheet:
                try:
                    # 모든 데이터를 문자열로 변환하여 저장 (오류 최소화)
                    sheet.append_row([str(date_in), cat_in, amt_in, memo_in])
                    st.success("저장되었습니다!")
                    st.session_state.rent_data = None # 초기화
                    st.rerun() # 즉시 반영을 위해 새로고침
                except Exception as e:
                    st.error(f"저장 실패: {e}")
            else:
                st.error("연결 실패: 비밀번호(Secrets) 설정을 확인하거나 구글 시트 이름을 확인하세요.")

# [탭 2] 통계 대시보드 (오류 방지 코드 적용)
with tab2:
    st.subheader("📊 관리비 납부 현황")
    if st.button("새로고침"):
        st.rerun()
        
    sheet = get_sheet()
    if sheet:
        try:
            # get_all_records() 대신 get_all_values() 사용 (헤더 오류 원천 차단)
            raw_data = sheet.get_all_values()
            
            if len(raw_data) > 1: # 데이터가 2줄 이상이어야 함 (헤더 + 내용)
                header = raw_data[0]
                rows = raw_data[1:]
                df = pd.DataFrame(rows, columns=header)
                
                # 금액 컬럼 찾기 (보통 3번째: 인덱스 2)
                # 혹시 모르니 컬럼 이름에 '금액'이 들어간 걸 찾음
                amt_col = next((c for c in df.columns if '금액' in c), None)
                
                if amt_col:
                    # 콤마 제거 및 숫자 변환
                    df[amt_col] = pd.to_numeric(df[amt_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                    
                    st.bar_chart(df, x=df.columns[0], y=amt_col, color=df.columns[1])
                    st.dataframe(df, use_container_width=True)
                else:
                    # 금액 컬럼을 못 찾으면 그냥 표만 보여줌
                    st.dataframe(df)
            else:
                st.info("데이터가 없습니다. (헤더만 있거나 비어있음)")
                
        except Exception as e:
            st.error(f"데이터를 불러오는 중 오류가 났습니다: {e}")
    else:
        # creds가 None인 경우 (연결 실패)
        st.warning("⚠️ 구글 시트 연결에 실패했습니다.")
        st.caption("Streamlit Cloud의 Settings > Secrets에 'gcp_service_account'가 올바르게 들어있는지 확인해주세요.")
