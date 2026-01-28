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
# [1] 설정 및 연결
# ------------------------------------------------------------------
st.set_page_config(page_title="병원 관리비 매니저", page_icon="🏢", layout="centered")

# API 키 및 구글 시트 연결
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    if "gcp_service_account" in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    else:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        except:
            creds = None

    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

except Exception as e:
    creds = None

model = genai.GenerativeModel('gemini-flash-latest')

def get_sheet():
    if not creds: return None
    try:
        client = gspread.authorize(creds)
        return client.open("My_Dashboard_DB").worksheet("관리비") 
    except: return None

# ------------------------------------------------------------------
# [2] 화면 구성
# ------------------------------------------------------------------
st.title("🏢 병원 관리비 매니저")

tab1, tab2 = st.tabs(["📸 고지서 스캔", "📊 통계 대시보드"])

# [탭 1] 입력 및 AI 분석
with tab1:
    st.info("고지서 사진을 올리면 AI가 읽어줍니다.")
    
    img_file = st.file_uploader("고지서 사진 업로드", type=["png", "jpg", "jpeg"])
    
    if "rent_data" not in st.session_state:
        st.session_state.rent_data = None

    if img_file:
        image = Image.open(img_file)
        st.image(image, caption="고지서 미리보기", use_container_width=True)
        
        if st.button("🔍 내용 추출하기"):
            with st.spinner("분석 중..."):
                try:
                    # 수선적립금 인식 강화
                    prompt = """
                    이 이미지에서 정보를 JSON으로 추출해.
                    항목(category)은 [월세, 전기세, 수도세, 관리비, 수선적립금, 기타] 중에서 골라줘.
                    특히 '장기수선충당금'이나 '수선적립금'이라는 단어가 있으면 category를 '수선적립금'으로 해.
                    {"date": "YYYY-MM-DD", "category": "...", "amount": 숫자, "memo": "..."}
                    """
                    response = model.generate_content([prompt, image])
                    match = re.search(r'\{.*\}', response.text, re.DOTALL)
                    if match:
                        st.session_state.rent_data = json.loads(match.group())
                        st.toast("분석 성공!")
                except Exception as e:
                    st.error(f"오류: {e}")

    st.divider()

    # 입력 폼
    with st.form("save_form"):
        st.subheader("📝 내용 확인 및 저장")
        data = st.session_state.rent_data or {}
        
        d_val = datetime.date.today()
        if data.get("date"):
            try: d_val = datetime.datetime.strptime(data["date"], "%Y-%m-%d").date()
            except: pass
        
        # [변경] 카테고리에 '수선적립금' 추가
        opts = ["월세", "전기세", "수도세", "관리비", "수선적립금", "기타"]
        c_val = data.get("category", "관리비")
        idx_cat = opts.index(c_val) if c_val in opts else 3
        
        c1, c2 = st.columns(2)
        date_in = c1.date_input("납부일", d_val)
        cat_in = c2.selectbox("항목", opts, index=idx_cat)
        
        # 금액 처리
        raw_amt = str(data.get("amount", 0)).replace(',', '')
        try: val_amt = int(raw_amt)
        except: val_amt = 0
            
        amt_in = st.number_input("금액 (원)", value=val_amt, step=1000)
        memo_in = st.text_input("메모", value=data.get("memo", ""))
        
        if st.form_submit_button("💾 시트에 저장"):
            sheet = get_sheet()
            if sheet:
                try:
                    sheet.append_row([str(date_in), cat_in, amt_in, memo_in])
                    st.success("저장되었습니다!")
                    st.session_state.rent_data = None
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

# [탭 2] 통계 대시보드 (핵심 수정!)
with tab2:
    st.subheader("📊 관리비 분석")
    if st.button("새로고침"):
        st.rerun()
        
    sheet = get_sheet()
    if sheet:
        try:
            raw_data = sheet.get_all_values()
            if len(raw_data) > 1:
                df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
                
                # 금액 컬럼 숫자 변환
                amt_col = next((c for c in df.columns if '금액' in c), None)
                cat_col = next((c for c in df.columns if '항목' in c), None)

                if amt_col and cat_col:
                    df[amt_col] = pd.to_numeric(df[amt_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                    
                    # [핵심] 수선적립금 vs 나머지 분리 계산
                    total_reserve = df[df[cat_col] == '수선적립금'][amt_col].sum()
                    total_others = df[df[cat_col] != '수선적립금'][amt_col].sum()
                    total_all = df[amt_col].sum()
                    
                    # 지표 카드 표시 (Metric)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("💰 순수 지출 총합", f"{total_others:,.0f}원", delta="운영 비용")
                    m2.metric("🏗️ 수선적립금 누적", f"{total_reserve:,.0f}원", delta="저축성", delta_color="off")
                    m3.metric("합계", f"{total_all:,.0f}원")
                    
                    st.divider()
                    
                    # 차트: 항목별 합계
                    st.caption("항목별 비중")
                    group_df = df.groupby(cat_col)[amt_col].sum()
                    st.bar_chart(group_df)
                    
                    st.dataframe(df, use_container_width=True)
                else:
                    st.warning("데이터 형식이 올바르지 않습니다. (항목, 금액 열 확인 필요)")
            else:
                st.info("데이터가 없습니다.")
        except Exception as e:
            st.error(f"데이터 오류: {e}")
