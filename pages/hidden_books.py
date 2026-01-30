import streamlit as st
import google.generativeai as genai

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="심해의 서재", page_icon="🕯️", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 화면 구성
# ------------------------------------------------------------------
st.title("🕯️ 심해의 서재 (Hidden Gems)")
st.caption("베스트셀러는 취급하지 않습니다. 당신의 영혼을 울릴 '숨은 명저'만 꺼내옵니다.")

st.divider()

# 입력 섹션
col1, col2 = st.columns([1, 2])
with col1:
    category = st.selectbox(
        "관심 분야", 
        ["인문/철학", "투자/경제", "의학/과학", "심리/인간본성", "예술/에세이", "소설/문학"]
    )
with col2:
    keyword = st.text_input("지금 꽂혀있는 키워드나 기분", placeholder="예: 고독, 본질적 가치, 번아웃, 인간 혐오...")

if st.button("서고 깊은 곳 탐색하기 🗝️", type="primary"):
    if keyword:
        with st.spinner("먼지 쌓인 서가에서 보물을 찾는 중입니다..."):
            
            # [핵심] 베스트셀러를 차단하는 강력한 프롬프트
            prompt = f"""
            당신은 50년 경력의 고집 센 '헌책방 주인'이자 '지식 큐레이터'입니다.
            사용자가 '{category}' 분야에서 '{keyword}'와 관련된 책을 찾고 있습니다.
            
            [절대 금지 사항]
            - 교보문고/아마존 베스트셀러 상위권 책 추천 금지.
            - 누구나 아는 책(예: 사피엔스, 부자 아빠, 총균쇠, 미움받을 용기 등) 추천 금지.
            - 자기계발서 류의 가벼운 책 금지.
            
            [추천 기준]
            - 대중에게는 잊혀졌으나 전문가들은 '인생의 책'으로 꼽는 책.
            - 절판되었거나 구하기 힘들어도 깊이가 압도적인 책.
            - 시대를 초월한 통찰이 있는 고전 혹은 숨겨진 걸작.
            
            [작성 포맷]
            1. **책 제목 (저자)**
            2. **발굴 이유**: 왜 이 책이 흔한 베스트셀러보다 나은가? (솔직하고 시니컬하게)
            3. **결정적 문장**: 책 내용을 관통하는 한 문장 인용.
            4. **추천 대상**: 구체적으로 어떤 상황의 사람에게 필요한가?
            
            책은 딱 1권만, 깊이 있게 추천해줘.
            """
            
            try:
                response = model.generate_content(prompt)
                st.markdown("### 📖 당신을 위한 발견")
                st.markdown(response.text)
                
                st.info("💡 Tip: 마음에 든다면 중고서점을 뒤져서라도 소장할 가치가 있습니다.")
                
            except Exception as e:
                st.error(f"서재가 너무 어두워 찾지 못했습니다. 다시 시도해주세요. ({e})")
    else:
        st.warning("어떤 지적 갈증을 느끼고 계신지 키워드를 알려주세요.")

st.divider()
st.markdown("""
<div style="text-align:center; color:gray; font-size:0.8em;">
    "좋은 책은 읽는 것이 아니라, 겪는 것이다."
</div>
""", unsafe_allow_html=True)
