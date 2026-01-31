import streamlit as st
import google.generativeai as genai
import json
import urllib.parse
import re
import ast

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="심해의 서재", page_icon="🕯️", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 기능 함수
# ------------------------------------------------------------------
def generate_recommendation(category, keyword):
    prompt = f"""
    당신은 50년 경력의 고집 센 '헌책방 주인'입니다.
    사용자가 '{category}' 분야에서 '{keyword}'와 관련된 책을 찾습니다.
    
    [절대 금지]
    1. 베스트셀러, 누구나 아는 유명한 책 금지.
    2. 자기계발서 금지.
    3. 절판된 책 절대 금지.
    
    [필수 출력 형식 - Python Dictionary]
    반드시 아래 파이썬 딕셔너리 형태로 답변해. 설명 붙이지 마.
    {{
        "title": "책 제목",
        "author": "저자",
        "reason": "추천 이유",
        "quote": "결정적 문장",
        "target": "추천 대상"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        # 데이터 정제
        text = text.replace("```json", "").replace("```python", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if match:
            text_data = match.group()
            try:
                return json.loads(text_data)
            except:
                return ast.literal_eval(text_data)
        else:
            return None
    except:
        return None

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.title("🕯️ 심해의 서재 (Hidden Gems)")
st.caption("베스트셀러는 거부합니다. 하지만 '구할 수 있는' 숨은 명저만 엄선합니다.")

st.divider()

col1, col2 = st.columns([1, 2])
with col1:
    category = st.selectbox(
        "관심 분야", 
        ["인문/철학", "투자/경제", "의학/과학", "심리/인간본성", "예술/에세이", "소설/문학"]
    )
with col2:
    keyword = st.text_input("현재의 갈증 키워드", placeholder="예: 본질, 고독, 역발상 투자...")

if st.button("서고 탐색 시작 🗝️", type="primary"):
    if keyword:
        with st.spinner("먼지 쌓인 서가에서 보물을 찾는 중입니다..."):
            book_info = generate_recommendation(category, keyword)
            
            if book_info:
                title = book_info.get('title', '제목 없음')
                author = book_info.get('author', '저자 미상')
                
                # 검색어 인코딩
                query = urllib.parse.quote(title)
                
                # [핵심 수정] 절대 안 깨지는 메인 링크들
                naver_link = f"[https://search.naver.com/search.naver?query=](https://search.naver.com/search.naver?query=){query}+책"
                kyobo_link = f"[https://search.kyobobook.co.kr/search?keyword=](https://search.kyobobook.co.kr/search?keyword=){query}"
                yuseong_link = "[https://lib.yuseong.go.kr/](https://lib.yuseong.go.kr/)"
                daejeon_link = "[https://www.u-library.kr/](https://www.u-library.kr/)"

                st.success(f"'{title}'을(를) 찾았습니다.")
                
                # 1. 책 정보 카드
                with st.container(border=True):
                    st.subheader(f"📖 {title}")
                    st.caption(f"저자: {author}")
                    st.markdown(f"**💭 발굴 이유:** {book_info.get('reason', '')}")
                    st.markdown(f"**❝ 결정적 문장:** *{book_info.get('quote', '')}*")
                
                # 2. 확실한 이동 링크 (HTML)
                st.divider()
                st.subheader("🏛️ 소장 확인 및 구매")
                st.info("👇 아래 제목을 복사(Ctrl+C)한 뒤, 링크를 눌러 검색창에 붙여넣으세요.")
                
                # 제목 복사 영역
                st.code(title, language="text")
                
                # HTML 링크 모음 (버튼 아님, 순수 링크)
                st.markdown(f"""
                <style>
                .link-box {{
                    padding: 10px;
                    border-radius: 5px;
                    background-color: #f0f2f6;
                    margin-bottom: 5px;
                    font-weight: bold;
                }}
                a {{ text-decoration: none; }}
                </style>
                
                <div class="link-box">
                    📗 <a href="{naver_link}" target="_blank">네이버 책 정보 보기 (새창)</a>
                </div>
                <div class="link-box">
                    📕 <a href="{kyobo_link}" target="_blank">교보문고 재고 확인 (새창)</a>
                </div>
                <div class="link-box">
                    🏛️ <a href="{yuseong_link}" target="_blank">유성구 통합도서관 이동 (새창)</a>
                </div>
                <div class="link-box">
                    🔍 <a href="{daejeon_link}" target="_blank">대전 사이버 도서관 이동 (새창)</a>
                </div>
                """, unsafe_allow_html=True)

            else:
                st.warning("AI가 추천을 생성했지만 형식이 불안정했습니다. 다시 한 번만 눌러주세요! 🙏")
    else:
        st.warning("키워드를 입력해야 책을 찾을 수 있습니다.")
