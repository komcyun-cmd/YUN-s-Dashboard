import streamlit as st
import google.generativeai as genai
import json
import urllib.parse
import re
import ast # <--- [핵심] 유연한 해석기 추가

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="심해의 서재", page_icon="🕯️", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 기능 함수 (강력해짐)
# ------------------------------------------------------------------
def generate_recommendation(category, keyword):
    prompt = f"""
    당신은 50년 경력의 고집 센 '헌책방 주인'입니다.
    사용자가 '{category}' 분야에서 '{keyword}'와 관련된 책을 찾습니다.
    
    [절대 금지]
    1. 베스트셀러, 누구나 아는 유명한 책 금지.
    2. 자기계발서 금지.
    3. 절판된 책 절대 금지.
    
    [추천 기준]
    - 대중적이지 않지만 깊이가 압도적인 '숨은 명저'.
    
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
        
        # 1. 마크다운 기호 제거
        text = text.replace("```json", "").replace("```python", "").replace("```", "").strip()
        
        # 2. 중괄호 {} 부분만 추출
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            text_data = match.group()
            
            # 3. [핵심] JSON으로 시도해보고, 안 되면 파이썬 문법으로 해석 시도
            try:
                return json.loads(text_data)
            except:
                # 작은따옴표(') 등을 썼을 경우 여기서 해결됨
                return ast.literal_eval(text_data)
        else:
            return None
    except Exception as e:
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
                # 딕셔너리 키 안전하게 가져오기
                title = book_info.get('title', '제목 없음')
                author = book_info.get('author', '저자 미상')
                
                st.success(f"'{title}'을(를) 찾았습니다.")
                
                # 1. 책 정보 카드
                with st.container(border=True):
                    st.subheader(f"📖 {title}")
                    st.caption(f"저자: {author}")
                    
                    st.markdown(f"**💭 발굴 이유:**\n{book_info.get('reason', '')}")
                    st.markdown(f"---")
                    st.markdown(f"**❝ 결정적 문장:**\n*{book_info.get('quote', '')}*")
                    st.markdown(f"**👤 추천 대상:** {book_info.get('target', '')}")
                
                # 2. 도서관/서점 검색
                st.divider()
                st.subheader("🏛️ 소장 확인")
                
                query = urllib.parse.quote(title)
                
                yuseong_url = f"[https://lib.yuseong.go.kr/web/program/searchResultList.do?searchType=SIMPLE&searchCategory=BOOK&keyword=](https://lib.yuseong.go.kr/web/program/searchResultList.do?searchType=SIMPLE&searchCategory=BOOK&keyword=){query}"
                daejeon_unified_url = f"[https://www.u-library.kr/search/tot/result?st=KWRD&si=TOTAL&q=](https://www.u-library.kr/search/tot/result?st=KWRD&si=TOTAL&q=){query}"
                kyobo_url = f"[https://search.kyobobook.co.kr/search?keyword=](https://search.kyobobook.co.kr/search?keyword=){query}&gbCode=TOT&target=total"

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.link_button("📍 유성구 도서관", yuseong_url)
                with c2:
                    st.link_button("🔍 대전 전체 도서관", daejeon_unified_url)
                with c3:
                    st.link_button("📕 교보문고 정보", kyobo_url)
                
                st.caption("※ 버튼이 작동하지 않으면 아래 제목을 복사하세요.")
                st.code(title, language="text")
                    
            else:
                st.error("AI가 추천을 생성했지만 형식이 불안정했습니다. 다시 한 번만 눌러주세요! 🙏")
    else:
        st.warning("키워드를 입력해야 책을 찾을 수 있습니다.")
