import streamlit as st
import google.generativeai as genai
import json
import urllib.parse
import re  # <--- [핵심] 정밀 데이터 추출 도구 추가

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="심해의 서재", page_icon="🕯️", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 기능 함수 (수정됨)
# ------------------------------------------------------------------
def generate_recommendation(category, keyword):
    prompt = f"""
    당신은 50년 경력의 고집 센 '헌책방 주인'입니다.
    사용자가 '{category}' 분야에서 '{keyword}'와 관련된 책을 찾습니다.
    
    [절대 금지]
    1. 베스트셀러, 누구나 아는 유명한 책 금지.
    2. 자기계발서 금지.
    3. **절판된 책 절대 금지** (현재 구할 수 있어야 함).
    
    [추천 기준]
    - 대중적이지 않지만 깊이가 압도적인 '숨은 명저'.
    
    [필수 출력 형식]
    다른 말 하지 말고 오직 아래 JSON 데이터만 출력해:
    {{
        "title": "책 제목",
        "author": "저자",
        "reason": "추천 이유 (시니컬하고 깊이 있게)",
        "quote": "결정적 문장",
        "target": "추천 대상"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        # [핵심 수정] AI가 잡담을 섞어도 {} 안에 있는 JSON만 강제로 끄집어냄
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
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
                st.success(f"'{book_info['title']}'을(를) 찾았습니다.")
                
                # 1. 책 정보 카드
                with st.container(border=True):
                    st.subheader(f"📖 {book_info['title']}")
                    st.caption(f"저자: {book_info['author']}")
                    
                    st.markdown(f"**💭 발굴 이유:**\n{book_info['reason']}")
                    st.markdown(f"---")
                    st.markdown(f"**❝ 결정적 문장:**\n*{book_info['quote']}*")
                    st.markdown(f"**👤 추천 대상:** {book_info['target']}")
                
                # 2. 도서관/서점 검색
                st.divider()
                st.subheader("🏛️ 소장 확인")
                
                query = urllib.parse.quote(book_info['title'])
                
                # 유성구 통합도서관
                yuseong_url = f"https://lib.yuseong.go.kr/web/program/searchResultList.do?searchType=SIMPLE&searchCategory=BOOK&keyword={query}"
                
                # 대전 통합 검색 (U-Library)
                daejeon_unified_url = f"https://www.u-library.kr/search/tot/result?st=KWRD&si=TOTAL&q={query}"
                
                # 교보문고 (가장 정확)
                kyobo_url = f"https://search.kyobobook.co.kr/search?keyword={query}&gbCode=TOT&target=total"

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.link_button("📍 유성구 도서관", yuseong_url)
                with c2:
                    st.link_button("🔍 대전 전체 도서관", daejeon_unified_url)
                with c3:
                    st.link_button("📕 교보문고 정보", kyobo_url)
                
                st.caption("※ 버튼이 작동하지 않으면 아래 제목을 복사하세요.")
                st.code(book_info['title'], language="text")
                    
            else:
                st.error("AI가 책을 찾다가 졸았나 봅니다. 다시 한 번 버튼을 눌러주세요. 😴")
    else:
        st.warning("키워드를 입력해야 책을 찾을 수 있습니다.")
