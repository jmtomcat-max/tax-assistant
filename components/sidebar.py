# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무 리서치 & AI 검토 - 미니멀 고정형 사이드바 컴포넌트
- 레퍼런스 이미지(Arc 브라우저 사이드바) 1:1 정밀 구현
- 마크다운 파서 코드블록 오작동(인덴트 버그) 원천 차단: 공백 제거 처리
"""
import streamlit as st
import config

NAV_DATA = [
    {
        "group_id": "review",
        "group_title": "검토",
        "has_dropzone": False,
        "items": [
            {
                "id": "new_review",
                "label": "새 검토",
                "icon": "✏️",
                "view": "new_review",
            },
            {
                "id": "review_history",
                "label": "지식 승인센터",
                "icon": "🧠",
                "view": "review_history",
                "show_count": True,
                "count_key": "approval_queue",
            },
            {
                "id": "approval_candidate",
                "label": "승인 대기",
                "icon": "📥",
                "view": "review_history",
                "queue": "candidate",
                "is_child": True,
                "show_count": True,
                "show_zero": True,
                "count_key": "candidate",
            },
            {
                "id": "approval_reviewing",
                "label": "검토 중",
                "icon": "🔎",
                "view": "review_history",
                "queue": "reviewing",
                "is_child": True,
                "show_count": True,
                "show_zero": True,
                "count_key": "reviewing",
            },
            {
                "id": "approval_rejected",
                "label": "반려 보관함",
                "icon": "🗃️",
                "view": "review_history",
                "queue": "rejected",
                "is_child": True,
                "show_count": True,
                "show_zero": True,
                "count_key": "rejected",
            },
        ],
    },
    {
        "group_id": "search",
        "group_title": "검색",
        "has_dropzone": False,
        "items": [
            {
                "id": "manual",
                "label": "내부 매뉴얼",
                "icon": "📖",
                "view": "manual",
            },
        ],
    },
    {
        "group_id": "data",
        "group_title": "자료",
        "has_dropzone": False,
        "items": [
            {
                "id": "vault",
                "label": "승인된 자료",
                "icon": "📚",
                "view": "vault",
                "show_count": True,
                "count_key": "approved",
            },
        ],
    },
    {
        "group_id": "tools",
        "group_title": "도구",
        "has_dropzone": False,
        "items": [
            {
                "id": "penalty",
                "label": "가산세 계산기",
                "icon": "🧮",
                "view": "penalty",
            },
        ],
    },
]


def _navigation_signature(view: str | None, queue: str | None = None) -> tuple[str, str]:
    """Return the URL navigation state that should be applied only once."""
    return (view or "", queue or "")


def render_sidebar():
    """
    레퍼런스 이미지(Arc 사이드바)와 100% 동일한 미니멀 고정형 사이드바를 렌더링합니다.
    """
    # URL 쿼리 파라미터 감지 및 세션 스테이트 동기화
    query_view = st.query_params.get("view", None)
    query_queue = st.query_params.get("queue", None)
    navigation_signature = _navigation_signature(query_view, query_queue)
    if query_view and st.session_state.get("_applied_navigation") != navigation_signature:
        if query_view == "new_review":
            st.session_state["search_input"] = ""
            st.session_state["main_prompt_text"] = ""
            st.session_state["active_view"] = "new_review"
        else:
            st.session_state["active_view"] = query_view
        st.session_state["_applied_navigation"] = navigation_signature

    active_view = st.session_state.get("active_view", "new_review")
    active_queue = (query_queue or "candidate") if active_view == "review_history" else ""
    if active_view == "search":
        active_view = "new_review"
        st.session_state["active_view"] = "new_review"
    try:
        from repositories.review_repo import get_review_repository
        repo = get_review_repository()
        status_counts = repo.get_kpi_stats().get("knowledge_status_counts", {})
        nav_counts = {
            "approval_queue": status_counts.get("candidate", 0) + status_counts.get("reviewing", 0),
            "approved": status_counts.get("approved", 0),
            "candidate": status_counts.get("candidate", 0),
            "reviewing": status_counts.get("reviewing", 0),
            "rejected": status_counts.get("rejected", 0),
        }
    except Exception:
        nav_counts = {"approval_queue": 0, "approved": 0, "candidate": 0, "reviewing": 0, "rejected": 0}

    # HTML 메뉴 항목 구성 (마크다운 파서가 코드블록으로 인식하지 않도록 인덴트 0 보장)
    groups_html_list = []
    for group in NAV_DATA:
        items_html_list = []
        for item in group["items"]:
            is_active = (
                active_view == item["view"]
                and (item.get("queue") == active_queue if item.get("is_child") else not item.get("queue") and active_view != "review_history")
            )
            active_cls = " active" if is_active else ""
            child_cls = " child" if item.get("is_child") else ""
            
            item_count = nav_counts.get(item.get("count_key", ""), 0)
            badge_str = f'<span class="arc-badge">{item_count}</span>' if (item.get("show_count") and (item_count > 0 or item.get("show_zero"))) else ""
            href = f'?view={item["view"]}' + (f'&queue={item["queue"]}' if item.get("queue") else "")

            item_str = (
                f'<a href="{href}" target="_self" class="arc-nav-item{active_cls}{child_cls}">'
                f'<span class="arc-item-icon">{item["icon"]}</span>'
                f'<span class="arc-item-label">{item["label"]}</span>'
                f'{badge_str}'
                f'</a>'
            )
            items_html_list.append(item_str)

        items_inner = "".join(items_html_list)
        group_str = (
            f'<div class="arc-group">'
            f'<div class="arc-group-title">{group["group_title"]}</div>'
            f'{items_inner}'
            f'</div>'
        )
        groups_html_list.append(group_str)

    all_groups_html = "".join(groups_html_list)

    # API 상태 표시
    oc_key = config.get_law_oc()
    dot_oc = '<span style="color:#10B981;">●</span>' if oc_key else '<span style="color:#EF4444;">●</span>'
    # AI 엔진 상태 감지 (ChatGPT Enterprise / OpenAI 우선)
    if config.is_ai_configured():
        dot_ai = '<span style="color:#10B981;">●</span>'
        model_name = config.get_azure_openai_deployment_name() or "GPT-4o"
        ai_name = f"ChatGPT ({model_name})"
    elif config.get_gemini_api_key():
        dot_ai = '<span style="color:#10B981;">●</span>'
        ai_name = "Gemini"
    else:
        dot_ai = '<span style="color:#EF4444;">●</span>'
        ai_name = "AI 미설정"
    settings_active_cls = " active" if active_view == "settings" else ""

    sidebar_html = (
'<style>'
'section[data-testid="stSidebar"] {'
'    background-color: #EBEBEB !important;'
'    background: #EBEBEB !important;'
'    border-right: 1px solid #DCDCDC !important;'
'    width: 220px !important;'
'    min-width: 200px !important;'
'    max-width: 240px !important;'
'}'
'section[data-testid="stSidebar"] > div:first-child {'
'    background-color: #EBEBEB !important;'
'    background: #EBEBEB !important;'
'    width: 220px !important;'
'}'
'section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {'
'    background-color: #EBEBEB !important;'
'    background: #EBEBEB !important;'
'    padding: 8px 6px 12px 6px !important;'
'    overflow-y: auto !important;'
'    overflow-x: hidden !important;'
'}'
'.arc-sidebar-root {'
'    display: flex;'
'    flex-direction: column;'
'    width: 100%;'
'    font-family: -apple-system, BlinkMacSystemFont, "Pretendard Variable", Pretendard, sans-serif;'
'    user-select: none;'
'}'
'.arc-header {'
'    display: flex;'
'    align-items: center;'
'    justify-content: space-between;'
'    padding: 4px 6px 8px 6px;'
'    margin-bottom: 4px;'
'}'
'.arc-header-left {'
'    display: flex;'
'    align-items: center;'
'    gap: 6px;'
'    cursor: default;'
'}'
'.arc-header-avatar {'
'    width: 22px;'
'    height: 22px;'
'    background: #FFFFFF;'
'    border: 1px solid #D0D0D0;'
'    border-radius: 6px;'
'    display: flex;'
'    align-items: center;'
'    justify-content: center;'
'    font-size: 13px;'
'    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);'
'}'
'.arc-header-title {'
'    font-size: 13px;'
'    font-weight: 700;'
'    color: #111111;'
'    letter-spacing: -0.01em;'
'}'
'.arc-header-chevron {'
'    font-size: 9px;'
'    color: #888888;'
'    margin-left: 2px;'
'}'
'.arc-header-right {'
'    display: flex;'
'    align-items: center;'
'    gap: 2px;'
'}'
'.arc-icon-btn {'
'    width: 22px;'
'    height: 22px;'
'    display: flex;'
'    align-items: center;'
'    justify-content: center;'
'    font-size: 11px;'
'    color: #666666;'
'    border-radius: 5px;'
'    cursor: pointer;'
'    transition: background 0.15s ease;'
'}'
'.arc-icon-btn:hover {'
'    background: rgba(0, 0, 0, 0.06);'
'    color: #111111;'
'}'
'.arc-group {'
'    margin-bottom: 8px;'
'}'
'.arc-group-title {'
'    font-size: 11px;'
'    font-weight: 600;'
'    color: #777777;'
'    padding: 6px 8px 3px 8px;'
'    letter-spacing: 0.01em;'
'}'
'.arc-nav-item {'
'    display: flex !important;'
'    align-items: center !important;'
'    height: 32px !important;'
'    padding: 0 9px !important;'
'    margin: 1.5px 2px !important;'
'    border-radius: 8px !important;'
'    text-decoration: none !important;'
'    color: #333333 !important;'
'    font-size: 12.5px !important;'
'    font-weight: 500 !important;'
'    transition: background 0.15s ease, color 0.15s ease !important;'
'    cursor: pointer !important;'
'}'
'.arc-nav-item:hover {'
'    background-color: rgba(0, 0, 0, 0.05) !important;'
'    color: #000000 !important;'
'}'
'.arc-nav-item.child {'
'    height: 27px !important;'
'    margin-left: 18px !important;'
'    padding-left: 8px !important;'
'    font-size: 11.5px !important;'
'}'
'.arc-nav-item.child .arc-item-icon {'
'    font-size: 12px;'
'    margin-right: 6px;'
'}'
'.arc-item-icon {'
'    font-size: 14px;'
'    margin-right: 8px;'
'    width: 16px;'
'    text-align: center;'
'    opacity: 0.85;'
'}'
'.arc-item-label {'
'    flex: 1;'
'    white-space: nowrap;'
'    overflow: hidden;'
'    text-overflow: ellipsis;'
'}'
'.arc-badge {'
'    font-size: 10px;'
'    font-weight: 700;'
'    background-color: #D6D6D6;'
'    color: #444444;'
'    padding: 1px 6px;'
'    border-radius: 10px;'
'    margin-left: 4px;'
'}'
'.arc-nav-item.active {'
'    background-color: #FFFFFF !important;'
'    background: #FFFFFF !important;'
'    border: 1px solid rgba(0, 0, 0, 0.08) !important;'
'    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04) !important;'
'    color: #111111 !important;'
'    font-weight: 600 !important;'
'}'
'.arc-nav-item.active:hover {'
'    background-color: #FFFFFF !important;'
'    border-color: rgba(0, 0, 0, 0.12) !important;'
'}'
'.arc-nav-item.active .arc-item-label {'
'    color: #111111 !important;'
'    font-weight: 600 !important;'
'}'
'.arc-divider {'
'    height: 1px;'
'    background-color: #DCDCDC;'
'    margin: 10px 4px 6px 4px;'
'}'
'.arc-user-card {'
'    display: flex;'
'    align-items: center;'
'    gap: 7px;'
'    padding: 6px 8px;'
'    margin: 4px 2px 2px 2px;'
'    border-radius: 7px;'
'    background: transparent;'
'}'
'.arc-user-avatar {'
'    width: 22px;'
'    height: 22px;'
'    background: #D8D8D8;'
'    color: #333333;'
'    font-size: 10px;'
'    font-weight: 700;'
'    border-radius: 50%;'
'    display: flex;'
'    align-items: center;'
'    justify-content: center;'
'}'
'.arc-user-info {'
'    flex: 1;'
'    overflow: hidden;'
'    line-height: 1.2;'
'}'
'.arc-user-name {'
'    font-size: 11.5px;'
'    font-weight: 600;'
'    color: #222222;'
'    white-space: nowrap;'
'}'
'.arc-user-role {'
'    font-size: 10px;'
'    color: #888888;'
'    white-space: nowrap;'
'}'
'.arc-status-dot {'
'    width: 6px;'
'    height: 6px;'
'    border-radius: 50%;'
'    background: #22C55E;'
'}'
'.arc-infra-footer {'
'    font-size: 10px;'
'    color: #777777;'
'    padding: 3px 8px 8px 8px;'
'    line-height: 1.35;'
'}'
'</style>'
'<div class="arc-sidebar-root">'
'<div class="arc-header">'
'<div class="arc-header-left">'
'<div class="arc-header-avatar">⚖️</div>'
'<div class="arc-header-title">TAX AI <span class="arc-header-chevron">▼</span></div>'
'</div>'
'<div class="arc-header-right">'
'<span class="arc-icon-btn" title="빠른 검색">🔍</span>'
'<span class="arc-icon-btn" title="사이드바">◫</span>'
'</div>'
'</div>'
f'{all_groups_html}'
'<div class="arc-divider"></div>'
'<div class="arc-group" style="margin-bottom: 2px;">'
'<div class="arc-group-title">설정 및 지원</div>'
f'<a href="?view=settings" target="_self" class="arc-nav-item{settings_active_cls}">'
'<span class="arc-item-icon">⚙️</span>'
'<span class="arc-item-label">시스템 설정</span>'
'</a>'
'</div>'
'<div class="arc-user-card">'
'<div class="arc-user-avatar">CJ</div>'
'<div class="arc-user-info">'
f'<div class="arc-user-name">{st.session_state.get("user_name", "경영지원담당 회계팀")}</div>'
f'<div class="arc-user-role">{st.session_state.get("user_id", "admin")} ({"관리자" if st.session_state.get("user_role") == "admin" else "실무자"})</div>'
'</div>'
'<div class="arc-status-dot" title="엔진 정상 작동중"></div>'
'</div>'
'<div class="arc-infra-footer">'
f'<div>{dot_oc} 법령센터 · {dot_ai} {ai_name}</div>'
f'<div style="font-size:9.5px; color:#999999; margin-top:2px;">기준일: {config.get_tax_base_date()} 세법</div>'
'</div>'
'</div>'
    )

    with st.sidebar:
        st.markdown(sidebar_html, unsafe_allow_html=True)
        if config.is_auth_enabled() and st.session_state.get("is_authenticated", False):
            if st.button("🚪 로그아웃", key="sidebar_logout_btn", use_container_width=True, help="현재 계정에서 안전하게 로그아웃합니다."):
                from components.auth import logout_user
                logout_user()
