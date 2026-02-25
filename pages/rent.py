import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import re
import ast

# ------------------------------------------------------------------
# [1] 설정
# ------------------------------------------------------------------
st.set_page_config(page_title="병원 관리비 매니저", page_icon="🏢", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel('gemini-flash-latest')

# ------------------------------------------------------------------
# [2] 영수증 AI 분석 함수 (강력한 파싱 적용)
# ------------------------------------------------------------------
def analyze_receipt(image):
    prompt = """
    당신은 깐깐하고 정확한 '병원 관리비 영수증 분석 AI'입니다.
    업로드된 고지서/영수증 이미지를 분석하여 아래 파이썬 딕셔너리(JSON) 형식으로만 응답하세요.
    인사말, 설명, 부연 설명은 절대 금지합니다. 오직 데이터만 출력하세요.

    {
        "month": "청구월 (예: 2026-02)",
        "total_amount": 총 청구 금액 (숫자만, 예: 1500000),
        "electricity": 전기 요금 (숫자만, 없으면 0),
        "water": 수도 요금 (숫자만, 없으면 0),
        "memo": "납부기한이나 기타 특이사항 (짧게)"
    }
    """
    try:
        # 이미지와 프롬프트를 함께 전송 (Vision 기능)
        response = model.generate_content([prompt, image])
        text = response.text
        
        # [핵심] 마크다운 및 잡담 제거 후 데이터만 강제 추출
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
        return f"error: {e}"

# ------------------------------------------------------------------
# [3] 화면 구성
# ------------------------------------------------------------------
st.title("🏢 병원 관리비 매니저")
st.caption("고지서를 스마트폰으로 찍어 올리시면, AI가 내역을 자동 정리합니다.")
st.divider()

# 파일 업로더
uploaded_file = st.file_uploader("관리비 고지서/영수증 사진 업로드", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # 이미지 화면에 보여주기
    image = Image.open(uploaded_file)
    st.image(image, caption="업로드된 고지서", use_container_width=True)
    
    if st.button("스캔 및 내역 추출 시작 🔍", type="primary"):
        with st.spinner("AI가 고지서의 숫자들을 읽어내고 있습니다..."):
            result = analyze_receipt(image)
            
            if isinstance(result, dict):
                st.success("스캔 완료!")
                
                # 추출된 데이터 카드 형태로 예쁘게 보여주기
                with st.container(border=True):
                    st.subheader(f"📅 {result.get('month', '알 수 없음')} 청구 내역")
                    
                    # 3열로 나누어서 숫자 강조
                    c1, c2, c3 = st.columns(3)
                    
                    # 숫자에 천 단위 콤마(,) 찍기
                    total = result.get('total_amount', 0)
                    elec = result.get('electricity', 0)
                    water = result.get('water', 0)
                    
                    c1.metric("총 청구 금액", f"{total:,}원" if isinstance(total, int) else f"{total}원")
                    c2.metric("전기 요금", f"{elec:,}원" if isinstance(elec, int) else f"{elec}원")
                    c3.metric("수도 요금", f"{water:,}원" if isinstance(water, int) else f"{water}원")
                    
                    st.divider()
                    st.markdown(f"**📌 특이사항:** {result.get('memo', '없음')}")
                    
            elif result is None:
                st.error("AI가 사진에서 데이터를 추출하지 못했습니다. 글자가 잘 보이게 다시 찍어주세요.")
            else:
                st.error(f"오류 발생: {result}")
