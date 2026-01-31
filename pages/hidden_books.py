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
                
                # [핵심] 무조건 작동하는 URL
                # 네이버/교보는 검색 결과로 바로 감 (잘 됨)
                naver_link = f"[https://search.naver.com/search.naver?where=book&query=](https://search.naver.com/search.naver?where=book&query=){query}"
                kyobo_link = f"[https://search.kyobobook.co.kr/search?keyword=](https://search.kyobobook.co.kr/search?keyword=){query}"
                
                # 도서관은 '메인 페이지'로 보냄 (검색 결과 페이지는 보안 때문에 404 에러 남)
                yuseong_link = "[https://lib.yuseong.go.kr/](https://lib.yuseong.go.kr/)"
                daejeon_link = "[https://www.u-library.kr/](https://www.u-library.kr/)"

                st.success(f"'{title}'을(를) 찾았습니다.")
                
                with st.container(border=True):
                    st.subheader(f"📖 {title}")
                    st.caption(f"저자: {author}")
                    st.markdown(f"**💭 발굴 이유:** {book_info.get('reason', '')}")
                    st.markdown(f"**❝ 결정적 문장:** *{book_info.get('quote', '')}*")
                
                st.divider()
                st.subheader("🏛️ 링크 모음 (클릭 시 새 창)")
                st.info("👇 책 제목을 복사해서 도서관 검색창에 붙여넣으세요.")
                st.code(title, language="text")

                # [여기가 핵심] Streamlit 버튼 대신 순수 HTML 링크 사용
                # 브라우저가 처리하므로 100% 열림
                st.markdown(f"""
                <style>
                    .custom-link {{
                        display: block;
                        background-color: #f0f2f6;
                        padding: 12px;
                        border-radius: 8px;
                        margin-bottom: 8px;
                        text-decoration: none;
                        color: #31333F;
                        font-weight: bold;
                        border: 1px solid #d6d6d8;
                        text-align: center;
                    }}
                    .custom-link:hover {{
                        background-color: #e0e2e6;
                        border-color: #ff4b4b;
                        color: #ff4b4b;
                    }}
                </style>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <a href="{naver_link}" target="_blank" class="custom-link">📗 네이버 책 (검색결과)</a>
                    <a href="{kyobo_link}" target="_blank" class="custom-link">📕 교보문고 (검색결과)</a>
                    <a href="{yuseong_link}" target="_blank" class="custom-link">🏛️ 유성구 도서관 (메인)</a>
                    <a href="{daejeon_link}" target="_blank" class="custom-link">🔍 대전 통합 도서관 (메인)</a>
                </div>
                """, unsafe_allow_html=True)

            else:
                st.warning("AI 데이터 오류입니다. 다시 눌러주세요.")
    else:
        st.warning("키워드를 입력해주세요.")
