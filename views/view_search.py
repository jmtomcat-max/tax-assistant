# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무·조세 판례 실시간 검색 및 AI 분석 뷰 (Search View)
"""
import io
import logging
import re
import hashlib
import time
import pandas as pd
import streamlit as st

import config
from config import STOP_KEYWORDS
from storage import save_saved_cases, check_duplicate_case
from summarizer import (
    generate_followup_answer,
    format_report_summary,
    format_report_opinion,
    format_report_detailed,
)
from services.analysis_pipeline import (
    analyze_question,
    create_briefing,
    load_internal_knowledge,
    search_official_sources,
)
from components.ui_elements import (
    format_notion_content,
    render_copy_button,
    render_case_comparison_table,
    render_case_card,
)

logger = logging.getLogger(__name__)


def _format_pipeline_timings(timings: dict) -> str:
    return " · ".join(
        f"{stage} {'캐시' if seconds is None else f'{seconds:.1f}초'}"
        for stage, seconds in timings.items()
    )


def _safe_relevance_score(val) -> int:
    """판례의 relevance_score가 str, None, int 등 어떤 타입이든 안전하게 int로 변환"""
    if isinstance(val, dict):
        val = val.get("relevance_score", 0)
    try:
        if val is None or val == "" or str(val).strip() == "":
            return 0
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def generate_case_patterns(c_item: dict, c_idx: int) -> list:
    """판례/예규 객체에서 본문 텍스트에 나타날 수 있는 모든 표기 변형 패턴을 생성"""
    c_no = (c_item.get("case_number") or "").strip()
    c_court = (c_item.get("court") or "").strip()
    clean_no = re.sub(r'^(국세법령정보시스템|국가법령정보센터)\s*', '', c_no).strip()
    
    patterns = set()
    if c_no:
        patterns.add(c_no)
        patterns.add(f"({c_no})")
        patterns.add(f"[{c_no}]")
        patterns.add(f"판례({c_no})")
        patterns.add(f"판례 {c_no}")
        patterns.add(f"결정례({c_no})")
        patterns.add(f"예규({c_no})")
    
    if clean_no:
        patterns.add(clean_no)
        patterns.add(f"({clean_no})")
        patterns.add(f"[{clean_no}]")
        patterns.add(f"판례({clean_no})")
        patterns.add(f"판례 {clean_no}")
        
    no_hyphens = clean_no.replace("-", "").strip()
    if len(no_hyphens) >= 4:
        patterns.add(no_hyphens)
        patterns.add(f"({no_hyphens})")
        patterns.add(f"[{no_hyphens}]")
        patterns.add(f"판례({no_hyphens})")
        patterns.add(f"판례 {no_hyphens}")
        
    with_spaces = clean_no.replace("-", " ").strip()
    if len(with_spaces) >= 4:
        patterns.add(with_spaces)
        patterns.add(f"({with_spaces})")
        patterns.add(f"[{with_spaces}]")
        
    if c_court:
        for num in [c_no, clean_no, no_hyphens, with_spaces]:
            if num:
                patterns.add(f"{c_court} {num}")
                patterns.add(f"{c_court}-{num}")
                patterns.add(f"{c_court}{num}")
                patterns.add(f"({c_court} {num})")
                patterns.add(f"[{c_court} {num}]")
                patterns.add(f"({c_court}-{num})")
                patterns.add(f"[{c_court}-{num}]")
                patterns.add(f"판례({c_court} {num})")
                patterns.add(f"판례({c_court}-{num})")
                
    m = re.search(r'(\d{4}[- ]?[가-힣]{1,4}[- ]?\d+)', clean_no)
    if m:
        core_num = m.group(1)
        patterns.add(core_num)
        patterns.add(core_num.replace("-", "").replace(" ", ""))
        patterns.add(f"({core_num})")
        patterns.add(f"[{core_num}]")
        patterns.add(f"판례({core_num})")
        patterns.add(f"판례 {core_num}")
        if c_court:
            patterns.add(f"{c_court} {core_num}")
            patterns.add(f"({c_court} {core_num})")
            
    patterns.add(f"[INDEX_{c_idx}]")
    patterns.add(f"INDEX_{c_idx}")
    patterns.add(f"【INDEX_{c_idx}】")
    patterns.add(f"[근거 #{c_idx+1}]")
    patterns.add(f"[근거 {c_idx+1}]")
    patterns.add(f"근거 #{c_idx+1}")
    patterns.add(f"근거 {c_idx+1}")
    
    pat_list = [p for p in patterns if p and len(p) >= 3]
    pat_list.sort(key=len, reverse=True)
    return pat_list


def render_direct_basis_badges(cited_cases: list, title: str = "📌 본 결론 직접 인용 근거") -> str:
    """의견서 요약 카드 하단에 인용된 모든 핵심 판례·예규의 원클릭 딥링크 뱃지 바 생성"""
    if not cited_cases:
        return ""
    badges = []
    for c_idx, c in enumerate(cited_cases):
        c_no = (c.get("case_number") or "").strip()
        c_slug = re.sub(r'\s+', '_', c_no) if c_no else f"case_{c_idx}"
        c_court = (c.get("court") or "").strip()
        clean_no = re.sub(r'^(국세법령정보시스템|국가법령정보센터)\s*', '', c_no).strip()
        display_label = f"{c_court} {clean_no}" if c_court and c_court not in clean_no else clean_no
        badges.append(
            f'<a href="#case-{c_slug}" target="_self" '
            f'onclick="const el = document.getElementById(\'case-{c_slug}\') || document.getElementById(\'case-anchor-{c_idx}\'); '
            f'if(el){{el.scrollIntoView({{behavior:\'smooth\'}}); el.style.backgroundColor=\'#FEF08A\'; setTimeout(()=>el.style.backgroundColor=\'\', 1500);}} return false;" '
            f'style="background:#FEF08A; color:#854D0E; font-size:0.84rem; font-weight:700; '
            f'padding:3px 10px; border-radius:12px; text-decoration:none; margin:2px 4px; '
            f'border:1px solid #FDE047; box-shadow:0 1px 3px rgba(0,0,0,0.06); '
            f'transition:all 0.2s; display:inline-flex; align-items:center; gap:4px; cursor:pointer;">'
            f'🔍 [근거 #{c_idx+1}] {display_label} ⬇</a>'
        )
    return (
        f'<div style="margin-top:14px; padding-top:10px; border-top:1px dashed #CBD5E1; display:flex; align-items:center; flex-wrap:wrap; gap:6px;">'
        f'<span style="font-size:0.82rem; font-weight:700; color:#005B45;">{title} ({len(cited_cases)}건):</span>'
        f'{"".join(badges)}'
        f'</div>'
    )


def inject_case_deeplinks(text: str, cited_cases: list) -> str:
    """
    [인터랙티브 딥링크 완전 연동]
    AI 결론/의견서 텍스트 내에 존재하는 판례 사건번호 및 모든 변형 표기를
    하단에 항상 펼쳐진 독립 판례 카드로 즉시 스크롤 이동하는 인라인 뱃지(Badge)로 완벽 치환합니다.
    """
    if not text or not cited_cases:
        return text or ""

    placeholders = {}
    for c_idx, c in enumerate(cited_cases):
        c_no = (c.get("case_number") or "").strip()
        if not c_no or len(c_no) < 3:
            continue
        c_slug = re.sub(r'\s+', '_', c_no)
        c_court = (c.get("court") or "").strip()
        clean_no = re.sub(r'^(국세법령정보시스템|국가법령정보센터)\s*', '', c_no).strip()
        display_label = f"{c_court} {clean_no}" if c_court and c_court not in clean_no else clean_no

        badge_html = (
            f'<a href="#case-{c_slug}" target="_self" '
            f'onclick="const el = document.getElementById(\'case-{c_slug}\') || document.getElementById(\'case-anchor-{c_idx}\'); '
            f'if(el){{el.scrollIntoView({{behavior:\'smooth\'}}); el.style.backgroundColor=\'#FEF08A\'; setTimeout(()=>el.style.backgroundColor=\'\', 1500);}} return false;" '
            f'style="background:#FEF08A; color:#854D0E; font-size:0.85rem; font-weight:700; '
            f'padding:2px 8px; border-radius:12px; text-decoration:none; margin:0 2px; '
            f'border:1px solid #FDE047; box-shadow: 0 1px 2px rgba(0,0,0,0.05); '
            f'transition: all 0.2s; display:inline-flex; align-items:center; gap:2px; vertical-align:middle; cursor:pointer;">'
            f'🔍 {display_label} ⬇</a>'
        )

        ph = f"__DEEPLINK_BADGE_{c_idx}__"
        placeholders[ph] = badge_html

        patterns_to_try = generate_case_patterns(c, c_idx)
        for pat in patterns_to_try:
            if pat in text:
                text = text.replace(pat, ph)

    # 플레이스홀더를 HTML 뱃지로 일괄 치환
    for ph, html in placeholders.items():
        text = text.replace(ph, html)

    return text


def build_briefing_clipboard_text(user_query: str, intent_info: dict, briefing_res: dict) -> str:
    """자연어 상황 진단 AI 종합 브리핑 클립보드 텍스트 생성"""
    cat = intent_info.get("tax_category", "조세일반")
    issue = intent_info.get("core_issue", "")
    conclusion = briefing_res.get("conclusion", "").strip()
    case_comp = briefing_res.get("case_comparison", "").strip()
    checklist = briefing_res.get("checklist", "").strip()

    text = f"""[CJ프레시웨이] AI 세무 실무 상황 진단 및 판례 솔루션 리포트
■ 사용자 질문 및 사실관계
{user_query}

■ AI 쟁점 분석
- 분류 세목: [{cat}]
- 핵심 쟁점: {issue}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 세무 리스크 진단 및 핵심 결론
{conclusion}

2. 관련 실제 판례와의 비교 및 법원 판단 취지
{case_comp}

3. 실무자를 위한 필수 증빙 체크리스트 & 행동 수칙
{checklist}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
* 생성 일시: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
* 출처: CJ프레시웨이 TAX AI 비서 (국가법령정보센터 DB & ChatGPT Enterprise 분석)
"""
    return text.strip()


def render_search_debug_panel(search_res: dict, intent_data: dict, active_keywords: list):
    """검색 품질을 진단하기 위한 내부 검색 과정 디버그 패널."""
    search_res = search_res or {}
    intent_data = intent_data or {}
    active_keywords = active_keywords or []
    items = search_res.get("items", []) or []

    debug = search_res.get("debug") or {}

    direct_cnt = debug.get("direct_basis_count", len([r for r in items if r.get("basis_bucket") == "direct_basis" or r.get("basis_type") == "직접근거 후보"]))
    support_cnt = debug.get("support_basis_count", len([r for r in items if r.get("basis_bucket") in ("similar_basis", "evidence_basis") or "보조" in str(r.get("basis_type", ""))]))
    ref_cnt = debug.get("reference_basis_count", len([r for r in items if r.get("basis_bucket") == "weak_reference" or "참고" in str(r.get("basis_type", ""))]))
    deduped_cnt = debug.get("deduped_count", len(items))
    query_logs = debug.get("query_logs", []) or []
    top_results = debug.get("top_results", []) or []

    if not top_results and items:
        top_results = [
            {
                "case_number": it.get("case_number", ""),
                "title": it.get("title", ""),
                "search_path": it.get("search_path", "직접 검색 결과"),
                "basis_type": it.get("basis_type", it.get("basis_bucket_name", "")),
                "relevance_score": it.get("relevance_score", 0),
                "match_reason": it.get("match_reason", ""),
                "matched_keywords": it.get("matched_keywords", [])
            }
            for it in items[:6]
        ]

    with st.expander("🧪 검색 디버그 패널: 왜 이 결과가 나왔는지 확인 (품질 진단)", expanded=False):
        st.markdown("""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-left:4px solid #003876; border-radius:8px; padding:10px 14px; margin-bottom:10px;">
            <div style="font-size:0.88rem; font-weight:800; color:#003876;">검색 품질 진단용 패널</div>
            <div style="font-size:0.80rem; color:#475569; line-height:1.5; margin-top:3px;">
                AI가 뽑은 쟁점어, 실제 API 검색어, 검색원별 건수, 직접근거 부재 사유를 확인합니다.
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("직접근거 후보", f"{direct_cnt}건")
        c2.metric("보조근거 후보", f"{support_cnt}건")
        c3.metric("참고자료", f"{ref_cnt}건")
        c4.metric("검색 결과 수", f"{deduped_cnt}건")

        no_direct_reason = debug.get("no_direct_basis_reason")
        if direct_cnt == 0 and not no_direct_reason:
            no_direct_reason = "거래대상(primary_topics)과 세무쟁점(tax_issues)이 동시에 매칭된 공식자료가 부족하여 보조/유사근거 중심으로 제공되었습니다."
        if no_direct_reason:
            st.warning(no_direct_reason)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**AI 추출 정보 및 쟁점**")
            st.json({
                "세목": intent_data.get("tax_category", debug.get("target_tax", "조세일반")),
                "핵심쟁점": intent_data.get("core_issue", ""),
                "거래대상/목적물": debug.get("primary_topics", []),
                "세무쟁점어": debug.get("tax_issues", []),
                "실제 활성 키워드": active_keywords,
                "제외 토큰": debug.get("excluded_tokens", [])
            })

        with col_b:
            st.markdown("**5대 검색전략 (Search Strategy)**")
            strat = intent_data.get("search_strategy", {}) or debug.get("search_strategy", {})
            st.json({
                "1.직접근거 쿼리": strat.get("direct_queries", []),
                "2.과세관청 리스크 쿼리": strat.get("risk_queries", []),
                "3.증빙/입증 쿼리": strat.get("evidence_queries", []),
                "4.반대/기각 쿼리": strat.get("opposite_queries", []),
                "5.대체/기본 쿼리": strat.get("fallback_queries", []),
                "제외단어": strat.get("exclude_terms", [])
            })

        if query_logs:
            st.markdown("**검색어별 결과 수**")
            q_df = pd.DataFrame(query_logs)
            rename_map = {
                "query": "검색어",
                "route_name": "검색경로",
                "prec_count": "판례",
                "decc_count": "조세심판",
                "expc_count": "예규/해석례",
                "total_count": "합계",
                "status": "상태"
            }
            # route 컬럼 제거 또는 숨김 처리 후 이름 변경
            if "route" in q_df.columns and "route_name" in q_df.columns:
                q_df = q_df.drop(columns=["route"])
            q_df = q_df.rename(columns=rename_map)
            st.dataframe(q_df, use_container_width=True, hide_index=True)

        api_errors = search_res.get("api_errors") or []
        if api_errors:
            st.markdown("**⚠️ 수집된 API 호출 오류/경고 내역**")
            err_df = pd.DataFrame([
                {
                    "오류분류": e.get("category", e.get("error_type", "")),
                    "호출대상": e.get("target", ""),
                    "검색어": e.get("query", ""),
                    "오류메시지": e.get("message", "")
                }
                for e in api_errors
            ])
            st.dataframe(err_df, use_container_width=True, hide_index=True)

        if top_results:
            st.markdown("**상위 결과 판단 근거**")
            top_df = pd.DataFrame(top_results)
            if not top_df.empty:
                top_df = top_df.rename(columns={
                    "case_number": "사건번호",
                    "title": "제목",
                    "search_path": "검색경로",
                    "basis_type": "근거유형",
                    "relevance_score": "관련도",
                    "match_reason": "매칭사유",
                    "matched_keywords": "매칭키워드"
                })
                # 필요 없는 내부 컬럼 정리
                cols_to_drop = [c for c in ["basis_bucket", "basis_bucket_name"] if c in top_df.columns]
                if cols_to_drop:
                    top_df = top_df.drop(columns=cols_to_drop)
                st.dataframe(top_df, use_container_width=True, hide_index=True)

def render_contract_risk_review(intent_data: dict, current_query: str):
    """
    [4단계: 분석 결과 대시보드] AI 계약서·문서 세무 독소조항 진단 및 권고 수정 가이드 렌더링
    """
    risk_clauses = intent_data.get("risk_clauses", [])
    overall_assessment = intent_data.get("overall_assessment", "")
    overall_risk = intent_data.get("overall_risk_level", "")

    if not risk_clauses and not overall_assessment:
        return

    # 리스크 뱃지 스타일링
    if "고위험" in overall_risk:
        badge_bg = "#FEF2F2"
        badge_color = "#DC2626"
        badge_border = "#FCA5A5"
        risk_emoji = "🔴"
    elif "저위험" in overall_risk or "안전" in overall_risk:
        badge_bg = "#F0FDF4"
        badge_color = "#16A34A"
        badge_border = "#86EFAC"
        risk_emoji = "🟢"
    else:
        badge_bg = "#FFFBEB"
        badge_color = "#D97706"
        badge_border = "#FCD34D"
        risk_emoji = "🟡"

    st.markdown(f"""
    <div style="background:#FFFFFF; border:1.5px solid #CBD5E1; border-radius:12px; padding:20px 22px; margin-bottom:18px; box-shadow:0 4px 12px rgba(0,0,0,0.04);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px; border-bottom:1px solid #E2E8F0; padding-bottom:12px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:1.3rem;">🚨</span>
                <span style="font-size:1.1rem; font-weight:800; color:#0F172A;">AI 계약서·문서 세무 독소조항 정밀 진단</span>
                <span style="font-size:0.78rem; background:#EFF8FF; color:#003876; border:1px solid #B2DDFF; padding:2px 8px; border-radius:4px; font-weight:700;">세무 리스크 스캐너</span>
            </div>
            <div style="display:inline-flex; align-items:center; gap:6px; background:{badge_bg}; color:{badge_color}; border:1px solid {badge_border}; padding:4px 12px; border-radius:20px; font-size:0.85rem; font-weight:800;">
                <span>{risk_emoji} 종합 위험도: {overall_risk if overall_risk else '유의 필요'}</span>
            </div>
        </div>
        <div style="background:#F8FAFC; border-left:4px solid #003876; border-radius:6px; padding:12px 16px; margin-bottom:8px;">
            <div style="font-size:0.86rem; font-weight:700; color:#003876; margin-bottom:4px;">📋 계약서 전반 종합 진단 및 실무 영향 평가</div>
            <div style="font-size:0.88rem; color:#334155; line-height:1.65;">
                {format_notion_content(overall_assessment) if overall_assessment else '문서 전반에 걸친 세무 리스크 분석 결과를 표시합니다.'}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if risk_clauses:
        st.markdown(f"<div style='font-size:0.96rem; font-weight:800; color:#005B45; margin-bottom:10px;'>📑 조항별 세무 리스크 진단 및 원문 vs 권고 수정안 (Before & After) — 총 {len(risk_clauses)}건 발견</div>", unsafe_allow_html=True)

        for idx, clause in enumerate(risk_clauses):
            c_art = clause.get("article_no", f"위험 조항 #{idx+1}")
            c_quoted = clause.get("quoted_text", "").strip()
            c_tax = clause.get("tax_type", "세법 일반")
            c_level = clause.get("risk_level", "유의")
            c_reason = clause.get("tax_risk_reason", "").strip()
            c_amend = clause.get("recommended_amendment", "").strip()
            c_rationale = clause.get("amendment_rationale", "").strip()

            c_risk_bg = "#FEF2F2" if "고" in c_level else ("#FFFBEB" if "중" in c_level or "유의" in c_level else "#F0FDF4")
            c_risk_color = "#DC2626" if "고" in c_level else ("#D97706" if "중" in c_level or "유의" in c_level else "#16A34A")
            c_risk_border = "#FCA5A5" if "고" in c_level else ("#FCD34D" if "중" in c_level or "유의" in c_level else "#86EFAC")

            with st.expander(f"⚠️ [{c_level}] {c_art} — {c_tax}", expanded=(idx < 2)):
                # 상단 헤더 영역
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px dashed #CBD5E1; padding-bottom:8px;">
                    <div style="font-size:0.95rem; font-weight:800; color:#0F172A;">
                        📌 <span style="color:#003876;">{c_art}</span>
                    </div>
                    <div style="display:flex; gap:6px;">
                        <span style="font-size:0.75rem; background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; padding:2px 8px; border-radius:4px; font-weight:700;">{c_tax}</span>
                        <span style="font-size:0.75rem; background:{c_risk_bg}; color:{c_risk_color}; border:1px solid {c_risk_border}; padding:2px 8px; border-radius:4px; font-weight:800;">{c_level}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_before, col_after = st.columns([1, 1], gap="medium")

                with col_before:
                    st.markdown(f"""
                    <div style="background:#FFF5F5; border:1.5px solid #FED7D7; border-radius:8px; padding:14px; min-height:100%;">
                        <div style="font-size:0.84rem; font-weight:800; color:#C53030; margin-bottom:8px; display:flex; align-items:center; gap:5px;">
                            <span>❌ [현행 원문] 위험 조항</span>
                        </div>
                        <div style="font-size:0.85rem; color:#2D3748; line-height:1.6; background:#FFFFFF; border:1px dashed #FEB2B2; border-radius:6px; padding:10px 12px; font-family:monospace; margin-bottom:10px;">
                            {c_quoted if c_quoted else '(원문 조항 없음)'}
                        </div>
                        <div style="font-size:0.80rem; font-weight:700; color:#9B2C2C; margin-bottom:3px;">🚨 세무 리스크 및 과세 원인:</div>
                        <div style="font-size:0.82rem; color:#4A5568; line-height:1.55;">
                            {format_notion_content(c_reason)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_after:
                    st.markdown(f"""
                    <div style="background:#F0FDF4; border:1.5px solid #BBF7D0; border-radius:8px; padding:14px; min-height:100%;">
                        <div style="font-size:0.84rem; font-weight:800; color:#15803D; margin-bottom:8px; display:flex; align-items:center; gap:5px;">
                            <span>✅ [AI 권고] 수정 조항 (Re-draft)</span>
                        </div>
                        <div style="font-size:0.85rem; color:#14532D; line-height:1.6; background:#FFFFFF; border:1px solid #86EFAC; border-radius:6px; padding:10px 12px; font-family:monospace; margin-bottom:10px;">
                            {c_amend if c_amend else '(권고 수정안 없음)'}
                        </div>
                        <div style="font-size:0.80rem; font-weight:700; color:#166534; margin-bottom:3px;">🛡️ 수정 취지 및 방어 논리:</div>
                        <div style="font-size:0.82rem; color:#374151; line-height:1.55; margin-bottom:8px;">
                            {format_notion_content(c_rationale)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if c_amend:
                        render_copy_button(c_amend, f"cp_amend_{idx}_{abs(hash(current_query))}")

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)


def compute_files_fingerprint(files_data_list: list) -> str:
    """
    업로드된 문서 목록에 대해 '파일명 + 파일 크기 + 파일 내용 해시(MD5)'를 결합하여
    같은 이름의 파일이라도 내용이나 크기가 변경되었을 때 즉시 캐시가 무효화되도록 고유 지문(Fingerprint)을 생성합니다.
    (형식: {파일명}_{파일크기}_{MD5해시})
    """
    if not files_data_list:
        return "no_files"
    tokens = []
    for f in files_data_list:
        if not isinstance(f, dict):
            continue
        fname = str(f.get("name", "unknown")).strip()
        fbytes = f.get("bytes", b"")
        if isinstance(fbytes, str):
            fbytes = fbytes.encode("utf-8", errors="ignore")
        elif not isinstance(fbytes, (bytes, bytearray)):
            fbytes = bytes(fbytes) if fbytes else b""

        fsize = len(fbytes)
        content_hash = hashlib.md5(fbytes).hexdigest()[:16]
        tokens.append(f"{fname}_{fsize}_{content_hash}")
    return "_".join(tokens) if tokens else "no_files"


def _build_briefing_cache_key(
    current_query: str,
    current_tax_type: str,
    category_choice: str,
    active_keywords: list,
    results_count: int,
    current_focus: str = "종합 검토",
    files_hash_str: str = "no_files",
) -> str:
    """
    사용자가 검색 키워드, 세목, 카테고리, 관점, 문서 업로드 내용을 변경할 때
    결과 개수가 동일하더라도 이전 AI 브리핑 보고서가 재사용되는 문제를 방지하는 지능형 복합 캐시 키.
    """
    kw_hash_str = "_".join(sorted(active_keywords)) if active_keywords else ""
    return (
        f"briefing_v9_{hash(current_query)}_"
        f"{current_tax_type}_{category_choice}_"
        f"{hash(kw_hash_str)}_"
        f"{results_count}_"
        f"{current_focus}_{hash(files_hash_str)}"
    )


def _build_analysis_snapshot_key(
    query: str, tax_type: str, files_hash: str, focus: str, category: str, selected_keywords: list
) -> str:
    context = "\x1f".join([tax_type, files_hash, focus, category, *sorted(selected_keywords or [])])
    return f"analysis_snapshot_v1_{hash(query)}_{hash(context)}"


def _load_or_run_analysis(current_query: str, current_tax_type: str, files_data_list: list) -> dict:
    """
    AI 쟁점분석(intent) -> 판례 검색(search) -> AI 브리핑(briefing) 파이프라인을
    session_state 캐시에서 로드하거나, 캐시가 없으면 새로 실행합니다.
    """
    pipeline_started = time.perf_counter()
    timings = {}
    save_error = None
    save_rec_id = None
    files_hash_str = compute_files_fingerprint(files_data_list)
    current_focus = st.session_state.get("current_focus", "종합 검토")
    category_choice = st.session_state.get("selected_category", "전체")
    current_kw_ver = st.session_state.get(f"kw_ver_{hash(current_query)}", 0)
    selected_keywords = st.session_state.get(f"kw_pills_{hash(current_query)}_{current_kw_ver}", [])
    snapshot_key = _build_analysis_snapshot_key(
        current_query, current_tax_type, files_hash_str, current_focus, category_choice, selected_keywords
    )
    if snapshot_key in st.session_state:
        return st.session_state[snapshot_key]

    # 0) 외부 AI 호출 전에 내부 Obsidian TAX 지식 DB를 먼저 검색합니다.
    knowledge_hits = []
    knowledge_error = ""
    knowledge_version = "missing"
    stage_started = time.perf_counter()
    knowledge_hits, knowledge_error, knowledge_version = load_internal_knowledge(current_query)
    timings["내부 지식"] = time.perf_counter() - stage_started
    # 현재 화면의 검색 결과는 명시적인 '분석 시작' 전까지 고정한다.
    # 카드 열기처럼 Streamlit이 재실행될 때 DB 버전 변화가 재검색을 유발하면
    # 사용자가 보고 있던 근거가 바뀌어 검토 재현성이 깨진다.
    intent_key = f"intent_v7_{hash(current_query)}_{hash(files_hash_str)}"

    is_new_analysis = False

    if intent_key not in st.session_state:
        is_new_analysis = True
        with st.status("🚀 AI 세무 비서가 심층 분석을 진행 중입니다...", expanded=True) as status:
            st.write(f"📚 내부 TAX 지식 DB 검색 완료 ({len(knowledge_hits)}건 · {timings['내부 지식']:.1f}초)")
            # 1) ChatGPT Enterprise 문맥 및 쟁점 분석
            st.write("🧠 ChatGPT Enterprise(GPT-4o)가 판례 문맥을 분석하고 재정렬하는 중...")
            stage_started = time.perf_counter()
            intent_data = analyze_question(current_query, files_data_list, knowledge_hits)
            timings["AI 쟁점 분석"] = time.perf_counter() - stage_started
            st.write(f"✅ AI 쟁점 분석 완료 ({timings['AI 쟁점 분석']:.1f}초)")
            intent_data["current_focus"] = current_focus
            st.session_state[intent_key] = intent_data

            detected_tax = intent_data.get("tax_category", "조세일반")
            raw_keywords = intent_data.get("search_keywords", [current_query])
            core_issue = intent_data.get("core_issue", "")

            # 키워드 가공 및 세션 저장
            kw_pool_key = f"kw_pool_{hash(current_query)}"
            kw_ver_key = f"kw_ver_{hash(current_query)}"
            kw_ver = st.session_state.get(kw_ver_key, 0)
            kw_pills_key = f"kw_pills_{hash(current_query)}_{kw_ver}"
            kw_active_key = f"kw_active_{hash(current_query)}"

            if kw_pool_key not in st.session_state:
                init_pool = []
                for k in raw_keywords:
                    for part in str(k).strip().split():
                        cl = re.sub(r'(은|는|이|가|을|를|에|의|과|와|으로|로)$', '', part)
                        if len(cl) >= 2 and cl not in init_pool and cl not in STOP_KEYWORDS:
                            init_pool.append(cl)
                for token in re.findall(r'[가-힣]{2,}', current_query):
                    cl = re.sub(r'(은|는|이|가|을|를|에|의|과|와|으로|로)$', '', token)
                    if len(cl) >= 2 and cl not in init_pool and cl not in STOP_KEYWORDS:
                        init_pool.append(cl)

                st.session_state[kw_pool_key] = init_pool[:7]
                st.session_state[kw_active_key] = list(init_pool[:7])

            available_keywords = [k for k in st.session_state.get(kw_pool_key, []) if k not in STOP_KEYWORDS]
            st.session_state[kw_pool_key] = available_keywords
            active_keywords = available_keywords
            keywords = active_keywords

            category_choice = st.session_state.get("selected_category", "전체")
            result_limit = st.session_state.get("result_limit", 15)
            kw_hash_str = "_".join(sorted(active_keywords))
            search_cache_key = f"search_v5_{hash(current_query)}_{category_choice}_{current_tax_type}_{kw_hash_str}_{hash(files_hash_str)}"

            # 2) 국가법령정보센터 판례 DB 검색
            st.write("🔍 국가법령정보센터 관련 판례 및 예규 검색 중...")
            stage_started = time.perf_counter()
            search_res = search_official_sources(
                current_query, current_tax_type, category_choice,
                active_keywords, result_limit, intent_data
            )
            timings["공식자료 검색"] = time.perf_counter() - stage_started
            st.write(f"✅ 공식자료 검색 완료 ({timings['공식자료 검색']:.1f}초)")
            # 네트워크 오류로 인한 일시적 실패 결과는 캐싱하지 않음 (다음 새로고침 시 자동 재호출)
            if search_res and (search_res.get("total", 0) > 0 or not search_res.get("error_type")):
                st.session_state[search_cache_key] = search_res
                st.session_state[f"search_latest_{hash(current_query)}"] = search_res
            results = search_res.get("items", [])

            # 3) 세무 보고서 작성
            st.write("📑 경영진 및 실무진을 위한 목적별 세무 보고서 작성 중...")
            stage_started = time.perf_counter()
            briefing_key = _build_briefing_cache_key(
                current_query=current_query,
                current_tax_type=current_tax_type,
                category_choice=category_choice,
                active_keywords=active_keywords,
                results_count=len(results),
                current_focus=current_focus,
                files_hash_str=files_hash_str,
            )
            briefing_res = create_briefing(current_query, intent_data, results, knowledge_hits)
            timings["AI 의견 작성"] = time.perf_counter() - stage_started
            st.write(f"✅ AI 의견 작성 완료 ({timings['AI 의견 작성']:.1f}초)")
            # 성공적인 응답일 때만 캐시에 보관 (일시적 지연 응답은 캐싱하지 않아 다음 재시도 시 새로 생성)
            if briefing_res and not briefing_res.get("error") and "일시적" not in briefing_res.get("conclusion", ""):
                st.session_state[briefing_key] = briefing_res
                st.session_state[f"briefing_latest_{hash(current_query)}"] = briefing_res

            # 분석 완료 처리
            status.update(label="✅ 심층 분석이 완료되었습니다!", state="complete", expanded=False)
    else:
        timings["AI 쟁점 분석"] = None
        intent_data = st.session_state[intent_key]
        intent_data["current_focus"] = current_focus
        detected_tax = intent_data.get("tax_category", "조세일반")
        raw_keywords = intent_data.get("search_keywords", [current_query])
        core_issue = intent_data.get("core_issue", "")

        kw_pool_key = f"kw_pool_{hash(current_query)}"
        kw_ver_key = f"kw_ver_{hash(current_query)}"
        kw_ver = st.session_state.get(kw_ver_key, 0)
        kw_pills_key = f"kw_pills_{hash(current_query)}_{kw_ver}"
        kw_active_key = f"kw_active_{hash(current_query)}"

        available_keywords = [k for k in st.session_state.get(kw_pool_key, []) if k not in STOP_KEYWORDS]
        if kw_pills_key in st.session_state:
            active_keywords = [k for k in st.session_state[kw_pills_key] if k not in STOP_KEYWORDS]
        else:
            active_keywords = [k for k in st.session_state.get(kw_active_key, available_keywords) if k not in STOP_KEYWORDS]

        if not active_keywords:
            active_keywords = available_keywords
        keywords = active_keywords

        category_choice = st.session_state.get("selected_category", "전체")
        result_limit = st.session_state.get("result_limit", 15)
        kw_hash_str = "_".join(sorted(active_keywords))
        search_cache_key = f"search_v5_{hash(current_query)}_{category_choice}_{current_tax_type}_{kw_hash_str}_{hash(files_hash_str)}"

        if search_cache_key in st.session_state:
            search_res = st.session_state[search_cache_key]
            timings["공식자료 검색"] = None
        elif f"search_latest_{hash(current_query)}" in st.session_state:
            search_res = st.session_state[f"search_latest_{hash(current_query)}"]
            st.session_state[search_cache_key] = search_res
            timings["공식자료 검색"] = None
        else:
            with st.spinner("🔍 국가법령 판례 DB를 검색 중입니다..."):
                stage_started = time.perf_counter()
                search_res = search_official_sources(
                    current_query, current_tax_type, category_choice,
                    active_keywords, result_limit, intent_data
                )
                timings["공식자료 검색"] = time.perf_counter() - stage_started
                if search_res and (search_res.get("total", 0) > 0 or not search_res.get("error_type")):
                    st.session_state[search_cache_key] = search_res
                    st.session_state[f"search_latest_{hash(current_query)}"] = search_res

        results = search_res.get("items", [])
        briefing_key = _build_briefing_cache_key(
            current_query=current_query,
            current_tax_type=current_tax_type,
            category_choice=category_choice,
            active_keywords=active_keywords,
            results_count=len(results),
            current_focus=current_focus,
            files_hash_str=files_hash_str,
        )
        if briefing_key in st.session_state:
            briefing_res = st.session_state[briefing_key]
            timings["AI 의견 작성"] = None
        elif f"briefing_latest_{hash(current_query)}" in st.session_state:
            briefing_res = st.session_state[f"briefing_latest_{hash(current_query)}"]
            st.session_state[briefing_key] = briefing_res
            timings["AI 의견 작성"] = None
        else:
            with st.spinner("📑 세무 검토 의견서를 생성하고 있습니다..."):
                stage_started = time.perf_counter()
                briefing_res = create_briefing(current_query, intent_data, results, knowledge_hits)
                timings["AI 의견 작성"] = time.perf_counter() - stage_started
                if briefing_res and not briefing_res.get("error") and "일시적" not in briefing_res.get("conclusion", ""):
                    st.session_state[briefing_key] = briefing_res
                    st.session_state[f"briefing_latest_{hash(current_query)}"] = briefing_res
                    is_new_analysis = True

    # [Stage 2] AI 신규 분석 완료 시에만 안전한 동기 저장 (Safe Synchronous Save)
    # 단순 카드 열기/닫기나 리프레시 시에는 중복 저장/리비전 누적을 방지함
    if is_new_analysis:
        stage_started = time.perf_counter()
        try:
            from repositories.review_repo import get_review_repository
            repo = get_review_repository()
            
            top_cases_summary = []
            for r in (results or [])[:5]:
                top_cases_summary.append({
                    "case_number": r.get("case_number", ""),
                    "title": r.get("title", ""),
                    "basis_type": r.get("basis_type", r.get("basis_bucket_name", "")),
                    "relevance_score": r.get("relevance_score", 0),
                    "court": r.get("court", ""),
                    "date": r.get("date", ""),
                    "url": r.get("url", ""),
                    "summary": (r.get("summary", "") or r.get("snippet", "") or "")[:200]
                })

            raw_chk = (briefing_res or {}).get("checklist", [])
            checklist_items = raw_chk if isinstance(raw_chk, list) else [str(raw_chk)] if raw_chk else []

            save_rec_id, is_new = repo.save_review(
                query=current_query,
                tax_category=detected_tax,
                core_issue=core_issue,
                active_keywords=active_keywords,
                risk_level=(briefing_res or {}).get("risk_level", "중립/유의"),
                briefing_conclusion=(briefing_res or {}).get("conclusion", ""),
                checklist=checklist_items,
                direct_basis_count=len([r for r in (results or []) if r.get("basis_bucket") == "direct_basis" or r.get("basis_type") == "직접근거 후보"]),
                total_results_count=len(results or []),
                top_cases=top_cases_summary,
                applied_tax_base_date=config.get_tax_base_date(),
                model_used=config.get_ai_service_name(),
                user_id="jongmin.park1@cj.net",
                case_comparison=(briefing_res or {}).get("case_comparison", ""),
                risk_reason=(briefing_res or {}).get("risk_reason", ""),
                briefing_full=briefing_res,
                selected_category=category_choice,
                current_focus=current_focus,
                files_fingerprint=files_hash_str,
                knowledge_sources=(briefing_res or {}).get("internal_knowledge_sources", []),
            )
            if not save_rec_id:
                save_error = "검토 기록 데이터 파일(review_history.json) 원자적 쓰기에 실패하였습니다."
            else:
                save_error = None
        except Exception as ex:
            save_error = f"검토 기록 저장 중 오류 발생: {str(ex)}"
            save_rec_id = None
        timings["검토 기록 저장"] = time.perf_counter() - stage_started

    timings["전체"] = time.perf_counter() - pipeline_started
    logger.info("[분석 성능] query_hash=%s | %s", abs(hash(current_query)), _format_pipeline_timings(timings))

    analysis = {
        "intent_data": intent_data,
        "detected_tax": detected_tax,
        "core_issue": core_issue,
        "kw_pool_key": kw_pool_key,
        "kw_ver_key": kw_ver_key,
        "kw_ver": kw_ver,
        "kw_pills_key": kw_pills_key,
        "kw_active_key": kw_active_key,
        "available_keywords": available_keywords,
        "active_keywords": active_keywords,
        "keywords": keywords,
        "search_res": search_res,
        "results": results,
        "briefing_res": briefing_res,
        "save_error": save_error,
        "save_rec_id": save_rec_id,
        "top_cases_summary": top_cases_summary if 'top_cases_summary' in locals() else [],
        "checklist_items": checklist_items if 'checklist_items' in locals() else [],
        "category_choice": category_choice,
        "current_focus": current_focus,
        "files_hash_str": files_hash_str,
        "knowledge_hits": knowledge_hits,
        "knowledge_error": knowledge_error,
        "knowledge_version": knowledge_version,
        "timings": timings,
    }
    st.session_state[snapshot_key] = analysis
    return analysis


def render_search_view():
    """
    화면 3: 판례 실시간 검색 및 AI 분석 뷰 (Search View) - 글로벌 SaaS 듀얼 페인 (Dual-Pane) 레이아웃
    """
    current_query = st.session_state.get("search_input", "").strip()
    is_home = not bool(current_query)

    # 1. 메인 서비스 헤더
    if is_home:
        st.markdown("""
        <div style="padding: 10px 0 14px 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 16px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:0.75rem; font-weight:700; color:#003876; background:#EFF8FF; border:1px solid #B2DDFF; padding:2px 8px; border-radius:4px;">CJ FRESHWAY · TAX AI</span>
                    <div style="font-size:1.40rem; font-weight:800; color:#0F172A; margin-top:4px;">세무 상황 진단 & 조세 판례 AI 검토</div>
                </div>
                <div style="font-size:0.84rem; color:#64748B;">
                    공식 판례·예규 DB + ChatGPT Enterprise(GPT-4o) 실시간 심층 분석
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="compact-header" style="padding-bottom:10px; margin-bottom:14px; border-bottom:1px solid #E2E8F0;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:0.75rem; font-weight:700; color:#003876; background:#EFF8FF; border:1px solid #B2DDFF; padding:2px 8px; border-radius:4px;">CJ FRESHWAY · TAX AI</span>
                    <div style="font-size:1.35rem; font-weight:800; color:#0F172A; margin-top:4px;">세무 상황 진단 & 판례 AI 검토</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # =========================================================================
    # [1단계: 상단 작업 공간] 대분류 탭 (법리·판례 검색 vs AI 문서/계약서 정밀 검토)
    # =========================================================================
    input_ver = st.session_state.get("input_version", 0)
    current_search_input = st.session_state.get("search_input", "")

    tab_search, tab_doc = st.tabs(["🔍 세무 법리·판례 검색", "📄 AI 문서/계약서 정밀 검토"])

    # --- 탭 1: 세무 법리·판례 검색 (기존 검색창 & 7대 요건 상세 폼) ---
    with tab_search:
        # 원클릭 추천 예시 질의 칩
        st.markdown("<div style='font-size:0.80rem; font-weight:700; color:#475569; margin-bottom:6px;'>💡 추천 예시 질의 (원클릭 자동 입력 및 즉시 분석):</div>", unsafe_allow_html=True)
        col_ex1, col_ex2, col_ex3, col_ex4 = st.columns([1.25, 1.25, 1.25, 0.75])
        with col_ex1:
            if st.button("🏢 특수관계인 무이자대여", key=f"ex_btn_1_{input_ver}", use_container_width=True):
                q = "모회사 A가 자회사 B에게 운영자금을 무이자로 대여해주려 하는데, 부당행위계산부인 대상이 될까?"
                st.session_state[f"nlp_query_{input_ver}"] = q
                st.session_state["search_input"] = q
                st.session_state["is_doc_mode"] = False
                st.toast("🚀 '특수관계인 무이자대여' 분석을 시작합니다!", icon="⏳")
                st.rerun()
        with col_ex2:
            if st.button("🧾 임원 퇴직금 한도초과", key=f"ex_btn_2_{input_ver}", use_container_width=True):
                q = "법인이 임원에게 지급하는 퇴직금이 손금산입 한도를 초과할 경우 세무조정은 어떻게 처리해야 할까?"
                st.session_state[f"nlp_query_{input_ver}"] = q
                st.session_state["search_input"] = q
                st.session_state["is_doc_mode"] = False
                st.toast("🚀 '임원 퇴직금 한도초과' 분석을 시작합니다!", icon="⏳")
                st.rerun()
        with col_ex3:
            if st.button("⚖️ 상표권 무상사용 VAT", key=f"ex_btn_3_{input_ver}", use_container_width=True):
                q = "CJ제일제당이 보유한 상표권을 CJ ENM이 무상으로 사용할 때 부가가치세 과세 문제가 발생해?"
                st.session_state[f"nlp_query_{input_ver}"] = q
                st.session_state["search_input"] = q
                st.session_state["is_doc_mode"] = False
                st.toast("🚀 '상표권 무상사용 VAT' 분석을 시작합니다!", icon="⏳")
                st.rerun()
        with col_ex4:
            if st.button("🔄 초기화", key=f"ex_btn_reset_{input_ver}", use_container_width=True):
                st.session_state["search_input"] = ""
                st.session_state[f"nlp_query_{input_ver}"] = ""
                st.session_state["is_doc_mode"] = False
                st.session_state["input_version"] = input_ver + 1
                st.rerun()

        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

        query_key = f"nlp_query_{input_ver}"
        if query_key not in st.session_state or not st.session_state[query_key]:
            if current_search_input and not st.session_state.get("is_doc_mode", False):
                st.session_state[query_key] = current_search_input

        with st.form(key=f"minimal_search_form_{input_ver}", clear_on_submit=False):
            # 1) 메인 큼직한 자연어 질의 입력창 (Google 스타일)
            user_query = st.text_area(
                "검토할 세무 사실관계, 거래 내용 또는 질문을 입력하세요.",
                height=140,
                placeholder="예시:\n- 모회사 A가 자회사 B에게 운영자금을 무이자로 대여해주려 하는데, 부당행위계산부인 대상이 될까?\n- 법인이 임원에게 지급하는 퇴직금이 손금산입 한도를 초과할 경우 세무조정은 어떻게 해?\n- CJ제일제당이 보유한 상표권을 CJ ENM이 무상으로 사용할 때 부가가치세 과세 문제가 발생해?",
                key=query_key,
                label_visibility="collapsed"
            )

            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

            # 2) 점진적 공개 Expander: 상세 검색 및 분석 옵션 (세목·기관 필터 / 7대 요건 상세 폼)
            with st.expander("⚙️ 상세 검색 및 분석 옵션 (세목·기관 필터 / 7대 요건 상세 폼)", expanded=False):
                # A. 세목 / 기관 검색 범위 필터
                st.markdown("<div style='font-size:0.84rem; font-weight:700; color:#475569; margin-bottom:6px;'>🔍 검색 범위 필터</div>", unsafe_allow_html=True)
                col_filt_tax, col_filt_cat = st.columns([5.0, 5.0], vertical_alignment="center")

                tax_pill_options = ["전체 세목", "🏢 법인세", "🧾 부가가치세", "👤 소득세·원천세"]
                tax_pill_map = {
                    "전체 세목": "전체",
                    "🏢 법인세": "법인세",
                    "🧾 부가가치세": "부가가치세",
                    "👤 소득세·원천세": "소득세·원천세"
                }
                reverse_tax_map = {v: k for k, v in tax_pill_map.items()}

                cat_pill_options = ["🏛️ 전체 자료", "⚖️ 법원 판례", "🏢 조세심판·결정례", "📜 예규·법령해석"]
                cat_pill_map = {
                    "🏛️ 전체 자료": "전체",
                    "⚖️ 법원 판례": "판례",
                    "🏢 조세심판·결정례": "조세심판/결정례",
                    "📜 예규·법령해석": "예규/해석례"
                }
                reverse_cat_map = {
                    "전체": "🏛️ 전체 자료",
                    "판례": "⚖️ 법원 판례",
                    "조세심판/행정청": "🏢 조세심판·결정례",
                    "조세심판/결정례": "🏢 조세심판·결정례",
                    "예규/해석례": "📜 예규·법령해석"
                }

                with col_filt_tax:
                    curr_tax = st.session_state.get("selected_tax_type", "전체")
                    def_tax_idx = 0
                    if reverse_tax_map.get(curr_tax) in tax_pill_options:
                        def_tax_idx = tax_pill_options.index(reverse_tax_map.get(curr_tax))
                    chosen_pill = st.radio(
                        "세목 필터",
                        tax_pill_options,
                        index=def_tax_idx,
                        horizontal=True,
                        label_visibility="collapsed",
                        key=f"tax_radio_selector_{input_ver}"
                    )
                    if chosen_pill:
                        st.session_state["selected_tax_type"] = tax_pill_map.get(chosen_pill, "전체")

                with col_filt_cat:
                    curr_cat = st.session_state.get("selected_category", "전체")
                    def_cat_idx = 0
                    if reverse_cat_map.get(curr_cat) in cat_pill_options:
                        def_cat_idx = cat_pill_options.index(reverse_cat_map.get(curr_cat))
                    chosen_cat_pill = st.radio(
                        "기관 필터",
                        cat_pill_options,
                        index=def_cat_idx,
                        horizontal=True,
                        label_visibility="collapsed",
                        key=f"cat_radio_selector_{input_ver}"
                    )
                    if chosen_cat_pill:
                        st.session_state["selected_category"] = cat_pill_map.get(chosen_cat_pill, "전체")

                st.markdown("<div style='height: 12px; border-bottom:1px dashed #E2E8F0; margin-bottom:12px;'></div>", unsafe_allow_html=True)

                # B. 세무검토 상세 폼 (7대 요건)
                st.markdown("<div style='font-size:0.84rem; font-weight:700; color:#475569; margin-bottom:4px;'>📋 세무검토 상세 폼 (7대 요건)</div>", unsafe_allow_html=True)
                st.markdown("<div style='font-size:0.79rem; color:#64748B; margin-bottom:8px;'>거래 주체, 목적 등 요건을 구조화하여 입력하시면 더 정밀하게 판례를 매칭합니다.</div>", unsafe_allow_html=True)
                f_actor = st.text_input("1. 주체 (행위자)", placeholder="예: 내국법인, 모회사", key=f"f_actor_{input_ver}")
                f_action = st.text_input("2. 행위 (거래형태)", placeholder="예: 무상대여, 자산양도", key=f"f_action_{input_ver}")
                f_object = st.text_input("3. 객체 (대상)", placeholder="예: 운영자금, 상표권", key=f"f_object_{input_ver}")
                f_purpose = st.text_input("4. 목적/사유", placeholder="예: 자금난 해소", key=f"f_purpose_{input_ver}")
                f_condition = st.text_input("5. 조건/금액", placeholder="예: 무이자, 시가 100억", key=f"f_condition_{input_ver}")
                f_result = st.text_input("6. 결과/현상", placeholder="예: 이자수익 미계상", key=f"f_result_{input_ver}")
                f_issue = st.text_input("7. 핵심 쟁점", placeholder="예: 부당행위계산부인 적용 여부", key=f"f_issue_{input_ver}")

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                analysis_focus = st.selectbox(
                    "🔍 주요 검토 포인트 (선택사항)",
                    ["종합 검토", "과세관청 입장/리스크", "절세/방어 논리", "조세불복/소송 가능성"],
                    key=f"nlp_focus_{input_ver}"
                )

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            # 3) 분석 시작 버튼
            analyze_clicked = st.form_submit_button("🚀 AI 세무·판례 심층 분석 시작 (Ctrl + Enter)", type="primary", use_container_width=True)
            st.markdown("<div style='font-size:0.76rem; color:#64748B; text-align:center; margin-top:2px;'>💡 내용을 입력하신 후 버튼을 누르거나 <b>Ctrl + Enter</b>를 누르시면 즉시 분석이 시작됩니다.</div>", unsafe_allow_html=True)

            if analyze_clicked:
                composed_parts = []
                if user_query and user_query.strip():
                    composed_parts.append(user_query.strip())

                form_fields = [
                    ("주체", f_actor), ("행위", f_action), ("객체", f_object),
                    ("목적", f_purpose), ("조건", f_condition), ("결과", f_result), ("쟁점", f_issue)
                ]
                form_str_parts = [f"{label}: {val.strip()}" for label, val in form_fields if val and val.strip()]
                if form_str_parts:
                    composed_parts.append("\n[세무검토 상세 폼 요건]\n" + "\n".join(form_str_parts))

                final_query = "\n\n".join(composed_parts).strip()

                if not final_query:
                    st.toast("⚠️ 검토할 세무 사실관계나 질문을 먼저 입력해 주세요!", icon="⚠️")
                    st.warning("⚠️ **질문이 입력되지 않았습니다.**\n\n위 입력창에 사실관계를 입력하시거나, 상단의 **[💡 추천 예시 질의]** 버튼을 눌러 바로 실행해 보세요.")
                else:
                    st.session_state["search_input"] = final_query
                    st.session_state["current_focus"] = analysis_focus
                    st.session_state["temp_files_data"] = []
                    st.session_state["is_doc_mode"] = False
                    
                    # 명시적 분석 버튼 클릭 시 이전 캐시 무효화하여 최신 분석 강제 실행
                    h_raw = str(hash(final_query))
                    h_abs = str(abs(hash(final_query)))
                    for k in list(st.session_state.keys()):
                        if any(k.startswith(prefix) for prefix in ("analysis_snapshot_", "intent_", "briefing_", "search_", "kw_")):
                            if h_raw in k or h_abs in k:
                                del st.session_state[k]

                    st.toast("🚀 AI 세무 비서가 심층 분석을 시작합니다. 잠시만 기다려 주세요...", icon="⏳")
                    current_query = final_query
                    is_home = False
                    st.rerun()

    # --- 탭 2: AI 문서/계약서 정밀 검토 (전용 업로더 & 정밀 검토 작업공간) ---
    with tab_doc:
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #005B45; border-radius:8px; padding:12px 16px; margin-bottom:12px;">
            <div style="font-size:0.92rem; font-weight:700; color:#005B45;">📄 AI 문서 & 계약서 세무 리스크 정밀 검토</div>
            <div style="font-size:0.82rem; color:#475569; line-height:1.5; margin-top:3px;">
                계약서, 합의서, 거래 품의서(PDF, 이미지, TXT, DOCX)를 업로드하시면 ChatGPT Enterprise(GPT-4o)가 조항별 과세 위험, 세금계산서 수취 적정성, 부당행위계산 부인 요건 등을 다각도로 정밀 검토합니다.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form(key=f"doc_analysis_form_{input_ver}", clear_on_submit=False):
            # 1) 큼직한 파일 업로더
            uploaded_files = st.file_uploader(
                "검토할 계약서 및 증빙 문서 업로드 (PDF, PNG, JPG, JPEG, TXT, DOCX)",
                type=["pdf", "png", "jpg", "jpeg", "txt", "docx"],
                accept_multiple_files=True,
                key=f"main_doc_uploader_{input_ver}",
                help="다중 파일 업로드를 지원합니다. 계약서 본문 및 첨부 별지를 함께 업로드하세요."
            )

            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

            # 2) AI 문맥 이해를 위한 배경 설명 텍스트 영역
            doc_context = st.text_area(
                "계약서 배경 및 특별히 검토할 쟁점을 적어주세요",
                placeholder="예시:\n- 당사와 계열사 간 체결한 부동산 임대차/용역 위탁 계약서입니다. 임대료/수수료 산정이 시가에 부합하는지 및 부당행위계산 부인 리스크를 중점 검토해 주세요.\n- OEM 위탁생산 계약에서 발생하는 원자재 무상사급 관련 부가가치세 공급의제 해당 여부를 확인해 주세요.",
                height=120,
                key=f"main_doc_context_{input_ver}"
            )

            col_doc_opt1, col_doc_opt2 = st.columns([1, 1], vertical_alignment="center")
            with col_doc_opt1:
                doc_tax_type = st.selectbox(
                    "관련 세목 우선 지정 (선택사항)",
                    ["전체 (AI 자동 판별)", "법인세", "부가가치세", "소득세·원천세"],
                    key=f"doc_tax_type_{input_ver}"
                )
            with col_doc_opt2:
                doc_focus = st.selectbox(
                    "중점 분석 관점",
                    ["종합 검토", "과세관청 입장/리스크", "절세/방어 논리", "조세불복/소송 가능성"],
                    key=f"doc_focus_{input_ver}"
                )

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            # 3) 문서 탭 전용 큼직한 실행 버튼
            doc_analyze_clicked = st.form_submit_button(
                "🚀 AI 계약서 심층 검토 시작 (Ctrl + Enter)",
                type="primary",
                use_container_width=True
            )
            st.markdown("<div style='font-size:0.76rem; color:#64748B; text-align:center; margin-top:2px;'>💡 문서를 첨부하신 후 버튼을 누르거나 <b>Ctrl + Enter</b>를 누르시면 즉시 분석이 시작됩니다.</div>", unsafe_allow_html=True)

            if doc_analyze_clicked:
                if not uploaded_files:
                    st.toast("⚠️ 검토할 계약서 또는 문서 파일(PDF, 이미지, TXT 등)을 1개 이상 업로드해 주세요!", icon="⚠️")
                    st.warning("⚠️ **문서가 첨부되지 않았습니다.** 검토할 계약서 또는 문서 파일(PDF, 이미지, TXT 등)을 1개 이상 업로드해 주세요.")
                else:
                    uploaded_files_data = []
                    files_list = uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]
                    file_names_str = ", ".join([f.name for f in files_list])
                    for uf in files_list:
                        uploaded_files_data.append({
                            "name": uf.name,
                            "bytes": uf.getvalue()
                        })

                    composed_doc_query = f"[{file_names_str}] 계약서 정밀 검토"
                    if doc_context and doc_context.strip():
                        composed_doc_query += f"\n\n[검토 요청 쟁점 및 배경]\n{doc_context.strip()}"

                    if doc_tax_type != "전체 (AI 자동 판별)":
                        st.session_state["selected_tax_type"] = doc_tax_type
                    else:
                        st.session_state["selected_tax_type"] = "전체"

                    st.session_state["search_input"] = composed_doc_query
                    st.session_state["current_focus"] = doc_focus
                    st.session_state["temp_files_data"] = uploaded_files_data
                    st.session_state["is_doc_mode"] = True
                    
                    # 문서 검토 시 이전 캐시 무효화
                    h_raw = str(hash(composed_doc_query))
                    h_abs = str(abs(hash(composed_doc_query)))
                    for k in list(st.session_state.keys()):
                        if any(k.startswith(prefix) for prefix in ("analysis_snapshot_", "intent_", "briefing_", "search_", "kw_")):
                            if h_raw in k or h_abs in k:
                                del st.session_state[k]

                    st.toast("🚀 AI 계약서 심층 검토를 시작합니다. 잠시만 기다려 주세요...", icon="⏳")
                    current_query = composed_doc_query
                    is_home = False
                    st.rerun()

    # C. 💬 전문 세무 비서 1:1 꼬리질문 상담 UI
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    
    chat_history_key = f"chat_{hash(current_query)}" if current_query else "chat_home"
    if chat_history_key not in st.session_state:
        st.session_state[chat_history_key] = []

    chat_list = st.session_state[chat_history_key]
    has_chat = len(chat_list) > 0
    expander_label = f"💬 전문 세무 비서 1:1 꼬리질문 상담 ({len(chat_list)//2}개 대화)" if has_chat else "💬 전문 세무 비서 1:1 꼬리질문 상담"

    with st.expander(expander_label, expanded=has_chat):
        st.markdown("""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-left:4px solid #003876; border-radius:6px; padding:8px 12px; margin-bottom:10px; font-size:0.82rem; color:#334155;">
            💡 <b>1:1 AI 세무 상담:</b> 아래 세무 검토 리포트를 확인하면서 추가 질문, 구비 증빙, 소명 논리 등을 자유롭게 질문하세요.
        </div>
        """, unsafe_allow_html=True)

        if chat_list:
            for msg in chat_list:
                avatar_icon = "👤" if msg["role"] == "user" else "🤖"
                with st.chat_message(msg["role"], avatar=avatar_icon):
                    st.markdown(msg["text"])
        else:
            if not current_query:
                st.caption("위 폼에 세무 질의를 입력하고 분석을 시작하시면 실시간 1:1 꼬리질문 상담이 활성화됩니다.")
            else:
                st.caption("아래 추천 버튼을 클릭하거나 추가 질문을 입력해 보세요.")

        if current_query:
            st.markdown("<div style='font-size:0.78rem; font-weight:700; color:#475569; margin-top:8px; margin-bottom:6px;'>💡 추천 꼬리질문 (1회 클릭 실행):</div>", unsafe_allow_html=True)
            col_b1, col_b2, col_b3 = st.columns([1, 1, 1], vertical_alignment="center")
            with col_b1:
                btn_q1 = st.button("📋 필수 증빙", key=f"btn_q1_{hash(current_query)}", use_container_width=True)
            with col_b2:
                btn_q2 = st.button("⚖️ 반박 포인트", key=f"btn_q2_{hash(current_query)}", use_container_width=True)
            with col_b3:
                btn_q3 = st.button("💡 리스크 방안", key=f"btn_q3_{hash(current_query)}", use_container_width=True)

            with st.form(key=f"followup_form_{hash(current_query)}", clear_on_submit=True):
                col_inp, col_btn = st.columns([3.6, 1.4], vertical_alignment="center")
                with col_inp:
                    user_text_val = st.text_input("추가 질문 입력", placeholder="추가 궁금한 점을 적어보세요", label_visibility="collapsed")
                with col_btn:
                    btn_send = st.form_submit_button("💬 질문", use_container_width=True)

            input_prompt = None
            if btn_q1:
                input_prompt = "📋 필수 구비 증빙 목록 자세히 설명해줘"
            elif btn_q2:
                input_prompt = "⚖️ 과세관청 주요 논리와 반박 포인트는?"
            elif btn_q3:
                input_prompt = "💡 이번 사안의 세무조사 리스크 최소화 방안은?"
            elif btn_send and user_text_val.strip():
                input_prompt = user_text_val.strip()

            if input_prompt:
                st.session_state[chat_history_key].append({"role": "user", "text": input_prompt})
                
                q_hash = hash(current_query)
                intent_prefix = f"intent_v5_{q_hash}_"
                ctx_intent = next((v for k, v in st.session_state.items() if k.startswith(intent_prefix) or f"_{q_hash}_" in k or f"_{q_hash}" in k), st.session_state.get(f"intent_v5_{q_hash}", {}))
                ctx_briefing = next((v for k, v in st.session_state.items() if k.startswith(f"briefing_v9_{q_hash}_") or (k.startswith("briefing_") and f"_{q_hash}_" in k)), st.session_state.get(f"briefing_{q_hash}", {}))

                context_bundle = {
                    "intent": ctx_intent,
                    "briefing": ctx_briefing
                }
                ai_response = generate_followup_answer(
                    user_message=input_prompt,
                    chat_history=st.session_state[chat_history_key][:-1],
                    context_data=context_bundle
                )
                st.session_state[chat_history_key].append({"role": "assistant", "text": ai_response})
                st.rerun()

    # D. 초기 홈 화면일 때: '최근 보관 사례 보기'
    if is_home:
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        saved_dict = st.session_state.get("saved_cases", {})
        with st.expander("📁 최근 보관 사례 보기", expanded=False):
            if saved_dict:
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:0.80rem; color:#475569;">보관된 최근 사례 목록</span>
                    <span style="font-size:0.78rem; color:#005B45; font-weight:600;">총 <b>{len(saved_dict)}건</b></span>
                </div>
                """, unsafe_allow_html=True)

                recent_cases = list(saved_dict.values())[-4:]
                recent_cases.reverse()

                for r_idx, r_item in enumerate(recent_cases):
                    r_title = r_item.get("title", "")
                    if len(r_title) > 40:
                        r_title = r_title[:40] + "..."
                    r_tax = r_item.get("tax_category", "조세일반")
                    r_risk = r_item.get("risk_level", "중립/유의")
                    r_date = str(r_item.get("created_at", r_item.get("saved_at", "-")))[:10]

                    r_risk_badge = '<span class="badge-risk-high">高</span>' if "고위험" in r_risk else ('<span class="badge-risk-low">低</span>' if ("저위험" in r_risk or "안전" in r_risk) else '<span class="badge-risk-med">中</span>')
                    r_tax_badge = f'<span class="tax-badge tax-corp">{r_tax}</span>'

                    st.markdown(f"""
                    <div class="recent-case-card" style="margin-bottom:6px; padding:8px 12px; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">
                            <div>{r_tax_badge} {r_risk_badge}</div>
                            <span style="font-size:0.70rem; color:#94A3B8;">{r_date}</span>
                        </div>
                        <div style="font-size:0.84rem; font-weight:700; color:#0F172A; line-height:1.3;">{r_title}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"사례 바로보기 ({r_title})", key=f"btn_recent_case_{r_idx}", use_container_width=True):
                        st.session_state["active_view"] = "vault"
                        st.rerun()
            else:
                st.info("현재 보관된 세무검토 사례가 없습니다.")

    # =========================================================================
    # [2단계: 하단 결과 영역] 결과 리포트 및 판례 뷰어 (전체 너비 100%)
    # =========================================================================
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # A. 초기 홈 화면 (검색 전): 상하 안내 가이드
    if is_home:
        st.markdown("""
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding: 48px 24px; background: #FFFFFF; border: 1.5px dashed #CBD5E1; border-radius: 12px; text-align: center; margin-top: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
            <div style="font-size: 2.5rem; margin-bottom: 12px; animation: pulse 2.5s infinite ease-in-out;">👆</div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 8px;">
                AI 세무 진단 및 판례 분석 대기 중
            </div>
            <div style="font-size: 0.90rem; color: #475569; max-width: 520px; line-height: 1.65; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 18px; margin-top: 8px;">
                <b>위 입력창에 세무 사실관계나 궁금한 점을 입력하시면,</b><br>
                AI가 정밀 분석한 결과가 이곳에 시원하게 넓은 화면으로 표시됩니다.
            </div>
            <div style="margin-top: 20px; display:flex; gap:10px; flex-wrap:wrap; justify-content:center;">
                <span style="font-size:0.78rem; background:#EFF6FF; color:#1D4ED8; padding:4px 10px; border-radius:14px; font-weight:600;">🏢 특수관계인 무상대여</span>
                <span style="font-size:0.78rem; background:#F0FDF4; color:#15803D; padding:4px 10px; border-radius:14px; font-weight:600;">🧾 임원 퇴직금 한도초과</span>
                <span style="font-size:0.78rem; background:#FAF5FF; color:#7E22CE; padding:4px 10px; border-radius:14px; font-weight:600;">⚖️ 상표권 무상사용 VAT</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # B. 검색 완료 화면 (current_query 존재하는 경우)
    else:
            # 1) intent 분석 & law API 검색 (캐시 로드 또는 신규 실행)
            current_tax_type = st.session_state.get("selected_tax_type", "전체")
            files_data_list = st.session_state.get("temp_files_data", [])

            _analysis = _load_or_run_analysis(current_query, current_tax_type, files_data_list)
            intent_data = _analysis["intent_data"]
            detected_tax = _analysis["detected_tax"]
            core_issue = _analysis["core_issue"]
            kw_pool_key = _analysis["kw_pool_key"]
            kw_ver_key = _analysis["kw_ver_key"]
            kw_ver = _analysis["kw_ver"]
            kw_pills_key = _analysis["kw_pills_key"]
            kw_active_key = _analysis["kw_active_key"]
            available_keywords = _analysis["available_keywords"]
            active_keywords = _analysis["active_keywords"]
            keywords = _analysis["keywords"]
            search_res = _analysis["search_res"]
            results = _analysis["results"]
            briefing_res = _analysis["briefing_res"]
            knowledge_hits = _analysis.get("knowledge_hits", [])
            knowledge_error = _analysis.get("knowledge_error", "")
            st.caption(f"⏱ 처리 시간 · {_format_pipeline_timings(_analysis.get('timings', {}))}")

            effective_tax = current_tax_type if current_tax_type != "전체" else detected_tax
            results = search_res.get("items", [])
            st.session_state["last_search_results"] = results
            total_cnt = search_res.get("total", 0)
            direct_basis_count = len([r for r in results if r.get("basis_bucket") == "direct_basis" or "직접" in str(r.get("basis_type", "")) or "직접" in str(r.get("basis_bucket_name", ""))])
            support_basis_count = len([r for r in results if r.get("basis_bucket") in ("similar_basis", "evidence_basis", "risk_basis") or "보조" in str(r.get("basis_type", "")) or "유사" in str(r.get("basis_bucket_name", "")) or "리스크" in str(r.get("basis_bucket_name", "")) or "증빙" in str(r.get("basis_bucket_name", ""))])
            reference_basis_count = len([r for r in results if r.get("basis_bucket") in ("statute_or_admin_basis", "weak_reference") or "참고" in str(r.get("basis_type", "")) or "예규" in str(r.get("basis_bucket_name", "")) or "참고" in str(r.get("basis_bucket_name", ""))])

            with st.expander(f"📚 내부 TAX 지식 검색 결과 ({len(knowledge_hits)}건 · 최대 5건)", expanded=False):
                if knowledge_error:
                    st.warning("내부 지식 DB를 조회하지 못했지만 기존 AI·판례 분석은 정상 진행했습니다.")
                elif not knowledge_hits:
                    st.info("현재 질문과 일치하는 내부 TAX 문서를 찾지 못했습니다.")
                else:
                    for index, hit in enumerate(knowledge_hits, 1):
                        source_label = "회계팀 승인 지식" if hit.get("knowledge_type") == "approved_review" else "Obsidian"
                        st.markdown(f"**{index}. [{source_label}] {hit.get('title', '제목 없음')}**")
                        st.caption(f"{source_label} · {hit.get('source_path', '')}")
                        st.write(hit.get("excerpt", ""))
                        if index < len(knowledge_hits):
                            st.divider()

            ai_error_msg = briefing_res.get("error")
            if ai_error_msg:
                st.markdown(f'''
                <div style="background:#FAF5FF; border:1.5px solid #D8B4FE; border-left:5px solid #9333EA; border-radius:10px; padding:14px 18px; margin-bottom:14px;">
                    <div style="font-weight:700; color:#6B21A8; font-size:0.95rem;">🤖 [ChatGPT Enterprise AI 모델 처리 오류]</div>
                    <div style="color:#7E22CE; font-size:0.86rem; margin-top:4px;">{ai_error_msg}</div>
                </div>
                ''', unsafe_allow_html=True)

            save_error = _analysis.get("save_error")
            if save_error and not st.session_state.get(f"save_resolved_{abs(hash(current_query))}", False):
                col_w_msg, col_w_btn = st.columns([4.2, 1.3], vertical_alignment="center")
                with col_w_msg:
                    st.markdown(f'''
                    <div style="background:#FFFBEB; border:1.5px solid #FCD34D; border-left:5px solid #D97706; border-radius:10px; padding:12px 16px; margin-bottom:12px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
                        <div style="font-weight:700; color:#B45309; font-size:0.90rem;">⚠️ [검토 기록 저장 실패 안내]</div>
                        <div style="font-size:0.83rem; color:#78350F; margin-top:4px; line-height:1.55;">
                            • <b>판례 검색 및 AI 심층 분석 결과</b>는 화면에 정상적으로 표시되었습니다.<br>
                            • 다만, 파일 시스템 오류로 <b>검토 기록(히스토리) 영구 저장에 실패</b>하였습니다.<br>
                            • 우측 버튼을 눌러 다시 시도하시거나, 문제가 지속될 경우 시스템 관리자에게 파일 쓰기 권한(<code>review_history.json</code>)을 확인해 주세요.
                        </div>
                        <div style="font-size:0.76rem; color:#92400E; margin-top:5px; background:#FEF3C7; padding:3px 8px; border-radius:4px; display:inline-block;">
                            <b>원인:</b> {save_error}
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                with col_w_btn:
                    if st.button("🔄 기록 저장 재시도", key=f"btn_retry_save_{abs(hash(current_query))}", use_container_width=True):
                        try:
                            from repositories.review_repo import get_review_repository
                            r_repo = get_review_repository()
                            r_id, _ = r_repo.save_review(
                                query=current_query,
                                tax_category=detected_tax,
                                core_issue=core_issue,
                                active_keywords=active_keywords,
                                risk_level=(briefing_res or {}).get("risk_level", "중립/유의"),
                                briefing_conclusion=(briefing_res or {}).get("conclusion", ""),
                                checklist=_analysis.get("checklist_items", []),
                                direct_basis_count=direct_basis_count,
                                total_results_count=len(results or []),
                                top_cases=_analysis.get("top_cases_summary", []),
                                applied_tax_base_date=config.get_tax_base_date(),
                                model_used=config.get_ai_service_name(),
                                user_id="jongmin.park1@cj.net",
                                case_comparison=(briefing_res or {}).get("case_comparison", ""),
                                risk_reason=(briefing_res or {}).get("risk_reason", ""),
                                briefing_full=briefing_res,
                                selected_category=_analysis.get("category_choice", "전체"),
                                current_focus=_analysis.get("current_focus", "종합"),
                                files_fingerprint=_analysis.get("files_hash_str", ""),
                                knowledge_sources=(briefing_res or {}).get("internal_knowledge_sources", []),
                            )
                            if r_id:
                                st.session_state[f"save_resolved_{abs(hash(current_query))}"] = True
                                st.toast("✅ 검토 기록이 성공적으로 저장되었습니다!", icon="💾")
                                st.rerun()
                            else:
                                st.error("❌ 저장 재시도 실패 (파일 쓰기 권한 확인 필요)")
                        except Exception as e_retry:
                            st.error(f"❌ 저장 재시도 오류: {str(e_retry)}")

            briefing_clip_text = build_briefing_clipboard_text(current_query, intent_data, briefing_res)
            kw_badges_html = "".join([f'<span class="keyword-pill">#{kw}</span>' for kw in keywords])

            r_level = briefing_res.get("risk_level", "중립/유의")
            r_reason = briefing_res.get("risk_reason", "").strip()
            if not r_reason or r_reason == "---":
                r_reason = "사실관계 및 객관적 입증 증빙(계약서, 금융내역 등) 구비 여부에 따라 과세 여부가 갈립니다."

            if "고위험" in r_level:
                risk_tag_html = '<span class="risk-tag risk-tag-high">🔴 과세 리스크: 高 (주의 요망)</span>'
                risk_box_cls = 'risk-badge-box risk-high'
            elif "저위험" in r_level or "안전" in r_level:
                risk_tag_html = '<span class="risk-tag risk-tag-low">🟢 과세 리스크: 低 (비용인정 유력)</span>'
                risk_box_cls = 'risk-badge-box risk-low'
            else:
                risk_tag_html = '<span class="risk-tag risk-tag-medium">🟡 과세 리스크: 中 (증빙보강 필수)</span>'
                risk_box_cls = 'risk-badge-box risk-medium'

            risk_box_html = (
                f'<div class="{risk_box_cls}">'
                f'{risk_tag_html}'
                f'<span style="font-size:0.88rem; font-weight:600; line-height:1.5;">{r_reason}</span>'
                f'</div>'
            )

            situation_summary_str = intent_data.get('situation_summary', core_issue)
            basis_strength = briefing_res.get("basis_strength", "유의 필요")
            basis_rationale = briefing_res.get("basis_rationale", "판례 및 법령 종합 검토 결과")

            if "확정 가능" in basis_strength:
                strength_badge_html = '<span style="background:#DCFCE7; color:#166534; border:1px solid #86EFAC; padding:3px 8px; border-radius:6px; font-weight:700; font-size:0.82rem;">🟢 근거 강도: 확정 가능</span>'
            elif "고위험" in basis_strength:
                strength_badge_html = '<span style="background:#FEE2E2; color:#991B1B; border:1px solid #FCA5A5; padding:3px 8px; border-radius:6px; font-weight:700; font-size:0.82rem;">🔴 근거 강도: 고위험</span>'
            elif "추가확인" in basis_strength:
                strength_badge_html = '<span style="background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; padding:3px 8px; border-radius:6px; font-weight:700; font-size:0.82rem;">⚪ 근거 강도: 추가확인 필요</span>'
            else:
                strength_badge_html = '<span style="background:#FEF3C7; color:#92400E; border:1px solid #FCD34D; padding:3px 8px; border-radius:6px; font-weight:700; font-size:0.82rem;">🟡 근거 강도: 유의 필요</span>'

            strength_box_html = (
                f'<div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; background:#F8FAFC; border:1px solid #E2E8F0; padding:6px 12px; border-radius:6px; margin: 6px 0 10px 0;">'
                f'{strength_badge_html}'
                f'<span style="font-size:0.83rem; color:#334155; font-weight:600;">{basis_rationale}</span>'
                f'</div>'
            )

            s_facts = intent_data.get("structured_facts", {})
            facts_pills_html = (
                f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:8px 12px; margin-bottom:8px;">'
                f'<div style="font-size:0.78rem; font-weight:700; color:#64748B; margin-bottom:4px;">📋 추출된 사실관계 7대 요건</div>'
                f'<div style="display:flex; flex-wrap:wrap; gap:4px; font-size:0.78rem;">'
                f'<span style="background:#EFF6FF; color:#1D4ED8; padding:2px 6px; border-radius:4px;"><b>세목:</b> {s_facts.get("tax_category", detected_tax)}</span>'
                f'<span style="background:#F0FDF4; color:#15803D; padding:2px 6px; border-radius:4px;"><b>거래유형:</b> {s_facts.get("trans_type", "미상")}</span>'
                f'<span style="background:#FAF5FF; color:#7E22CE; padding:2px 6px; border-radius:4px;"><b>상대방:</b> {s_facts.get("counterparty", "미기재")}</span>'
                f'<span style="background:#FEF2F2; color:#B91C1C; padding:2px 6px; border-radius:4px;"><b>금액:</b> {s_facts.get("amount", "미기재")}</span>'
                f'<span style="background:#FFFBEB; color:#B45309; padding:2px 6px; border-radius:4px;"><b>과세기간:</b> {s_facts.get("tax_period", "해당 연도")}</span>'
                f'<span style="background:#F1F5F9; color:#334155; padding:2px 6px; border-radius:4px;"><b>보유증빙:</b> {s_facts.get("evidence_held", "확인 필요")}</span>'
                f'</div>'
                f'</div>'
            )

            missing_facts = intent_data.get("missing_facts", [])
            missing_box_html = ""
            if missing_facts:
                missing_items_li = "".join([f"<li style='margin-bottom:2px;'>{item}</li>" for item in missing_facts])
                missing_box_html = (
                    f'<div style="background:#FFFBEB; border:1px solid #FCD34D; border-left:4px solid #D97706; border-radius:6px; padding:10px 14px; margin: 8px 0 10px 0;">'
                    f'<div style="font-weight:700; color:#B45309; font-size:0.86rem;">⚠️ [핵심 사실관계 추가 확인 필요사항]</div>'
                    f'<ul style="margin: 4px 0 0 16px; padding:0; font-size:0.80rem; color:#78350F;">'
                    f'{missing_items_li}'
                    f'</ul>'
                    f'</div>'
                )

            files_data_list = st.session_state.get("temp_files_data", [])
            file_badge_html = ""
            if files_data_list:
                file_names = ", ".join([f["name"] for f in files_data_list])
                file_badge_html = f'<div style="margin-top:6px; margin-bottom:2px; font-size:0.80rem; color:#005B45; font-weight:700;"><span style="background:#DCFCE7; padding:3px 6px; border-radius:4px; border:1px solid #A7F3D0;">📄 첨부 문서 분석 완료: {file_names}</span></div>'

            briefing_cited_list = briefing_res.get("cited_cases", [])
            briefing_badges_bar = render_direct_basis_badges(briefing_cited_list, "📌 솔루션 핵심 인용 근거")

            briefing_card_html = (
                f'<div class="ai-briefing-card" style="padding:16px 20px; border-radius:10px; margin-bottom:14px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:6px;">'
                f'<div>'
                f'<span class="ai-briefing-tag">✨ CHATGPT ENTERPRISE 맞춤 세무 진단 솔루션</span>'
                f'{file_badge_html}'
                f'<div style="font-size:1.12rem; font-weight:800; color:#0F172A; margin: 6px 0 4px 0;">'
                f'상황 분석: {situation_summary_str}'
                f'</div>'
                f'<div style="font-size:0.83rem; color:#475569; margin-bottom:6px;">'
                f'세목 분류: <b style="color:#005B45;">[{detected_tax}]</b> | 핵심 쟁점: <b>{core_issue}</b>'
                f'</div>'
                f'<div style="margin-bottom:6px;">'
                f'<span style="font-size:0.78rem; color:#64748B; margin-right:4px;">발굴 키워드:</span>'
                f'{kw_badges_html}'
                f'</div>'
                f'</div>'
                f'</div>'
                f'{strength_box_html}'
                f'{facts_pills_html}'
                f'{missing_box_html}'
                f'{risk_box_html}'
                f'{briefing_badges_bar}'
                f'</div>'
            )

            # -----------------------------------------------------------------
            # [오른쪽 단 순서 a] 상단 요약 바 (발굴 판례 건수, 엑셀 다운로드 버튼, 새 상황 질문 버튼)
            # -----------------------------------------------------------------
            col_count, col_excel, col_home = st.columns([4.2, 2.0, 1.8], vertical_alignment="center")
            with col_count:
                tax_filter_str = f" · 세목: <b style='color:#005B45;'>{current_tax_type}</b>" if current_tax_type != "전체" else f" · 세목: <b style='color:#005B45;'>{detected_tax}</b>"
                top_err_cat = search_res.get("error_category")
                if total_cnt == 0 and top_err_cat and top_err_cat != "검색 결과 없음":
                    quality_summary_html = f"<span style='background:#FEE2E2; color:#991B1B; border:1px solid #FCA5A5; padding:2px 7px; border-radius:12px; font-size:0.76rem; font-weight:700;'>⚠️ {top_err_cat}</span>"
                else:
                    quality_summary_html = (
                        f"<span style='background:#EFF8FF; color:#175CD3; border:1px solid #B2DDFF; padding:2px 7px; border-radius:12px; font-size:0.76rem; font-weight:700;'>🎯 직접근거 {direct_basis_count}건</span> "
                        f"<span style='background:#F8F9FA; color:#344054; border:1px solid #D0D5DD; padding:2px 7px; border-radius:12px; font-size:0.76rem; font-weight:700;'>보조 {support_basis_count}건</span> "
                        f"<span style='background:#F4F3FF; color:#5925DC; border:1px solid #D9D6FE; padding:2px 7px; border-radius:12px; font-size:0.76rem; font-weight:700;'>참고 {reference_basis_count}건</span>"
                    )
                st.markdown(
                    f"<div style='font-size:0.90rem; color:#1E293B; font-weight:700;'>🏛️ 발굴 판례·예규 <b>{total_cnt:,}건</b> "
                    f"(솔루션 인용 <b>{len(briefing_res.get('cited_cases', []))}건</b>{tax_filter_str})</div>"
                    f"<div style='margin-top:4px; display:flex; gap:5px; flex-wrap:wrap; align-items:center;'>{quality_summary_html}</div>",
                    unsafe_allow_html=True
                )
            
            with col_excel:
                export_list = list(briefing_res.get("cited_cases", [])) + list(results)
                if export_list:
                    normalized_export = []
                    for e in export_list:
                        if isinstance(e, dict):
                            normalized_export.append({
                                "tax_category": e.get("tax_category", e.get("tax_type", detected_tax)),
                                "court": e.get("court", e.get("Court", e.get("org", "-"))),
                                "case_number": e.get("case_number", e.get("CaseNumber", e.get("number", "-"))),
                                "date": e.get("date", e.get("Date", "-")),
                                "title": e.get("title", e.get("Title", "-")),
                                "basis_type": e.get("basis_type", ""),
                                "relevance_score": e.get("relevance_score", ""),
                                "match_reason": e.get("match_reason", ""),
                                "matched_keywords": ", ".join(e.get("matched_keywords", []) or []),
                                "source": e.get("source", e.get("Source", "국가법령정보센터")),
                                "link": e.get("link", e.get("Link", ""))
                            })
                    if normalized_export:
                        df_export = pd.DataFrame(normalized_export)[["tax_category", "court", "case_number", "date", "title", "basis_type", "relevance_score", "match_reason", "matched_keywords", "source", "link"]]
                        df_export.columns = ["세목", "기관/법원", "사건번호", "선고일자", "사건명(판결요지)", "근거유형", "관련도점수", "매칭사유", "매칭키워드", "출처", "원문링크"]
                        df_export = df_export.drop_duplicates(subset=["사건번호"])
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df_export.to_excel(writer, index=False, sheet_name='판례검색결과')
                        
                        st.download_button(
                            label="📥 판례 엑셀 다운",
                            data=buffer.getvalue(),
                            file_name=f"세무판례_{current_tax_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            key=f"dl_excel_{hash(current_query)}"
                        )


            with col_home:
                if st.button("🔄 새 질문", key="btn_reset_home", use_container_width=True, help="초기 화면으로 돌아가기"):
                    st.session_state["search_input"] = ""
                    st.session_state["selected_tax_type"] = "전체"
                    st.session_state["input_version"] = st.session_state.get("input_version", 0) + 1
                    for k in list(st.session_state.keys()):
                        if k.startswith("analysis_snapshot_") or k.startswith("search_") or k.startswith("intent_") or k.startswith("briefing_") or k.startswith("kw_") or k.startswith("chat_"):
                            del st.session_state[k]
                    st.rerun()

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            render_search_debug_panel(search_res, intent_data, active_keywords)

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            if results and direct_basis_count == 0:
                st.markdown("""
                <div style="background:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #D97706; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                    <div style="font-size:0.88rem; font-weight:800; color:#92400E;">⚠️ 직접 적용 가능한 공식 근거가 아직 약합니다</div>
                    <div style="font-size:0.82rem; color:#78350F; line-height:1.5; margin-top:3px;">
                        현재 결과는 보조근거 또는 참고자료 중심입니다. 결론을 확정하기 전 검색 키워드를 추가하거나 예규·법령 조문을 추가 확인하는 것이 좋습니다.
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # [오른쪽 단 순서 a-2] 🚨 계약서 세무 독소조항 진단 & 권고 수정 가이드 (Stage 4)
            # -----------------------------------------------------------------
            render_contract_risk_review(intent_data, current_query)

            # -----------------------------------------------------------------
            # [오른쪽 단 순서 b] 📊 AI 세무전문가 종합 실무 의견서 (briefing_card_html + 4개 탭)
            # -----------------------------------------------------------------
            st.markdown('<div id="briefing-conclusion" style="scroll-margin-top: 80px;"></div>', unsafe_allow_html=True)
            st.markdown(briefing_card_html, unsafe_allow_html=True)

            briefing_case_id = f"briefing_{abs(hash(current_query))}"
            is_briefing_saved = briefing_case_id in st.session_state["saved_cases"]
            
            col_br_title, col_br_save, col_br_copy = st.columns([3.5, 1.4, 2.1], vertical_alignment="center")
            with col_br_title:
                st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#005B45;'>📊 AI 세무전문가 종합 실무 의견서</div>", unsafe_allow_html=True)
            with col_br_save:
                btn_save_br_label = "승인 후 자동 저장"
                if st.button(btn_save_br_label, key=f"btn_save_{briefing_case_id}", use_container_width=True,
                             disabled=True, help="지식 승인센터에서 승인하면 승인된 자료에 자동 반영됩니다."):
                    if is_briefing_saved:
                        del st.session_state["saved_cases"][briefing_case_id]
                        save_saved_cases(st.session_state["saved_cases"])
                        st.toast("세무검토 사례가 보관함에서 삭제되었습니다.", icon="🗑️")
                        st.rerun()
                    else:
                        is_dup, dup_msg, dup_id = check_duplicate_case(st.session_state["saved_cases"], None, current_query, briefing_case_id)
                        if is_dup:
                            st.warning(f"⚠️ {dup_msg}")
                        
                        real_refs = []
                        for c in briefing_res.get("cited_cases", []):
                            if c.get("case_number"):
                                real_refs.append({
                                    "type": "판례/예규",
                                    "title": c.get("title", ""),
                                    "case_number": c.get("case_number", ""),
                                    "court": c.get("court", ""),
                                    "date": c.get("date", ""),
                                    "link": c.get("link", ""),
                                    "source": c.get("source", "국가법령정보센터"),
                                    "prec_id": c.get("prec_id", ""),
                                    "basis_type": c.get("basis_type", ""),
                                    "relevance_score": c.get("relevance_score", ""),
                                    "match_reason": c.get("match_reason", ""),
                                    "matched_keywords": c.get("matched_keywords", [])
                                })
                        
                        saved_br_item = {
                            "case_id": briefing_case_id,
                            "title": f"[{detected_tax}] {intent_data.get('situation_summary', current_query[:40])}",
                            "tax_category": detected_tax,
                            "issue_tags": [detected_tax] + [kw for kw in keywords[:4]],
                            "risk_level": briefing_res.get("risk_level", "중립/유의"),
                            "review_status": "검토중",
                            "user_query": current_query,
                            "facts_summary": intent_data.get("structured_facts", {}),
                            "legal_references": real_refs,
                            "ai_opinion": {
                                "basis_strength": briefing_res.get("basis_strength", "유의 필요"),
                                "basis_rationale": briefing_res.get("basis_rationale", "판례 및 법령 종합 검토"),
                                "conclusion": briefing_res.get("conclusion", ""),
                                "case_comparison": briefing_res.get("case_comparison", ""),
                                "checklist": briefing_res.get("checklist", "")
                            },
                            "basis_quality": {
                                "direct_basis_count": direct_basis_count,
                                "support_basis_count": support_basis_count,
                                "reference_basis_count": reference_basis_count,
                                "notice": "직접근거 후보는 거래대상과 세무쟁점이 동시에 매칭된 공식자료입니다."
                            },
                            "user_memo": "",
                            "created_at": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
                            "updated_at": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
                            "case_number": f"TAX-{pd.Timestamp.now().strftime('%m%d%H%M')}",
                            "date": pd.Timestamp.now().strftime('%Y-%m-%d'),
                            "court": "ChatGPT Enterprise 세무검토",
                            "source": "CJ프레시웨이 TAX AI",
                            "prec_id": briefing_case_id,
                            "link": "",
                            "saved_at": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
                            "ai_summary": {
                                "legal_basis": briefing_res.get('conclusion', ''),
                                "tax_office_view": "과세관청 입증 책임 및 법령 요건 엄격 적용",
                                "taxpayer_view": "거래의 실질 및 합리적 경제 행위 소명",
                                "court_decision": briefing_res.get('case_comparison', ''),
                                "actionable_takeaway": briefing_res.get('checklist', '')
                            }
                        }
                        st.session_state["saved_cases"][briefing_case_id] = saved_br_item
                        save_saved_cases(st.session_state["saved_cases"])
                        st.toast("📁 세무검토 사례 카드가 보관함에 저장되었습니다!", icon="⭐")
                        st.rerun()
            with col_br_copy:
                render_copy_button(briefing_clip_text, f"cp_{briefing_case_id}")

            st.markdown('<div id="briefing-conclusion" style="scroll-margin-top: 80px;"></div>', unsafe_allow_html=True)
            tab_c_res, tab_c_basis, tab_c_action, tab_c_missing = st.tabs([
                "⚖️ 1. 핵심 결론",
                "🏛️ 2. 판단 근거 & 판례",
                "💼 3. 실무 처리 & 증빙",
                "⚠️ 4. 추가 확인 필요사항"
            ])

            with tab_c_res:
                conclusion_raw = briefing_res.get('conclusion', '')
                cited_list = briefing_res.get("cited_cases", [])
                conclusion_html = inject_case_deeplinks(format_notion_content(conclusion_raw), cited_list)
                conclusion_badges_bar = render_direct_basis_badges(cited_list, "📌 본 결론 직접 인용 근거")
                card_html = (
                    '<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #005B45; border-radius:8px; padding:16px 20px; margin-bottom:10px;">'
                    '<div style="font-size:0.92rem; font-weight:700; color:#005B45; margin-bottom:6px;">⚖️ 세무 리스크 진단 및 핵심 결론 요약</div>'
                    f'<div style="font-size:0.88rem; line-height:1.65; color:#1E293B;">{conclusion_html}</div>'
                    f'{conclusion_badges_bar}'
                    '</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                
                if "일시적" in conclusion_raw or briefing_res.get("error"):
                    if st.button("🔄 AI 검토의견서 다시 생성하기", key=f"btn_retry_briefing_{abs(hash(current_query))}", type="primary"):
                        # 캐시에서 지우고 즉시 재생성
                        for k in list(st.session_state.keys()):
                            if (k.startswith("briefing_") or k.startswith("analysis_snapshot_")) and str(hash(current_query)) in k:
                                del st.session_state[k]
                        st.rerun()

            with tab_c_basis:
                case_comp_raw = briefing_res.get('case_comparison', '')
                cited_list = briefing_res.get("cited_cases", [])
                case_comp_html = inject_case_deeplinks(format_notion_content(case_comp_raw), cited_list)
                basis_badges_bar = render_direct_basis_badges(cited_list, "📌 비교 검토 핵심 근거")
                basis_card_html = (
                    '<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #003876; border-radius:8px; padding:16px 20px; margin-bottom:10px;">'
                    '<div style="font-size:0.92rem; font-weight:700; color:#003876; margin-bottom:6px;">🏛️ 관련 실제 판례 법리 비교 및 법원 판단 취지</div>'
                    f'<div style="font-size:0.88rem; line-height:1.65; color:#1E293B;">{case_comp_html}</div>'
                    f'{basis_badges_bar}'
                    '</div>'
                )
                st.markdown(basis_card_html, unsafe_allow_html=True)

            with tab_c_action:
                checklist_html = format_notion_content(briefing_res.get('checklist', ''))
                action_card_html = (
                    '<div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #B54708; border-radius:8px; padding:16px 20px; margin-bottom:10px;">'
                    '<div style="font-size:0.92rem; font-weight:700; color:#B54708; margin-bottom:6px;">💼 실무자 필수 증빙 체크리스트 & 행동 수칙</div>'
                    f'<div style="font-size:0.88rem; line-height:1.65; color:#1E293B;">{checklist_html}</div>'
                    '</div>'
                )
                st.markdown(action_card_html, unsafe_allow_html=True)

            with tab_c_missing:
                missing_facts_list = intent_data.get("missing_facts", [])
                if missing_facts_list:
                    missing_items_html = "".join([f"<li style='margin-bottom:4px;'>{it}</li>" for it in missing_facts_list])
                else:
                    missing_items_html = "<li>추가 누락 사실관계 없음 (기본 핵심 요건 충족)</li>"
                missing_card_html = (
                    '<div style="background:#FFFBEB; border:1px solid #FEDF89; border-left:4px solid #B54708; border-radius:8px; padding:16px 20px; margin-bottom:10px;">'
                    '<div style="font-size:0.92rem; font-weight:700; color:#B54708; margin-bottom:6px;">⚠️ 과세관청 처분 대비 핵심 사실관계 추가 확인사항</div>'
                    '<div style="font-size:0.84rem; color:#78350F; margin-bottom:6px;">최종 결론 확정 및 세무조사 입증을 위해 다음 사항의 객관적 증빙을 추가 확인하십시오:</div>'
                    f'<ul style="margin:0 0 0 16px; padding:0; font-size:0.84rem; color:#78350F; line-height:1.6;">{missing_items_html}</ul>'
                    '</div>'
                )
                st.markdown(missing_card_html, unsafe_allow_html=True)

            save_rec_id = _analysis.get("save_rec_id")
            if save_rec_id:
                with st.expander("💬 이 검토 결과가 실무에 도움이 되었나요?", expanded=False):
                    st.caption("평가는 검색 품질 개선과 회계팀 검토 우선순위에 반영됩니다. ‘수정 필요’는 구체적인 사유를 남겨주세요.")
                    with st.form(key=f"feedback_form_{save_rec_id}", clear_on_submit=False):
                        feedback_label = st.radio(
                            "평가",
                            ["선택하세요", "👍 도움됨", "🛠️ 수정 필요"],
                            horizontal=True,
                            key=f"feedback_rating_{save_rec_id}",
                        )
                        feedback_note = st.text_area(
                            "의견",
                            placeholder="어떤 부분이 유용했거나 수정되어야 하는지 알려주세요.",
                            height=80,
                            key=f"feedback_note_{save_rec_id}",
                        )
                        feedback_submit = st.form_submit_button("피드백 저장", use_container_width=True)
                    if feedback_submit:
                        rating = (
                            "helpful" if feedback_label == "👍 도움됨"
                            else "needs_correction" if feedback_label == "🛠️ 수정 필요"
                            else ""
                        )
                        if not rating:
                            st.warning("평가를 먼저 선택해 주세요.")
                        elif rating == "needs_correction" and not feedback_note.strip():
                            st.warning("수정이 필요한 부분을 간단히 적어주세요.")
                        else:
                            try:
                                from repositories.review_repo import get_review_repository
                                if get_review_repository().set_feedback(
                                    save_rec_id, rating, "jongmin.park1@cj.net", feedback_note
                                ):
                                    st.toast("피드백을 저장했습니다.", icon="✅")
                                else:
                                    st.error("피드백을 저장하지 못했습니다.")
                            except ValueError as exc:
                                st.warning(str(exc))

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # [오른쪽 단 순서 c] 📑 목적별 3대 세무 보고서 출력 (expander)
            # -----------------------------------------------------------------
            with st.expander("📑 목적별 3대 세무 보고서 출력 및 다운로드 (클릭하여 펼치기)", expanded=False):
                st.markdown("<div style='font-size:0.86rem; color:#64748B; margin-bottom:8px;'>경영진 보고용, 실무 회신용, 감사 방어용 보고서를 원클릭으로 복사/다운로드 할 수 있습니다.</div>", unsafe_allow_html=True)
                
                rep_summary_txt = format_report_summary(intent_data, briefing_res)
                rep_opinion_txt = format_report_opinion(intent_data, briefing_res)
                rep_detailed_txt = format_report_detailed(intent_data, briefing_res)

                tab_rep_sum, tab_rep_op, tab_rep_det = st.tabs(["📊 1. 요약형 (경영진 1분 보고)", "📝 2. 검토의견형 (팀내 실무 회신)", "📑 3. 상세검토형 (세무조사 방어/감사용)"])

                with tab_rep_sum:
                    col_rs_c, col_rs_d = st.columns([1.5, 1.5], vertical_alignment="center")
                    with col_rs_c:
                        render_copy_button(rep_summary_txt, f"cp_rep_sum_{hash(current_query)}")
                    with col_rs_d:
                        st.download_button(
                            label="💾 요약형 .txt 다운",
                            data=rep_summary_txt.encode("utf-8"),
                            file_name=f"CJ프레시웨이_세무요약보고서_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
                            mime="text/plain",
                            use_container_width=True,
                            key=f"dl_rep_sum_{hash(current_query)}"
                        )
                    st.code(rep_summary_txt, language="markdown")

                with tab_rep_op:
                    col_ro_c, col_ro_d = st.columns([1.5, 1.5], vertical_alignment="center")
                    with col_ro_c:
                        render_copy_button(rep_opinion_txt, f"cp_rep_op_{hash(current_query)}")
                    with col_ro_d:
                        st.download_button(
                            label="💾 검토의견형 .txt 다운",
                            data=rep_opinion_txt.encode("utf-8"),
                            file_name=f"CJ프레시웨이_세무검토의견서_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
                            mime="text/plain",
                            use_container_width=True,
                            key=f"dl_rep_op_{hash(current_query)}"
                        )
                    st.code(rep_opinion_txt, language="markdown")

                with tab_rep_det:
                    col_rd_c, col_rd_d = st.columns([1.5, 1.5], vertical_alignment="center")
                    with col_rd_c:
                        render_copy_button(rep_detailed_txt, f"cp_rep_det_{hash(current_query)}")
                    with col_rd_d:
                        st.download_button(
                            label="💾 상세검토형 .txt 다운",
                            data=rep_detailed_txt.encode("utf-8"),
                            file_name=f"CJ프레시웨이_세무심층검토보고서_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
                            mime="text/plain",
                            use_container_width=True,
                            key=f"dl_rep_det_{hash(current_query)}"
                        )
                    st.code(rep_detailed_txt, language="markdown")

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # [오른쪽 단 순서 d] ⚖️ 유사 판례 비교표 (expander)
            # -----------------------------------------------------------------
            with st.expander("⚖️ 유사 판례 비교표 및 심층 법리 분석 (클릭하여 펼치기)", expanded=False):
                high_ranked_results = [it for it in results if it.get("is_high_relevance", False) or _safe_relevance_score(it) >= 50]
                if not high_ranked_results:
                    high_ranked_results = results[:5]
                comparison_pool = list(briefing_res.get("cited_cases", [])) + high_ranked_results
                render_case_comparison_table(
                    pool_cases=comparison_pool,
                    user_query=current_query,
                    facts_summary=intent_data.get("structured_facts", {}),
                    table_id_prefix="search_main_comp"
                )

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # [오른쪽 단 순서 e-1] 📌 솔루션 인용 핵심 판례·예규 (항상 펼쳐진 독립 영역 & 딥링크 타겟)
            # -----------------------------------------------------------------
            cited_cases = briefing_res.get("cited_cases", [])
            if cited_cases:
                unverified_cnt = briefing_res.get("unverified_count", 0)
                unverified_banner = ""
                if unverified_cnt > 0:
                    unverified_banner = f"""
                    <div style="background:#FFFBEB; border:1.5px solid #FDE68A; border-left:4px solid #D97706; border-radius:6px; padding:10px 14px; margin-bottom:10px; font-size:0.80rem; color:#92400E;">
                        <b>🛡️ 판례 인용 신뢰성 검증기 작동</b>: AI가 제안한 판례 중 <b>{unverified_cnt}건</b>은 이번 국가법령정보센터 실시간 검색 결과 풀에서 확인되지 않아 사건번호 표시를 안전하게 배제하였습니다. (아래 목록은 100% 실존하는 검증 판례입니다)
                    </div>
                    """

                st.markdown(f"""
                {unverified_banner}
                <div style="background:#FFFFFF; border:1.5px solid #CBD5E1; border-left:4px solid #005B45; border-radius:10px; padding:14px 18px; margin-bottom:12px; margin-top:14px; box-shadow:0 2px 6px rgba(0,0,0,0.03);">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:1.15rem;">📌</span>
                            <span style="font-size:0.98rem; font-weight:800; color:#0F172A;">솔루션 인용 핵심 판례·예규 ({len(cited_cases)}건)</span>
                            <span style="font-size:0.75rem; background:#F0FDF4; color:#005B45; border:1px solid #86EFAC; padding:2px 8px; border-radius:12px; font-weight:700;">인터랙티브 딥링크 연동</span>
                        </div>
                        <div style="font-size:0.80rem; color:#64748B;">
                            상단 의견서의 <span style="background:#FEF08A; color:#854D0E; padding:1px 6px; border-radius:8px; font-weight:700;">🔍 사건번호</span>를 클릭하면 해당 판례로 즉시 스크롤 이동합니다
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for c_idx, c_item in enumerate(cited_cases):
                    c_no = (c_item.get("case_number") or "").strip()
                    c_slug = re.sub(r'\s+', '_', c_no) if c_no else f"case_{c_idx}"
                    c_summary = (c_item.get("summary") or c_item.get("core_point") or c_item.get("title") or "").strip()

                    # 1) 스크롤 타겟 앵커 태그 (인덱스 ID 및 슬러그 ID 동시 지원)
                    st.markdown(f'<div id="case-anchor-{c_idx}" style="scroll-margin-top: 80px;"></div><div id="case-{c_slug}" style="scroll-margin-top: 80px;"></div>', unsafe_allow_html=True)

                    # 2) 복귀 링크 및 원문 하이라이트 박스
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px; margin-bottom:4px;">
                        <div style="font-size:0.82rem; font-weight:700; color:#005B45;">
                            🎯 [인용 근거 #{c_idx+1}] 사건번호: <b>{c_no if c_no else c_item.get('title', '')}</b>
                        </div>
                        <a href="#briefing-conclusion" target="_self" onclick="document.getElementById('briefing-conclusion')?.scrollIntoView({{behavior:'smooth'}}); return true;" style="font-size:0.75rem; color:#64748B; text-decoration:none; padding:2px 8px; border:1px solid #CBD5E1; border-radius:6px; background:#F8FAFC; transition:all 0.2s;">
                            ⬆ 의견서 본문으로
                        </a>
                    </div>
                    <div style="background-color: #FEF9C3; border-left: 4px solid #EAB308; padding: 12px; border-radius: 4px; font-size: 0.85rem; line-height: 1.6; color: #334155; margin-bottom: 8px;">
                        <div style="font-weight:700; color:#854D0E; font-size:0.80rem; margin-bottom:4px;">💡 AI 리포트 인용 핵심 요약 & 판단 근거:</div>
                        {format_notion_content(c_summary)}
                    </div>
                    """, unsafe_allow_html=True)

                    # 3) 판례 카드 렌더링
                    render_case_card(c_item, c_idx, prefix="cited")

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background:#F8FAFC; border:1.5px dashed #CBD5E1; border-left:4px solid #94A3B8; border-radius:10px; padding:14px 18px; margin-bottom:12px; margin-top:14px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:1.15rem;">📌</span>
                            <span style="font-size:0.98rem; font-weight:800; color:#334155;">솔루션 인용 핵심 판례·예규 (0건)</span>
                            <span style="font-size:0.75rem; background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; padding:2px 8px; border-radius:12px; font-weight:700;">직접 인용 판례 없음</span>
                        </div>
                    </div>
                    <div style="font-size:0.83rem; color:#64748B; margin-top:6px; line-height:1.5;">
                        💡 <b>사실관계 직접 일치 판례 부재</b>: 이번 질의의 구체적 사실관계와 직접적으로 부합하는 판례가 없어 본문 인용 판례를 0건으로 판정하였습니다. 하단의 전체 검색 결과 목록에서 유관 참고 자료를 확인하실 수 있습니다.
                    </div>
                </div>
                <div style='height: 12px;'></div>
                """, unsafe_allow_html=True)

            # -----------------------------------------------------------------
            # [오른쪽 단 순서 e-2] ⚖️ 국가법령 공식 DB 검색 결과 및 6대 근거버킷 탐색
            # -----------------------------------------------------------------
            st.markdown(f"#### ⚖️ 국가법령 공식 DB 판례·해석례 ({total_cnt:,}건)")

            # 1. 6대 근거버킷 카운트 집계 (상단 통계 바와 100% 일치하도록 단일 기준 적용)
            direct_cnt = direct_basis_count
            similar_cnt = len([it for it in results if it.get("basis_bucket") == "similar_basis"])
            risk_cnt = len([it for it in results if it.get("basis_bucket") == "risk_basis"])
            evidence_cnt = len([it for it in results if it.get("basis_bucket") == "evidence_basis"])
            statute_cnt = len([it for it in results if it.get("basis_bucket") == "statute_or_admin_basis"])
            weak_cnt = len([it for it in results if it.get("basis_bucket") == "weak_reference"])

            # 2. 검색 관점 선택 바 (Perspective Toggle)
            st.markdown("<div style='font-size:0.79rem; color:#475569; font-weight:700; margin-bottom:4px;'>🎯 검색 관점 선택 (정렬 기준)</div>", unsafe_allow_html=True)
            persp_options = [
                "🎯 직접근거 우선",
                "🔴 과세리스크 우선",
                "🛡️ 납세자 방어 우선",
                "📜 예규·해석례 우선",
                "⏱️ 최신 선례 우선"
            ]
            persp_key = f"persp_toggle_{hash(current_query)}"
            selected_persp = st.pills(
                "검색 관점 선택",
                options=persp_options,
                default="🎯 직접근거 우선",
                key=persp_key,
                selection_mode="single",
                label_visibility="collapsed"
            ) or "🎯 직접근거 우선"

            # 3. 6대 근거버킷 필터 바
            st.markdown("<div style='font-size:0.79rem; color:#475569; font-weight:700; margin-top:8px; margin-bottom:4px;'>📂 6대 근거 분류 필터</div>", unsafe_allow_html=True)
            bucket_options = [f"전체 ({len(results)})"]
            if direct_cnt: bucket_options.append(f"🎯 직접근거 ({direct_cnt})")
            if similar_cnt: bucket_options.append(f"🔄 유사근거 ({similar_cnt})")
            if risk_cnt: bucket_options.append(f"🔴 과세리스크 ({risk_cnt})")
            if evidence_cnt: bucket_options.append(f"📑 증빙·입증 ({evidence_cnt})")
            if statute_cnt: bucket_options.append(f"📜 예규·해석례 ({statute_cnt})")
            if weak_cnt: bucket_options.append(f"📎 단순참고 ({weak_cnt})")

            bucket_key = f"bucket_pills_{hash(current_query)}"
            selected_bucket_label = st.pills(
                "근거 분류 필터",
                options=bucket_options,
                default=f"전체 ({len(results)})",
                key=bucket_key,
                selection_mode="single",
                label_visibility="collapsed"
            ) or f"전체 ({len(results)})"

            # 4. 필터링 및 관점별 정렬 적용
            filtered_cases = list(results)
            if "직접근거" in selected_bucket_label:
                filtered_cases = [it for it in filtered_cases if it.get("basis_bucket") == "direct_basis"]
            elif "유사근거" in selected_bucket_label:
                filtered_cases = [it for it in filtered_cases if it.get("basis_bucket") == "similar_basis"]
            elif "과세리스크" in selected_bucket_label:
                filtered_cases = [it for it in filtered_cases if it.get("basis_bucket") == "risk_basis"]
            elif "증빙" in selected_bucket_label:
                filtered_cases = [it for it in filtered_cases if it.get("basis_bucket") == "evidence_basis"]
            elif "예규" in selected_bucket_label:
                filtered_cases = [it for it in filtered_cases if it.get("basis_bucket") == "statute_or_admin_basis"]
            elif "단순참고" in selected_bucket_label:
                filtered_cases = [it for it in filtered_cases if it.get("basis_bucket") == "weak_reference"]

            # 정렬
            if selected_persp == "🎯 직접근거 우선":
                filtered_cases = sorted(filtered_cases, key=lambda x: (x.get("basis_bucket") == "direct_basis", _safe_relevance_score(x)), reverse=True)
            elif selected_persp == "🔴 과세리스크 우선":
                filtered_cases = sorted(filtered_cases, key=lambda x: (x.get("basis_bucket") == "risk_basis", x.get("has_losing_signal", False), _safe_relevance_score(x)), reverse=True)
            elif selected_persp == "🛡️ 납세자 방어 우선":
                filtered_cases = sorted(filtered_cases, key=lambda x: (x.get("has_winning_signal", False), x.get("basis_bucket") == "direct_basis", _safe_relevance_score(x)), reverse=True)
            elif selected_persp == "📜 예규·해석례 우선":
                filtered_cases = sorted(filtered_cases, key=lambda x: (x.get("basis_bucket") == "statute_or_admin_basis", _safe_relevance_score(x)), reverse=True)
            elif selected_persp == "⏱️ 최신 선례 우선":
                filtered_cases = sorted(filtered_cases, key=lambda x: (str(x.get("date", "")), _safe_relevance_score(x)), reverse=True)

            # 5. 대화형 키워드/쟁점 보정 바
            with st.expander("🛠️ 쟁점 태그 보정 및 검색 조건 조정", expanded=False):
                active_kw_display = ", ".join(active_keywords) if active_keywords else "선택 없음"
                st.markdown(f"<div style='font-size:0.80rem; color:#475569; margin-bottom:6px;'>현재 검색 키워드: <b>{active_kw_display}</b></div>", unsafe_allow_html=True)
                chosen_pills = st.pills(
                    "판례 키워드 태그",
                    options=available_keywords,
                    default=active_keywords,
                    selection_mode="multi",
                    key=kw_pills_key,
                    label_visibility="collapsed"
                )
                with st.form(key=f"add_kw_form_{hash(current_query)}_{kw_ver}", clear_on_submit=True):
                    c_in, c_btn = st.columns([4.2, 1.2], vertical_alignment="center")
                    with c_in:
                        new_kw_val = st.text_input("새 키워드 입력", placeholder="+ 추가할 검색 키워드 직접 입력 (예: 부당행위계산)", label_visibility="collapsed")
                    with c_btn:
                        btn_add_kw = st.form_submit_button("➕ 키워드 추가", use_container_width=True)
                    if btn_add_kw and new_kw_val.strip():
                        clean_new = new_kw_val.strip()
                        if clean_new not in available_keywords and clean_new not in STOP_KEYWORDS:
                            available_keywords.append(clean_new)
                            st.session_state[kw_pool_key] = available_keywords
                        cur_active = list(st.session_state.get(kw_active_key, available_keywords))
                        if clean_new not in cur_active and clean_new not in STOP_KEYWORDS:
                            cur_active.append(clean_new)
                        st.session_state[kw_active_key] = cur_active
                        st.session_state[kw_ver_key] = kw_ver + 1
                        st.rerun()

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            # 6. 판례 카드 렌더링
            if not filtered_cases:
                if total_cnt == 0:
                    api_err_type = search_res.get("error_type")
                    api_err_cat = search_res.get("error_category") or ""
                    api_err_msg = search_res.get("error") or ""

                    if api_err_type == "AUTH_ERROR" or "인증" in api_err_cat:
                        st.markdown(f"""
                        <div style="background:#FEF2F2; border:1.5px solid #FCA5A5; border-left:5px solid #DC2626; border-radius:10px; padding:18px 20px; margin-top:16px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
                            <div style="display:flex; align-items:flex-start; gap:12px;">
                                <span style="font-size:1.6rem; line-height:1.2;">🔑</span>
                                <div style="flex:1;">
                                    <div style="font-size:1.02rem; font-weight:800; color:#991B1B; margin-bottom:6px;">
                                        [API 인증 오류] 국가법령정보센터 Open API 인증 및 권한 확인 필요
                                    </div>
                                    <div style="font-size:0.86rem; color:#7F1D1D; line-height:1.6;">
                                        법제처 국가법령정보센터(law.go.kr) Open API 호출 인증키(OC)에 오류가 있거나 해당 서비스 신청이 승인되지 않았습니다.<br>
                                        단순 검색 결과 없음이 아니라 <b>인증 권한 오류</b>로 인해 데이터를 조회할 수 없는 상태입니다.
                                    </div>
                                    <div style="background:#FFFFFF; border:1px solid #FECACA; border-radius:6px; padding:10px 14px; margin-top:10px; font-size:0.82rem; color:#450A0A;">
                                        <b>🛠️ 확인 및 조치 방법:</b><br>
                                        1. <code>.env</code> 파일의 <code>LAW_API_KEY</code>가 올바르게 입력되어 있는지 확인해 주세요.<br>
                                        2. 국가법령정보센터 Open API 관리 사이트에서 <b>판례(prec) 및 행정해석례(expc)</b> 서비스가 정상 신청/승인되어 있는지 확인해 주세요.
                                        {f'<div style="margin-top:6px; color:#B91C1C; font-weight:600;"><b>상세 오류:</b> {api_err_msg}</div>' if api_err_msg else ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif api_err_type == "NETWORK_ERROR" or "네트워크" in api_err_cat:
                        st.markdown(f"""
                        <div style="background:#FFFBEB; border:1.5px solid #FDE68A; border-left:5px solid #D97706; border-radius:10px; padding:18px 20px; margin-top:16px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
                            <div style="display:flex; align-items:flex-start; gap:12px;">
                                <span style="font-size:1.6rem; line-height:1.2;">📡</span>
                                <div style="flex:1;">
                                    <div style="font-size:1.02rem; font-weight:800; color:#92400E; margin-bottom:6px;">
                                        [네트워크 통신 오류] 국가법령정보센터 서버 연결 실패
                                    </div>
                                    <div style="font-size:0.86rem; color:#78350F; line-height:1.6;">
                                        국가법령정보센터(law.go.kr) 서버 응답 지연(Timeout) 또는 일시적인 네트워크 통신 단절이 발생했습니다.<br>
                                        공공 API 서버의 트래픽 과부하 또는 외부 방화벽 설정으로 인해 연결이 지연될 수 있습니다.
                                    </div>
                                    <div style="background:#FFFFFF; border:1px solid #FDE68A; border-radius:6px; padding:10px 14px; margin-top:10px; font-size:0.82rem; color:#451A03;">
                                        <b>🛠️ 확인 및 조치 방법:</b><br>
                                        1. 아래 <b>[🔄 캐시 초기화 후 즉시 재시도]</b> 버튼을 누르거나 상단의 <b>[🚀 AI 세무·판례 심층 분석 시작]</b>을 눌러주세요.<br>
                                        2. 웹 브라우저에서 <a href="https://www.law.go.kr" target="_blank" style="color:#B45309; font-weight:700; text-decoration:underline;">law.go.kr</a> 정상 접속 여부를 확인해 주세요.
                                        {f'<div style="margin-top:6px; color:#B45309; font-weight:600;"><b>상세 오류:</b> {api_err_msg}</div>' if api_err_msg else ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("🔄 캐시 초기화 후 즉시 재시도", key="retry_net_err_btn", use_container_width=True):
                            for k in list(st.session_state.keys()):
                                if k.startswith("analysis_snapshot_") or k.startswith("search_v5_") or k.startswith("intent_v7_") or k.startswith("briefing_v9_"):
                                    del st.session_state[k]
                            st.rerun()
                    elif api_err_type == "PARSE_ERROR" or "형식" in api_err_cat:
                        st.markdown(f"""
                        <div style="background:#F5F3FF; border:1.5px solid #DDD6FE; border-left:5px solid #7C3AED; border-radius:10px; padding:18px 20px; margin-top:16px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
                            <div style="display:flex; align-items:flex-start; gap:12px;">
                                <span style="font-size:1.6rem; line-height:1.2;">📄</span>
                                <div style="flex:1;">
                                    <div style="font-size:1.02rem; font-weight:800; color:#5B21B6; margin-bottom:6px;">
                                        [검색 응답 형식 오류] 법령 데이터 파싱 및 구조 처리 실패
                                    </div>
                                    <div style="font-size:0.86rem; color:#4C1D95; line-height:1.6;">
                                        국가법령정보센터에서 수신된 응답 본문이 표준 XML 형식이 아니거나 서버 점검 HTML 오류 페이지가 반환되었습니다.<br>
                                        특정 검색어의 특수문자 또는 국가법령정보센터 서버의 일시적 점검 시 발생할 수 있습니다.
                                    </div>
                                    <div style="background:#FFFFFF; border:1px solid #DDD6FE; border-radius:6px; padding:10px 14px; margin-top:10px; font-size:0.82rem; color:#2E1065;">
                                        <b>🛠️ 확인 및 조치 방법:</b><br>
                                        검색어에서 따옴표나 특수기호를 줄이시고 키워드를 단순화하여 다시 시도해 주세요.
                                        {f'<div style="margin-top:6px; color:#6D28D9; font-weight:600;"><b>상세 오류:</b> {api_err_msg}</div>' if api_err_msg else ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background:#F8FAFC; border:1.5px solid #E2E8F0; border-left:5px solid #64748B; border-radius:10px; padding:18px 20px; margin-top:16px; box-shadow:0 2px 6px rgba(0,0,0,0.02);">
                            <div style="display:flex; align-items:flex-start; gap:12px;">
                                <span style="font-size:1.6rem; line-height:1.2;">🔍</span>
                                <div style="flex:1;">
                                    <div style="font-size:1.02rem; font-weight:800; color:#1E293B; margin-bottom:6px;">
                                        [검색 결과 없음] 일치하는 공식 판례 및 행정해석례가 없습니다
                                    </div>
                                    <div style="font-size:0.86rem; color:#475569; line-height:1.6;">
                                        국가법령정보센터 Open API 정상 호출을 완료하였으나, 입력하신 사실관계 조건에 부합하는 선례가 DB에 존재하지 않습니다.<br>
                                        (사건 사실관계가 지극히 특수하거나 아직 대법원 판례나 국세청 예규로 확립되지 않은 신종 거래일 수 있습니다.)
                                    </div>
                                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:10px 14px; margin-top:10px; font-size:0.82rem; color:#334155;">
                                        <b>💡 권장 해결 방안:</b><br>
                                        1. 상단의 <b>발굴 키워드(#키워드)</b> 태그를 클릭하여 더 일반적인 단어로 검색 범위를 넓혀보세요.<br>
                                        2. 세목 필터를 <b>전체</b>로 변경하시거나, <b>[📄 AI 문서/계약서 정밀 검토]</b>를 통해 일반 세법 원칙 기반의 해석을 받아보세요.
                                    </div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="notion-block nb-gray" style="margin-top:16px;">
                        <div class="notion-icon">🔍</div>
                        <div class="notion-body">
                            <div class="notion-title">선택하신 분류({selected_bucket_label})에 해당하는 자료가 없습니다</div>
                            전체 검색 결과는 총 <b>{total_cnt:,}건</b> 발굴되었습니다. 위의 다른 근거 분류 태그(예: 전체, 유사근거 등)를 선택하시거나 검색 관점을 변경해 보세요.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                for idx, item in enumerate(filtered_cases):
                    render_case_card(item, idx, prefix=f"bucket_{idx}")
