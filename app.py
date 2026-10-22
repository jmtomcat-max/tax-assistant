# -*- coding: utf-8 -*-
"""
CJ프레시웨이(CJ Freshway) 세무·조세 판례 실시간 검색 및 ChatGPT Enterprise(Azure OpenAI / GPT-4o) 분석 비서
- CJ CI/BI 컬러 팔레트 완벽 적용: CJ 딥 블루 (#003876) & CJ 시그니처 레드 (#E61E2B)
- 네이버 클로바 일체형 검색 + 노션 콜아웃 리포트
- 칼각 수평 버튼 정렬 + 마크다운 기호(**) 자동 변환
"""
import streamlit as st
import config
from storage import load_saved_cases
from views.view_settings import render_settings_view
from views.view_manual import render_manual_view
from views.view_penalty import render_penalty_view
from views.view_approved_knowledge import render_approved_knowledge_view
from views.view_search import render_search_view
from components.ui_elements import apply_custom_css


st.set_page_config(
    page_title="CJ프레시웨이 세무 리서치 & AI 검토",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)



# ----------------- 관심 판례 및 AI 리포트 보관함 영구 저장 관리 -----------------
# load_saved_cases 및 save_saved_cases는 storage 모듈(원자적 파일 쓰기 & 데이터 살균)에서 제공됩니다.


# ----------------- CJ프레시웨이 테마 커스텀 CSS -----------------
apply_custom_css()

# ----------------- 보안 로그인 인증 게이트키퍼 -----------------
from components.auth import check_authentication
if not check_authentication():
    st.stop()

# ----------------- 세션 스테이트 초기화 -----------------
if "search_input" not in st.session_state:
    st.session_state["search_input"] = ""
if "main_prompt_text" not in st.session_state:
    st.session_state["main_prompt_text"] = ""
if "selected_tax_type" not in st.session_state:
    st.session_state["selected_tax_type"] = "전체"
if "selected_category" not in st.session_state:
    st.session_state["selected_category"] = "전체"
if "result_limit" not in st.session_state:
    st.session_state["result_limit"] = 15
if "saved_cases" not in st.session_state:
    st.session_state["saved_cases"] = load_saved_cases()
if "active_view" not in st.session_state or st.session_state.get("active_view") == "search":
    st.session_state["active_view"] = "new_review"

import importlib
import components.sidebar
importlib.reload(components.sidebar)
from components.sidebar import render_sidebar

# ----------------- 사이드바 렌더링 (미니멀 고정형 네비게이션) -----------------
render_sidebar()

category_choice = st.session_state.get("selected_category", "전체")
result_limit = st.session_state.get("result_limit", 15)
cur_view = st.session_state.get("active_view", "new_review")

# 화면 라우팅
if cur_view == "review_history":
    # ⏱️ 세무 검토 기록(Review History) 전용 아카이브 & 지식 DB
    import importlib
    import views.view_history
    importlib.reload(views.view_history)
    from views.view_history import render_history_view
    render_history_view()

elif cur_view == "vault":
    # 📚 회계팀 승인 지식만 표시
    render_approved_knowledge_view()

elif cur_view == "manual":
    # 사내 세무 매뉴얼 & 계정과목 사전
    render_manual_view()

elif cur_view == "penalty":
    # 부가가치세 가산세 계산기
    render_penalty_view()

elif cur_view == "settings":
    # 시스템 설정 및 기준세율 관리
    render_settings_view()

else:
    # 기본값: 판례 검색 및 AI 검토 (Search View)
    render_search_view()

