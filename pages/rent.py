import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
from PIL import Image
import datetime
import json
import re
import ast

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
        # 구글 시트 이름과 워크시트 이름이 정확해야 합니다.
        return client.open("My_Dashboard_DB").worksheet("관리비") 
    except: return None

# ------------------------------------------------------------------
# [2] 화면 구성
# ------------------------------------------------------------------
st.title("🏢 병원 관리비 매니저")

tab1, tab2 = st.tabs(["📸 고지서 스캔 및 저장", "📊 통계 대시보드"])

# ==================================================================
# [탭 1] 고지서 스캔 및 저장
# ==================================================================
with tab1:
    st.info("고지서 사진을 올리면 AI가 분석하고, 구글 시트에 바로 저장합니다.")
    
    img_file = st.file_uploader("고지서/영수증 사진 업로드", type=["png", "jpg", "jpeg"])
    
    # AI가 분석한 데이터를 임시 저장할 세션 스테이트
    if "rent_data" not in st.session_state:
        st.session_state.rent_data = None

    if img_file:
        image = Image.open(img_file)
        st.image(image, caption="고지서 미리보기", use_container_width=True)
        
        if st.button("🔍 내용 추출하기", type="primary"):
            with st.spinner("AI가 고지서를 읽고 분류 중입니다..."):
                try:
                    # AI에게 줄 명확한 지시사항
                    prompt = """
                    당신은 정확한 영수증 분석기입니다.
                    이 이미지에서 정보를 추출해서 오직 아래 JSON 형식으로만 답하세요. 부가 설명은 절대 금지합니다.
                    
                    항목(category)은 [월세, 전기세, 수도세, 관리비, 수선적립금, 기타] 중에서 가장 적절한 것을 골라주세요.
                    특히 '장기수선충당금'이나 '수선적립금'이라는 단어가 있으면 category를 무조건 '수선적립금'으로 하세요.
                    
                    {
                        "date": "YYYY-MM-DD", 
                        "category": "분류", 
                        "amount": 숫자만(예: 150000), 
                        "memo": "납부기한이나 기타 특징 (짧게)"
                    }
                    """
                    response = model.generate_content([prompt, image])
                    text = response.text
                    
                    # [핵심] AI 잡담 제거 및 데이터 강제 추출
                    text = text.replace("```json", "").replace("```python", "").replace("```", "").strip()
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    
                    if match:
                        text_data = match.group()
                        try:
                            st.session_state.rent_data = json.loads(text_data)
                        except:
                            st.session_state.rent_data = ast.literal_eval(text_data)
                            
                        st.toast("✨ 분석 성공! 아래 폼에서 내용을 확인하세요.")
                    else:
                        st.error("데이터를 찾을 수 없습니다. 다시 시도해주세요.")
                        
                except Exception as e:
                    st.error(f"오류: {e}")

    st.divider()

    # 입력/수정 및 저장 폼 (session_state 활용)
    with st.form("save_form"):
        st.subheader("📝 내용 확인 및 저장")
        data = st.session_state.rent_data or {}
        
        # 날짜 기본값 세팅
        d_val = datetime.date.today()
        if data.get("date"):
            try: d_val = datetime.datetime.strptime(data["date"], "%Y-%m-%d").date()
            except: pass
        
        # 카테고리 세팅
        opts = ["월세", "전기세", "수도세", "관리비", "수선적립금", "기타"]
        c_val = data.get("category", "관리비")
        idx_cat = opts.index(c_val) if c_val in opts else 3
        
        c1, c2 = st.columns(2)
        date_in = c1.date_input("납부/청구일", d_val)
        cat_in = c2.selectbox("항목 분류", opts, index=idx_cat)
        
        # 금액 세팅 (콤마 제거나 숫자 변환 오류 방지)
        raw_amt = str(data.get("amount", 0)).replace(',', '').replace('원', '').strip()
        try: val_amt = int(raw_amt)
        except: val_amt = 0
            
        amt_in = st.number_input("청구 금액 (원)", value=val_amt, step=1000)
        memo_in = st.text_input("메모 (선택)", value=data.get("memo", ""))
        
        # 시트 저장 버튼
        if st.form_submit_button("💾 시트에 저장 및 분류"):
            sheet = get_sheet()
            if sheet:
                try:
                    # [날짜, 항목, 금액, 메모] 순서로 구글 시트에 행 추가
                    sheet.append_row([str(date_in), cat_in, amt_in, memo_in])
                    st.success("✅ 구글 시트에 안전하게 저장되었습니다!")
                    # 저장 완료 후 세션 초기화
                    st.session_state.rent_data = None
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: 구글 시트 연결을 확인하세요. ({e})")
            else:
                st.error("구글 시트에 연결할 수 없습니다. secrets.json 또는 권한을 확인하세요.")

# ==================================================================
# [탭 2] 통계 대시보드
# ==================================================================
with tab2:
    col_head, col_btn = st.columns([4, 1])
    with col_head:
        st.subheader("📊 병원 관리비 종합 분석")
    with col_btn:
        if st.button("데이터 새로고침 🔄"):
            st.rerun()
        
    sheet = get_sheet()
    if sheet:
        try:
            raw_data = sheet.get_all_values()
            # 헤더(첫 줄)를 포함하여 데이터가 있는지 확인
            if len(raw_data) > 1:
                df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
                
                # '금액'과 '항목'이라는 단어가 들어간 컬럼을 자동 찾기
                amt_col = next((c for c in df.columns if '금액' in c), None)
                cat_col = next((c for c in df.columns if '항목' in c), None)

                if amt_col and cat_col:
                    # 문자열로 된 금액을 숫자로 변환 (콤마 제거)
                    df[amt_col] = pd.to_numeric(df[amt_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                    
                    # 수선적립금(저축성)과 순수 지출 분리 계산
                    total_reserve = df[df[cat_col] == '수선적립금'][amt_col].sum()
                    total_others = df[df[cat_col] != '수선적립금'][amt_col].sum()
                    total_all = df[amt_col].sum()
                    
                    # 3단 메트릭 카드 표시
                    m1, m2, m3 = st.columns(3)
                    m1.metric("💰 순수 지출 총합", f"{total_others:,.0f}원", delta="운영 소모비용", delta_color="inverse")
                    m2.metric("🏗️ 수선적립금 누적", f"{total_reserve:,.0f}원", delta="돌려받을 자산", delta_color="normal")
                    m3.metric("🧾 총 납부 합계", f"{total_all:,.0f}원")
                    
                    st.divider()
                    
                    c_chart, c_table = st.columns([1, 1])
                    with c_chart:
                        st.caption("📈 항목별 지출 비중")
                        group_df = df.groupby(cat_col)[amt_col].sum()
                        st.bar_chart(group_df)
                        
                    with c_table:
                        st.caption("📋 전체 납부 상세 내역")
                        st.dataframe(df.sort_values(by=df.columns[0], ascending=False), use_container_width=True, hide_index=True)
                        
                else:
                    st.warning("구글 시트에 '항목' 또는 '금액'이라는 이름의 열(Column)이 필요합니다.")
            else:
                st.info("아직 구글 시트에 저장된 데이터가 없습니다. 탭 1에서 고지서를 스캔해 보세요!")
        except Exception as e:
            st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    else:
        st.error("구글 시트에 연결되지 않았습니다.")
