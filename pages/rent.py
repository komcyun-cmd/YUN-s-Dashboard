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
st.set_page_config(page_title="병원 관리비 매니저", page_icon="🏢", layout="wide") # 넓게 보기

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

# [핵심 수정] 원장님 환경에서 가장 잘 돌아가는 호환성 100% 모델명으로 원복
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
st.title("🏢 병원 관리비 세부 매니저")

tab1, tab2 = st.tabs(["📸 고지서 항목별 스캔", "📊 통계 대시보드"])

# ==================================================================
# [탭 1] 고지서 스캔 및 데이터 에디터
# ==================================================================
with tab1:
    st.info("고지서를 올리면 AI가 전기세, 수도세, 관리비 등 '세부 항목'을 쪼개서 표로 만들어 줍니다.")
    
    img_file = st.file_uploader("고지서/영수증 사진 업로드", type=["png", "jpg", "jpeg"])
    
    if "rent_data_list" not in st.session_state:
        st.session_state.rent_data_list = []

    if img_file:
        col_img, col_data = st.columns([1, 2])
        
        with col_img:
            image = Image.open(img_file)
            st.image(image, caption="고지서 미리보기", use_container_width=True)
            
            if st.button("🔍 세부 내역 추출하기", type="primary", use_container_width=True):
                with st.spinner("AI가 항목별로 금액을 쪼개는 중입니다..."):
                    try:
                        # [핵심] 단일 JSON이 아닌 JSON 배열(List)로 요구
                        prompt = """
                        당신은 꼼꼼한 관리비 고지서 분석기입니다.
                        이미지의 세부 청구 내역을 분석해서, 각 항목을 분리해 **JSON 배열(Array)** 형태로 답하세요.
                        
                        [분류 규칙]
                        - category는 무조건 ["월세", "전기세", "수도세", "관리비", "수선적립금", "기타"] 중 하나만 쓰세요.
                        - 장기수선충당금, 수선유지비 등은 무조건 '수선적립금'
                        - 세대 전기료, 공동 전기료 등은 합쳐서 '전기세'
                        - 일반관리비, 청소비, 승강기유지비 등은 합쳐서 '관리비'
                        
                        [출력 형식 예시] (반드시 아래처럼 배열로 줄 것, 다른 말 금지)
                        [
                            {"date": "2026-02-25", "category": "관리비", "amount": 150000, "memo": "일반관리비 및 청소비"},
                            {"date": "2026-02-25", "category": "전기세", "amount": 55000, "memo": "공동전기 포함"},
                            {"date": "2026-02-25", "category": "수선적립금", "amount": 20000, "memo": "장기수선충당금"}
                        ]
                        """
                        response = model.generate_content([prompt, image])
                        text = response.text
                        
                        # 대괄호 [ ... ] 영역만 추출
                        text = text.replace("```json", "").replace("```python", "").replace("```", "").strip()
                        match = re.search(r'\[.*\]', text, re.DOTALL)
                        
                        if match:
                            text_data = match.group()
                            try:
                                parsed_list = json.loads(text_data)
                            except:
                                parsed_list = ast.literal_eval(text_data)
                                
                            # 딕셔너리로 잘못 왔을 경우 대비 (리스트로 감싸줌)
                            if isinstance(parsed_list, dict):
                                parsed_list = [parsed_list]
                                
                            st.session_state.rent_data_list = parsed_list
                            st.rerun() # 데이터 에디터를 그리기 위해 새로고침
                        else:
                            st.error("항목을 분리하지 못했습니다. 글자가 잘 보이는지 확인해주세요.")
                            
                    except Exception as e:
                        st.error(f"오류: {e}")

        with col_data:
            if st.session_state.rent_data_list:
                st.subheader("📝 세부 내역 확인 및 수정")
                st.caption("엑셀처럼 표를 클릭해서 금액이나 항목을 직접 수정하고, 불필요한 행은 삭제할 수 있습니다.")
                
                # DataFrame 변환
                df = pd.DataFrame(st.session_state.rent_data_list)
                
                # 필수 컬럼 보장
                for col in ["date", "category", "amount", "memo"]:
                    if col not in df.columns:
                        df[col] = ""
                
                # 날짜 형식 변환 (문자열 -> datetime object)
                df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
                df['date'] = df['date'].fillna(datetime.date.today())
                
                # 금액 형식 변환 (숫자)
                df['amount'] = pd.to_numeric(df['amount'].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)

                # st.data_editor (웹 엑셀) 적용
                opts = ["월세", "전기세", "수도세", "관리비", "수선적립금", "기타"]
                
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "date": st.column_config.DateColumn("납부/청구일", required=True),
                        "category": st.column_config.SelectboxColumn("항목 분류", options=opts, required=True),
                        "amount": st.column_config.NumberColumn("금액 (원)", min_value=0, step=1000, required=True),
                        "memo": st.column_config.TextColumn("메모")
                    },
                    num_rows="dynamic", # 사용자 행 추가/삭제 허용
                    use_container_width=True,
                    hide_index=True
                )
                
                total_sum = edited_df['amount'].sum()
                st.info(f"🧾 **총 합계:** {total_sum:,}원")

                if st.button("💾 위 내역 구글 시트에 일괄 저장", type="primary"):
                    sheet = get_sheet()
                    if sheet:
                        try:
                            # 데이터프레임을 리스트로 변환하여 구글 시트에 다중 행(Multiple Rows) 한 번에 추가
                            edited_df['date'] = edited_df['date'].astype(str)
                            rows_to_insert = edited_df[["date", "category", "amount", "memo"]].values.tolist()
                            
                            sheet.append_rows(rows_to_insert) # 여러 줄 한 번에 쏘기!
                            
                            st.success(f"✅ {len(rows_to_insert)}건의 세부 항목이 구글 시트에 저장되었습니다!")
                            st.session_state.rent_data_list = [] # 폼 초기화
                        except Exception as e:
                            st.error(f"저장 실패: {e}")
                    else:
                        st.error("구글 시트 연결 실패!")

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
            if len(raw_data) > 1:
                df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
                
                amt_col = next((c for c in df.columns if '금액' in c), None)
                cat_col = next((c for c in df.columns if '항목' in c), None)

                if amt_col and cat_col:
                    df[amt_col] = pd.to_numeric(df[amt_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                    
                    total_reserve = df[df[cat_col] == '수선적립금'][amt_col].sum()
                    total_others = df[df[cat_col] != '수선적립금'][amt_col].sum()
                    total_all = df[amt_col].sum()
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("💰 순수 지출 총합", f"{total_others:,.0f}원", delta="운영 비용", delta_color="inverse")
                    m2.metric("🏗️ 수선적립금 누적", f"{total_reserve:,.0f}원", delta="저축성", delta_color="normal")
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
                    st.warning("구글 시트에 '항목' 또는 '금액'이라는 이름의 열이 없습니다.")
            else:
                st.info("데이터가 없습니다.")
        except Exception as e:
            st.error(f"오류: {e}")
