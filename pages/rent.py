import streamlit as st
from PIL import Image
import google.generativeai as genai
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import pandas as pd
import re

# ------------------------------------------------------------------
# [1] 설정 영역
# ------------------------------------------------------------------
GEMINI_API_KEY = "AIzaSyAVTOCvgX62QR3L3GsWQ3Cd3Hr4T-NTpCk"

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

if os.path.exists(os.path.join(root_dir, "secrets.json")):
    SECRET_FILE = os.path.join(root_dir, "secrets.json")
elif os.path.exists(os.path.join(current_dir, "secrets.json")):
    SECRET_FILE = os.path.join(current_dir, "secrets.json")
else:
    SECRET_FILE = "secrets.json"

SHEET_NAME = "My_Dashboard_DB"
TAB_NAME = "관리비"

# ------------------------------------------------------------------
# [2] 기능 함수들
# ------------------------------------------------------------------
def configure_genai():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel('gemini-flash-latest')
    except Exception as e:
        st.error(f"AI 설정 오류: {e}")
        return None

def get_google_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(SECRET_FILE, scope)
        client = gspread.authorize(creds)
        return client.open(SHEET_NAME).worksheet(TAB_NAME)
    except Exception as e:
        st.error(f"구글 시트 연결 실패: {e}")
        return None

def load_data():
    sheet = get_google_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty and '금액' in df.columns:
                df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',',''), errors='coerce').fillna(0)
            return df
        except:
            pass
    return pd.DataFrame()

def extract_json(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return None

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.set_page_config(page_title="관리비 매니저", page_icon="🏢", layout="wide")
st.title("🏢 병원 관리비 매니저")

tab1, tab2 = st.tabs(["📸 고지서 스캔", "📊 통계 대시보드"])

# [탭 1] 스캔 및 저장
with tab1:
    st.write("### 🧾 고지서를 찍어주세요")
    uploaded_file = st.file_uploader("사진 업로드", type=["jpg", "png", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, width=400, caption='업로드된 고지서')
        
        if st.button("🔍 상세 분석 및 저장", key="scan_btn"):
            model = configure_genai()
            with st.spinner('AI 분석 중 (부가세 계산 포함)...'):
                try:
                    # ==========================================================
                    # 🔴 [수정됨] 부가세 계산 명령 추가된 프롬프트
                    # ==========================================================
                    prompt = """
                    이 관리비 고지서 이미지를 정밀 분석해줘.
                    
                    [지시사항]
                    1. 청구년월(YYYY-MM)을 추출해.
                    2. **상세 내역 분리**: '관리운영비' 뭉뚱그린 금액 말고, 하단의 '산출근거'에 있는 작은 항목들(일반관리비, 청소비 등)을 다 분리해.
                    3. **주요 항목**: 전기요금, 수도요금, 수선적립금 등도 포함해.
                    4. **🔴 중요: 부가세(VAT) 추가**: 
                       - '관리운영비'와 '전기요금' 옆에 '(부가세 10%)'라고 적혀 있으면, 해당 항목들의 10% 금액을 계산해서 **'부가세'**라는 별도 항목으로 반드시 추가해.
                       - 예: (관리운영비+전기요금) * 0.1 = 부가세
                       - 모든 항목의 합계가 고지서에 적힌 '총 합계금액(1,827,440원 등)'과 거의 일치해야 해.
                    5. 출력은 오직 JSON 형식으로만 해.

                    Example output:
                    { 
                      "date": "2026-01", 
                      "items": { 
                        "일반관리비": 466050, 
                        "전기요금": 976530, 
                        "수도요금": 50360,
                        "부가세": 161550,
                        "수선적립금": 50000 
                      }, 
                      "total": 1877440 
                    }
                    """
                    response = model.generate_content([prompt, image])
                    
                    data = extract_json(response.text)
                    if data is None:
                        st.error("AI 응답 오류. 다시 시도해주세요.")
                        st.stop()

                    items = data.get('items', {})
                    if not items:
                        items = {k: v for k, v in data.items() if k not in ['date', 'total', '청구년월', '합계']}
                    
                    billing_date = data.get('date', datetime.now().strftime("%Y-%m"))
                    
                    # 총합 검증 (화면에 보여주기용)
                    calc_total = sum(items.values())

                    st.success("✅ 분석 완료!")
                    
                    # 큼지막하게 총액 보여주기
                    col1, col2 = st.columns(2)
                    col1.metric("📅 청구월", billing_date)
                    col2.metric("💰 인식된 총액", f"{calc_total:,} 원")
                    
                    st.write("📋 **추출된 상세 내역 (부가세 포함)**")
                    st.json(items)
                    
                    # 시트 저장
                    if items:
                        sheet = get_google_sheet()
                        if sheet:
                            save_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            rows_to_add = []
                            for item_name, amount in items.items():
                                rows_to_add.append([billing_date, item_name, amount, save_time])
                            
                            sheet.append_rows(rows_to_add)
                            st.toast(f"💾 {len(rows_to_add)}개 항목 저장 성공!", icon="🎉")
                            st.balloons()
                    
                except Exception as e:
                    st.error(f"오류: {e}")

# [탭 2] 대시보드
with tab2:
    st.write("### 📊 관리비 추세")
    if st.button("🔄 데이터 새로고침"):
        st.rerun()

    df = load_data()
    if not df.empty:
        monthly_sum = df.groupby('청구월')['금액'].sum()
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("#### 📅 월별 총액")
            st.dataframe(monthly_sum.map('{:,.0f}원'.format))
        with c2:
            st.markdown("#### 📈 추이 그래프")
            st.bar_chart(monthly_sum)
            
        st.divider()
        st.markdown("#### 🔎 이번 달 지출 비중")
        latest_month = df['청구월'].max()
        latest_df = df[df['청구월'] == latest_month]
        
        if not latest_df.empty:
            st.bar_chart(latest_df.set_index('항목명')['금액'], horizontal=True)
    else:
        st.info("데이터가 없습니다. [고지서 스캔] 탭에서 데이터를 추가해주세요!")