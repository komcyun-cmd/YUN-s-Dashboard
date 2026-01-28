import streamlit as st
import datetime

# ------------------------------------------------------------------
# [1] 페이지 설정
# ------------------------------------------------------------------
st.set_page_config(
    page_title="YUN's Intelligent HQ", 
    page_icon="🏥", 
    layout="wide" # 넓은 화면 사용
)

# ------------------------------------------------------------------
# [2] 헤더 및 인사말
# ------------------------------------------------------------------
st.title("🏥 YUNs Intelligent HQ")
st.markdown(f"**{datetime.date.today().strftime('%Y년 %m월 %d일')}**, 오늘도 최고의 하루를 설계하세요.")
st.divider()

# ------------------------------------------------------------------
# [3] 대시보드 그리드 (카테고리별 정리)
# ------------------------------------------------------------------

# 2단 레이아웃 (왼쪽: 데일리/투자, 오른쪽: 라이프/도구)
col_left, col_right = st.columns(2)

# === [왼쪽 컬럼] ===
with col_left:
    # 1. 🌅 하루의 시작 & 생산성
    with st.container(border=True):
        st.subheader("🌅 Daily & Productivity")
        st.caption("하루를 시작하고 기록하는 공간입니다.")
        
        st.page_link("pages/today.py", label="오늘의 브리핑 (날씨/역사/할일)", icon="📅")
        st.page_link("pages/newsletter.py", label="뉴스레터 요약기", icon="📰")
        st.page_link("pages/obsidian.py", label="지식 수집 (Obsidian Connector)", icon="🧠")

    # 2. 💰 자산 & 병원 경영
    with st.container(border=True):
        st.subheader("💰 Asset & Management")
        st.caption("투자와 자산을 빈틈없이 관리합니다.")
        
        st.page_link("pages/stock.py", label="주식 시장 대시보드", icon="📈")
        st.page_link("pages/investment.py", label="워렌 버핏의 투자 청문회", icon="👨‍⚖️")
        st.page_link("pages/rent.py", label="병원 관리비 & 임대료", icon="🏢")

# === [오른쪽 컬럼] ===
with col_right:
    # 3. 👨‍👩‍👧‍👦 가족 & 라이프스타일
    with st.container(border=True):
        st.subheader("👨‍👩‍👧‍👦 Family & Lifestyle")
        st.caption("가족과의 시간과 개인의 취향을 챙깁니다.")
        
        st.page_link("pages/travel.py", label="가족 여행 플래너 & 맛집 검증", icon="✈️")
        st.page_link("pages/movie.py", label="우리 가족 시네마 천국", icon="🎬")
        st.page_link("pages/lens.py", label="닥터의 만물 도감 (이미지 분석)", icon="🔍")
        st.page_link("pages/dream.py", label="프로이트의 꿈 해몽", icon="🔮")

    # 4. 🛠️ 스마트 도구 & 커뮤니케이션
    with st.container(border=True):
        st.subheader("🛠️ Smart Tools")
        st.caption("복잡한 고민과 업무를 AI가 해결해줍니다.")
        
        st.page_link("pages/decision.py", label="결정의 신 (A vs B 선택)", icon="⚖️")
        st.page_link("pages/sms.py", label="환자 안부 문자 (CRM)", icon="📨")
        st.page_link("pages/english.py", label="글로벌 젠틀맨 (영어 비서)", icon="👔")

# ------------------------------------------------------------------
# [4] 하단 상태바
# ------------------------------------------------------------------
st.divider()
st.caption("🚀 Powered by **Gemini AI** & **Streamlit** | System Status: **Online** ✅")

