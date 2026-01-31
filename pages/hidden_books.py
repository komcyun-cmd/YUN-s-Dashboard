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
                title = book_info.get('title', '제목 없음')
                author = book_info.get('author', '저자 미상')
                
                st.success(f"'{title}'을(를) 찾았습니다.")
                
                # 1. 책 정보 카드
                with st.container(border=True):
                    st.subheader(f"📖 {title}")
                    st.caption(f"저자: {author}")
                    st.markdown(f"**💭 발굴 이유:** {book_info.get('reason', '')}")
                    st.markdown(f"**❝ 결정적 문장:** *{book_info.get('quote', '')}*")
                
                # 2. 통합 검색 및 바로가기
                st.divider()
                st.subheader("🏛️ 소장 확인")
                st.caption("아래 버튼을 눌러 사이트로 이동한 뒤, 복사한 제목을 붙여넣으세요.")

                # 검색어 인코딩 (공백 처리에 강한 quote_plus 사용)
                query = urllib.parse.quote_plus(title)
                
                # [수정] 가장 확실한 메인 페이지 URL + 네이버 책
                naver_book_url = f"[https://search.naver.com/search.naver?where=book&query=](https://search.naver.com/search.naver?where=book&query=){query}"
                yuseong_home = "[https://lib.yuseong.go.kr/](https://lib.yuseong.go.kr/)"
                u_library_home = "[https://www.u-library.kr/](https://www.u-library.kr/)"
                kyobo_home = f"[https://search.kyobobook.co.kr/search?keyword=](https://search.kyobobook.co.kr/search?keyword=){query}" # 교보는 이게 표준이라 유지하되 인코딩 강화

                # 버튼 배치
                c1, c2, c3, c4 = st.columns(4)
                
                with c1:
                    # 네이버는 링크가 깨질 일이 거의 없음
                    st.link_button("📗 네이버 책", naver_book_url, help="책 상세 정보와 판매처를 확인합니다.")
                with c2:
                    st.link_button("📕 교보문고", kyobo_home, help="교보문고 검색 결과로 이동합니다.")
                with c3:
                    st.link_button("🏛️ 유성구 도서관", yuseong_home, help="유성구 통합도서관 메인으로 이동합니다.")
                with c4:
                    st.link_button("🏛️ 대전 사이버", u_library_home, help="대전 전체 도서관 검색 메인으로 이동합니다.")

                # 제목 복사 편의성 제공
                st.info("👇 아래 제목을 복사해서 도서관 검색창에 붙여넣으세요!")
                st.code(title, language="text")
                    
            else:
                st.warning("AI가 잠시 길을 잃었습니다. 다시 한 번 버튼을 눌러주세요.")
    else:
        st.warning("키워드를 입력해야 책을 찾을 수 있습니다.")
