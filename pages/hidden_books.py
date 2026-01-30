import streamlit as st
import google.generativeai as genai
import json
import urllib.parse

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
    - 베스트셀러, 누구나 아는 유명한 책 금지.
    - 자기계발서 금지.
    
    [추천 기준]
    - 절판되었거나 구하기 힘들어도 깊이가 압도적인 '숨은 명저'.
    - 전문가들만 아는 인생의 책.
    
    [필수 출력 형식]
    반드시 아래 JSON 포맷으로만 답변해. 다른 말 섞지 마.
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
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        return None

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.title("🕯️ 심해의 서재 (Hidden Gems)")
st.caption("베스트셀러는 거부합니다. 유성구 도서관 구석에 있을법한 명저를 찾아드립니다.")

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
                st.success("발견했습니다.")
                
                # 1. 책 정보 카드
                with st.container(border=True):
                    st.subheader(f"📖 {book_info['title']}")
                    st.caption(f"저자: {book_info['author']}")
                    
                    st.markdown(f"**💭 발굴 이유:**\n{book_info['reason']}")
                    st.markdown(f"---")
                    st.markdown(f"**❝ 결정적 문장:**\n*{book_info['quote']}*")
                    st.markdown(f"**👤 추천 대상:** {book_info['target']}")
                
                # 2. 도서관 검색 (수정된 URL)
                st.divider()
                st.subheader("🏛️ 도서관 소장 확인")
                
                # 검색어 인코딩
                query = urllib.parse.quote(book_info['title'])
                
                # [수정 1] 유성구 통합도서관 (정확한 최신 경로)
                # 경로: /web/program/searchResultList.do
                yuseong_url = f"https://lib.yuseong.go.kr/web/program/searchResultList.do?searchType=SIMPLE&searchCategory=BOOK&keyword={query}"
                
                # [수정 2] 한밭도서관 (대전 대표, 유성구와 같은 시스템 사용 확률 높음)
                # 대전 통합검색이 불안정하여 한밭도서관으로 변경
                hanbat_url = f"https://www.hanbatlibrary.kr/web/program/searchResultList.do?searchType=SIMPLE&searchCategory=BOOK&keyword={query}"
                
                c1, c2 = st.columns(2)
                with c1:
                    st.link_button(
                        label="📍 유성구 도서관 검색 (노은/유성/진잠)", 
                        url=yuseong_url, 
                        help="클릭하면 바로 검색 결과가 뜹니다."
                    )
                with c2:
                    st.link_button(
                        label="🔍 한밭도서관 검색 (대전 전체)", 
                        url=hanbat_url,
                        help="유성에 없다면 대전 대표 도서관을 찾아봅니다."
                    )
                
                # 3. 혹시 몰라 제목 복사 기능 제공
                st.caption("※ 만약 버튼으로 검색이 안 되면, 아래 제목을 복사해서 이용하세요.")
                st.code(book_info['title'], language="text")
                    
            else:
                st.error("AI가 책을 찾다가 길을 잃었습니다. 다시 시도해주세요.")
    else:
        st.warning("키워드를 입력해야 책을 찾을 수 있습니다.")
