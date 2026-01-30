import streamlit as st
import datetime

# ------------------------------------------------------------------
# [1] 페이지 설정
# ------------------------------------------------------------------
st.set_page_config(
    page_title="YUN's Intelligent HQ",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ------------------------------------------------------------------
# [2] 헤더 및 인사말
# ------------------------------------------------------------------
st.title("🏥 YUN's Intelligent HQ")
st.markdown(f"**{datetime.date.today().strftime('%Y년 %m월 %d일')}**, 오늘도 최고의 하루를 설계하세요.")
st.divider()

# ------------------------------------------------------------------
# [3] 대시보드 그리드
# ------------------------------------------------------------------

col_left, col_right = st.columns(2)

# === [왼쪽 컬럼] ===
with col_left:
    # 1. 🌅 하루의 시작
    with st.container(border=True):
        st.subheader("🌅 Daily & Productivity")
        st.caption("하루를 시작하고 기록하는 공간")
        
        st.page_link("pages/today.py", label="오늘의 브리핑 (날씨/할일)", icon="📅")
        st.page_link("pages/newsletter.py", label="뉴스레터 요약기", icon="📰")
        st.page_link("pages/obsidian.py", label="지식 수집 (Obsidian)", icon="🧠")

    # 2. 💰 자산 & 병원
    with st.container(border=True):
        st.subheader("💰 Asset & Management")
        st.caption("투자와 병원 경영 관리")
        
        # 머니 플로우
        st.page_link("pages/flow.py", label="🐋 머니 플로우 (자금 추적기)", icon="🌊")
        # 미국 증시
        st.page_link("pages/us_market.py", label="🇺🇸 월스트리트 인사이드", icon="🗽")
        
        st.page_link("pages/valuation.py", label="🧮 적정 주가 판독기 (S-RIM)", icon="⚖️")
        st.page_link("pages/stock.py", label="📈 주식 시장 대시보드", icon="📊")
        st.page_link("pages/investment.py", label="👨‍⚖️ 워렌 버핏의 투자 청문회", icon="🎤")
        st.page_link("pages/rent.py", label="🏢 병원 관리비 매니저", icon="🧾")

# === [오른쪽 컬럼] ===
with col_right:
    # 3. 👨‍👩‍👧‍👦 가족 & 라이프 & 휴식
    with st.container(border=True):
        st.subheader("☕ Life & Inspiration")
        st.caption("가족과의 시간, 그리고 나만의 지적 유희")
        
        # [NEW] 심해의 서재 추가!
        st.page_link("pages/hidden_books.py", label="심해의 서재 (숨은 명저 찾기)", icon="🕯️")
        
        st.page_link("pages/movie.py", label="우리 가족 시네마", icon="🎬")
        st.page_link("pages/travel.py", label="가족 여행 플래너", icon="✈️")
        st.page_link("pages/lens.py", label="닥터의 만물 도감", icon="🔍")
        st.page_link("pages/dream.py", label="프로이트의 꿈 해몽", icon="🔮")

    # 4. 🛠️ 스마트 도구
    with st.container(border=True):
        st.subheader("🛠️ Smart Tools")
        st.caption("AI가 당신의 시간을 벌어줍니다.")
        
        st.page_link("pages/youtube.py", label="유튜브 인사이트 채굴기", icon="⛏️")
        st.page_link("pages/pdf_summary.py", label="논문/보고서 3초 요약기", icon="📑")
        
        st.page_link("pages/decision.py", label="결정의 신 (A vs B)", icon="⚖️")
        st.page_link("pages/sms.py", label="환자 안부 문자 (CRM)", icon="📨")
        st.page_link("pages/english.py", label="글로벌 젠틀맨 (영어)", icon="👔")

# ------------------------------------------------------------------
# [4] 하단 상태바
# ------------------------------------------------------------------
st.divider()
st.caption("🚀 Powered by **Gemini AI** | Dr. Kim's Private System ✅")
