import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import datetime
import altair as alt # 예쁜 그래프 그리는 도구

# ------------------------------------------------------------------
# [1] 기본 설정
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Dr.Kim's Dashboard",
    page_icon="👨‍⚕️",
    layout="wide"
)

# ------------------------------------------------------------------
# [2] 데이터 연결 (구글 시트)
# ------------------------------------------------------------------
# 키 파일 찾기 (Main.py랑 같은 위치 혹은 pages 폴더 확인)
if "gcp_service_account" in st.secrets:
    # 클라우드 배포 환경
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
else:
    # 내 컴퓨터(로컬) 환경
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    if os.path.exists("secrets.json"):
        SECRET_FILE = "secrets.json"
    elif os.path.exists(os.path.join("pages", "secrets.json")):
        SECRET_FILE = os.path.join("pages", "secrets.json")
    else:
        SECRET_FILE = "secrets.json"
        
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(SECRET_FILE, scope)
    except:
        creds = None

def load_data():
    """구글 시트에서 관리비 데이터를 싹 긁어옵니다."""
    try:
        if creds is None:
            return pd.DataFrame()

        client = gspread.authorize(creds)
        sheet = client.open("My_Dashboard_DB").worksheet("관리비")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty:
            return pd.DataFrame()
            
        # 금액 숫자로 변환 (콤마 제거)
        if '금액' in df.columns:
            df['금액'] = pd.to_numeric(df['금액'].astype(str).str.replace(',',''), errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"데이터 불러오기 오류: {e}")
        return pd.DataFrame()

# ------------------------------------------------------------------
# [3] 화면 구성 (Real-Time Dashboard)
# ------------------------------------------------------------------
st.title("👨‍⚕️ 김 원장의 종합 상황실")
st.markdown(f"**{datetime.datetime.now().strftime('%Y년 %m월 %d일')}** 주요 지표 브리핑")

st.divider()

# 데이터 로딩
df = load_data()

# 1. 상단 요약 지표 (Metrics)
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🏢 관리비 현황")
    if not df.empty:
        # 가장 최근 달 데이터 찾기
        latest_month = df['청구월'].max()
        # 그 달의 총액 계산 (여러 항목 합산)
        this_month_total = df[df['청구월'] == latest_month]['금액'].sum()
        
        st.metric(
            label=f"{latest_month} 청구액",
            value=f"{this_month_total:,.0f}원",
            delta="데이터 누적 중..." # 나중에 전월 대비 계산 로직 추가 가능
        )
    else:
        st.info("데이터가 없습니다.")

with col2:
    st.subheader("📈 투자 포트폴리오")
    st.metric(label="Tesla (TSLA)", value="$235.40", delta="-1.2%")

with col3:
    st.subheader("📰 오늘의 뉴스")
    st.success("✅ [할일] 관리비 데이터 확인")

st.divider()

# 2. 메인 그래프 (진짜 데이터 연동)
st.subheader("📊 병원 관리비 추세 (Real-Time)")

if not df.empty:
    # 월별 총액 계산 (항목들 다 합쳐서 월별로 묶기)
    monthly_trend = df.groupby('청구월')['금액'].sum().reset_index()
    
    # 막대 그래프 그리기 (최신순 정렬)
    chart = alt.Chart(monthly_trend).mark_bar().encode(
        x=alt.X('청구월', sort=None),
        y=alt.Y('금액', title='청구 금액(원)'),
        color=alt.value("#4C78A8"),
        tooltip=['청구월', alt.Tooltip('금액', format=',.0f')]
    ).properties(
        height=300
    )
    
    st.altair_chart(chart, use_container_width=True)
    
    # 3. 상세 표 보여주기 (접었다 폈다 가능)
    with st.expander("📋 상세 데이터 대장 보기"):
        st.dataframe(df.sort_values(by='청구월', ascending=False), use_container_width=True)

else:
    st.info("📉 아직 저장된 관리비 데이터가 없습니다. 왼쪽 메뉴 [관리비 매니저]에서 고지서를 등록해주세요.")
    
st.caption("※ 이 데이터는 구글 시트 'My_Dashboard_DB'에서 실시간으로 가져옵니다.")
