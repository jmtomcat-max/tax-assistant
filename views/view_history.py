# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무 리서치 & AI 검토 - 검토 기록 전용 화면 (view_history.py)
- 기업 세무 지식자산 아카이브 & 감사 추적(Audit Trail) 대시보드
- 통계 KPI, 실시간 역검색, 다차원 필터, 원클릭 재검토, CSV/TXT 내보내기, 소프트 딜리트(보관) 지원
- st.html()을 사용하여 마크다운 파서 오작동(코드블록 렌더링 버그) 원천 차단
"""
import io
import csv
import streamlit as st
import pandas as pd
from datetime import datetime

from repositories.review_repo import get_review_repository


KNOWLEDGE_STATUS_LABELS = {
    "candidate": "🟡 승인 대기",
    "reviewing": "🔵 검토 중",
    "approved": "🟢 승인 지식",
    "rejected": "🔴 반려",
    "superseded": "⚪ 대체됨",
}


def _needs_freshness_review(record: dict) -> bool:
    """승인 지식이 기준 세법일로부터 1년 이상 지났는지 판단."""
    if record.get("knowledge_status") != "approved":
        return False
    try:
        base_date = datetime.strptime(record.get("applied_tax_base_date", ""), "%Y-%m-%d")
        return (datetime.now() - base_date).days >= 365
    except (TypeError, ValueError):
        return True


def generate_history_csv(records: list) -> str:
    """Excel 호환 (UTF-8-SIG) 검토 기록 CSV 생성"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "검토ID", "최종검토일시", "최초검토일시", "누적검토수", "세목", "리스크등급",
        "검토질의(사실관계)", "핵심쟁점", "AI진단결론요약", "인용판례목록", "지식상태",
        "지식검토자", "지식검토일시", "검토메모", "기준세법", "사용모델"
    ])
    for r in records:
        cases_str = "; ".join([f"{c.get('case_number','')} {c.get('title','')}" for c in r.get("top_cases", [])])
        writer.writerow([
            r.get("id", ""),
            r.get("last_reviewed_at", ""),
            r.get("first_created_at", ""),
            r.get("review_count", 1),
            r.get("tax_category", ""),
            r.get("risk_level", ""),
            r.get("query", "").replace("\n", " "),
            r.get("core_issue", "").replace("\n", " "),
            r.get("briefing_conclusion", "").replace("\n", " "),
            cases_str,
            KNOWLEDGE_STATUS_LABELS.get(r.get("knowledge_status", "candidate"), "승인 대기"),
            r.get("knowledge_reviewed_by", ""),
            r.get("knowledge_reviewed_at", ""),
            r.get("knowledge_review_note", ""),
            r.get("applied_tax_base_date", ""),
            r.get("model_used", "")
        ])
    return output.getvalue()


def generate_history_txt(records: list) -> str:
    """경영지원담당 회계팀 공식 서식의 세무 검토 아카이브 종합 리포트"""
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "[CJ프레시웨이 경영지원담당 회계팀] 세무 검토 기록(Review History) 아카이브 리포트",
        f"· 출력 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"· 총 검토 건수: {len(records)}건",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    for idx, r in enumerate(records, 1):
        lines.append(f"【검토 사례 #{idx}】 [{r.get('tax_category', '조세일반')}] (누적 검토: {r.get('review_count', 1)}회)")
        lines.append(f"• 최종 검토일시: {r.get('last_reviewed_at', '-')} (최초 등록: {r.get('first_created_at', '-')})")
        lines.append(f"• 리스크 등급: {r.get('risk_level', '중립/유의')} | 적용 세법: {r.get('applied_tax_base_date', '2026-01-01')} 기준 | 모델: {r.get('model_used', '')}")
        lines.append(f"• 지식 승인 상태: {KNOWLEDGE_STATUS_LABELS.get(r.get('knowledge_status', 'candidate'), '승인 대기')} | 검토자: {r.get('knowledge_reviewed_by', '-') or '-'} | 검토일: {r.get('knowledge_reviewed_at', '-') or '-'}")
        lines.append(f"• 검토 대상 질문: {r.get('query', '')}")
        if r.get('core_issue'):
            lines.append(f"• 핵심 쟁점: {r.get('core_issue')}")
        if r.get('active_keywords'):
            lines.append(f"• 검색 키워드: {', '.join(r.get('active_keywords'))}")
        if r.get('risk_reason'):
            lines.append(f"• 리스크 판단 근거: {r.get('risk_reason')}")
        lines.append(f"• AI 진단 결론:\n  {r.get('briefing_conclusion', '').strip()}")
        
        checklist = r.get("checklist", [])
        if checklist:
            lines.append("• 과세관청 입증 대비 필수 증빙 체크리스트:")
            for chk in checklist:
                lines.append(f"  [ ] {chk}")

        case_comp = r.get("case_comparison", "")
        if case_comp:
            lines.append(f"• 유사/상충 판례 비교 분석:\n  {case_comp.strip()}")

        top_cases = r.get("top_cases", [])
        if top_cases:
            lines.append("• 주요 인용 판례/예규:")
            for c in top_cases:
                lines.append(f"  - {c.get('case_number', '')} {c.get('title', '')} ({c.get('court', '')} {c.get('date', '')}, 관련도: {c.get('relevance_score', 0)}%)")
                if c.get('summary'):
                    lines.append(f"    요지: {c.get('summary')}")
        lines.append("──────────────────────────────────────────────────────────────────\n")
    lines.append("* 본 문서는 CJ프레시웨이 세무 리서치 & AI 검토 시스템에서 자동 추출된 공식 검토 이력입니다.")
    return "\n".join(lines)


def render_history_view():
    """AI 답변 후보를 검토하고 승인 지식으로 승격하는 대시보드."""
    repo = get_review_repository()
    kpi = repo.get_kpi_stats()
    status_counts = kpi.get("knowledge_status_counts", {})

    # 1. 헤더 영역 (st.html 사용으로 마크다운 파서 간섭 차단)
    header_html = """
    <div style="padding: 10px 0 16px 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 18px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-size:0.75rem; font-weight:700; color:#003876; background:#EFF8FF; border:1px solid #B2DDFF; padding:2px 8px; border-radius:4px;">
                    CJ FRESHWAY · TAX KNOWLEDGE BASE
                </span>
                <div style="font-size:1.45rem; font-weight:800; color:#0F172A; margin-top:4px;">
                    🧠 지식 승인센터
                </div>
            </div>
            <div style="text-align:right; font-size:0.80rem; color:#64748B;">
                담당: <strong>경영지원담당 회계팀</strong> (jongmin.park1@cj.net)
            </div>
        </div>
        <div style="font-size:0.84rem; color:#475569; margin-top:6px; line-height:1.5;">
            AI 답변을 검토·수정·승인하여 신뢰할 수 있는 세무 지식 DB로 승격하는 공간입니다. 승인된 결과만 '승인된 자료'에 자동 반영됩니다.
        </div>
    </div>
    """
    st.html(header_html)

    queue = st.query_params.get("queue", "candidate")
    if queue not in {"candidate", "reviewing", "rejected"}:
        queue = "candidate"
    queue_labels = {"candidate": "📥 승인 대기", "reviewing": "🔎 검토 중", "rejected": "🗃️ 반려 보관함"}
    center_mode = queue_labels[queue]
    st.subheader(f"{center_mode} · {status_counts.get(queue, 0)}건")

    # 2. KPI 메트릭 바 (st.html 사용)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.html(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:3px solid #003876; border-radius:8px; padding:12px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:0.78rem; font-weight:600; color:#64748B;">활성 검토 사례</div>
            <div style="font-size:1.50rem; font-weight:800; color:#003876; margin-top:3px;">{kpi.get('total_active_cases', 0)}<span style="font-size:0.85rem; font-weight:500; color:#64748B;">건</span></div>
        </div>
        """)

    with c2:
        st.html(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:3px solid #0284C7; border-radius:8px; padding:12px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:0.78rem; font-weight:600; color:#64748B;">누적 분석 실행</div>
            <div style="font-size:1.50rem; font-weight:800; color:#0284C7; margin-top:3px;">{kpi.get('total_reviews_run', 0)}<span style="font-size:0.85rem; font-weight:500; color:#64748B;">회</span></div>
        </div>
        """)

    with c3:
        st.html(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:3px solid #10B981; border-radius:8px; padding:12px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:0.78rem; font-weight:600; color:#64748B;">최근 검토 일시</div>
            <div style="font-size:0.95rem; font-weight:700; color:#0F172A; margin-top:8px;">{kpi.get('recent_reviewed_at', '-')}</div>
        </div>
        """)

    with c4:
        st.html(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:3px solid #16A34A; border-radius:8px; padding:12px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:0.78rem; font-weight:600; color:#64748B;">승인 지식</div>
            <div style="font-size:1.50rem; font-weight:800; color:#166534; margin-top:3px;">{status_counts.get('approved', 0)}<span style="font-size:0.85rem; font-weight:500; color:#64748B;">건</span></div>
        </div>
        """)

    with c5:
        pending_count = status_counts.get('candidate', 0) + status_counts.get('reviewing', 0)
        st.html(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:3px solid #D97706; border-radius:8px; padding:12px 16px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:0.78rem; font-weight:600; color:#64748B;">승인 대기·검토 중</div>
            <div style="font-size:1.50rem; font-weight:800; color:#B45309; margin-top:3px;">{pending_count}<span style="font-size:0.85rem; font-weight:500; color:#64748B;">건</span></div>
        </div>
        """)

    feedback_counts = kpi.get("feedback_counts", {})
    feedback_total = feedback_counts.get("helpful", 0) + feedback_counts.get("needs_correction", 0)
    helpful_rate = round(feedback_counts.get("helpful", 0) * 100 / feedback_total) if feedback_total else None
    active_total = kpi.get("total_active_cases", 0)
    approval_rate = round(status_counts.get("approved", 0) * 100 / active_total) if active_total else 0
    with st.expander("📈 지식 성장 현황", expanded=False):
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("지식 승인율", f"{approval_rate}%", help="활성 검토 중 회계팀이 승인한 지식 비율")
        g2.metric(
            "도움됨 비율",
            f"{helpful_rate}%" if helpful_rate is not None else "평가 없음",
            help="피드백이 등록된 답변 중 도움됨 평가 비율",
        )
        g3.metric("수정 필요", f"{feedback_counts.get('needs_correction', 0)}건", help="우선 재검토해야 할 사용자 피드백")
        g4.metric("내부 지식 활용", f"{kpi.get('knowledge_source_uses', 0)}회", help="검토 이력에 저장된 내부 근거의 누적 사용 횟수")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 3. 검색 및 필터 툴바
    with st.container():
        f1, f2, f3, f4, f5 = st.columns([2.8, 1.35, 1.35, 1.5, 1.1])
        with f1:
            search_query = st.text_input("🔍 지식 후보 검색", placeholder="질문, 쟁점, 세무 키워드, 판례명 검색...", label_visibility="collapsed")
        with f2:
            tax_filter = st.selectbox("세목 필터", ["전체", "법인세", "부가가치세", "원천세", "상속·증여세", "지방세", "조세일반"], label_visibility="collapsed")
        with f3:
            risk_filter = st.selectbox("리스크 등급", ["전체", "고위험", "중립/유의", "저위험"], label_visibility="collapsed")
        with f4:
            st.caption(f"현재 폴더  \n**{center_mode.split(' (')[0]}**")
            status_filter_label = "전체"
        with f5:
            include_archived = st.checkbox("📦 보관함 포함", value=False)
        quality_filter = st.selectbox(
            "품질 관리 작업함",
            ["전체", "🛠️ 수정 필요 · 미처리", "✅ 수정 필요 · 처리 완료", "⏰ 승인 지식 재검토 필요"],
            help="사용자 피드백과 오래된 승인 지식을 빠르게 모아봅니다.",
        )

    # 4. 데이터 조회 및 필터링
    records = repo.get_all(include_archived=include_archived, search_query=search_query, tax_category=tax_filter)
    # 승인 완료 지식은 '승인된 자료'에서만 관리합니다.
    records = [r for r in records if r.get("knowledge_status", "candidate") != "approved"]
    if queue == "candidate":
        records = [r for r in records if r.get("knowledge_status", "candidate") == "candidate"]
    elif queue == "reviewing":
        records = [r for r in records if r.get("knowledge_status", "candidate") == "reviewing"]
    else:
        records = [r for r in records if r.get("knowledge_status", "candidate") == "rejected"]
    if risk_filter != "전체":
        records = [r for r in records if r.get("risk_level") == risk_filter]
    if status_filter_label != "전체":
        selected_status = next(k for k, v in KNOWLEDGE_STATUS_LABELS.items() if v == status_filter_label)
        records = [r for r in records if r.get("knowledge_status", "candidate") == selected_status]
    if quality_filter == "🛠️ 수정 필요 · 미처리":
        records = [r for r in records if r.get("feedback_rating") == "needs_correction" and not r.get("feedback_resolved_at")]
    elif quality_filter == "✅ 수정 필요 · 처리 완료":
        records = [r for r in records if r.get("feedback_rating") == "needs_correction" and r.get("feedback_resolved_at")]
    elif quality_filter == "⏰ 승인 지식 재검토 필요":
        records = [r for r in records if _needs_freshness_review(r)]

    # 내보내기 버튼 바
    col_cnt, col_exp1, col_exp2 = st.columns([5, 1.5, 1.5])
    with col_cnt:
        st.html(f"<div style='font-size:0.88rem; color:#334155; font-weight:700; padding-top:6px;'>검색 결과 총 <span style='color:#003876;'>{len(records)}</span>건</div>")
    with col_exp1:
        if records:
            csv_data = "\ufeff" + generate_history_csv(records)
            st.download_button(
                label="📥 엑셀(CSV)",
                data=csv_data.encode("utf-8-sig"),
                file_name=f"CJFreshway_Review_History_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    with col_exp2:
        if records:
            txt_data = generate_history_txt(records)
            st.download_button(
                label="📑 TXT 보고서",
                data=txt_data.encode("utf-8"),
                file_name=f"CJFreshway_Review_Report_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 5. 레코드 카드 렌더링
    if not records:
        empty_html = """
        <div style="text-align:center; padding:50px 20px; background:#F8FAFC; border:1px dashed #CBD5E1; border-radius:10px; margin-top:10px;">
            <div style="font-size:2rem; margin-bottom:10px;">⏱️</div>
            <div style="font-size:1.05rem; font-weight:700; color:#334155;">조건에 부합하는 검토 기록이 없습니다</div>
            <div style="font-size:0.85rem; color:#64748B; margin-top:5px;">
                사이드바의 '새 검토' 메뉴에서 세무 상황 질의를 실행하시면 이곳에 자동으로 이력이 축적됩니다.
            </div>
        </div>
        """
        st.html(empty_html)
        return

    for rec in records:
        rec_id = rec.get("id", "")
        tax = rec.get("tax_category", "조세일반")
        risk = rec.get("risk_level", "중립/유의")
        is_archived = rec.get("is_archived", False)
        rev_count = rec.get("review_count", 1)
        last_dt = rec.get("last_reviewed_at", "-")
        first_dt = rec.get("first_created_at", "-")
        knowledge_status = rec.get("knowledge_status", "candidate") or "candidate"
        knowledge_status_badge = KNOWLEDGE_STATUS_LABELS.get(knowledge_status, "🟡 승인 대기")
        feedback_rating = rec.get("feedback_rating", "")
        feedback_badge = "👍 도움됨" if feedback_rating == "helpful" else "🛠️ 수정 필요" if feedback_rating == "needs_correction" else ""
        if feedback_rating == "needs_correction" and rec.get("feedback_resolved_at"):
            feedback_badge = "✅ 수정 완료"
        freshness_badge = "⏰ 재검토 필요" if _needs_freshness_review(rec) else ""
        feedback_badge_html = f'<span style="background:#FFF7ED; color:#9A3412; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px; border:1px solid #FED7AA;">{feedback_badge}</span>' if feedback_badge else ""
        freshness_badge_html = f'<span style="background:#FEF2F2; color:#B91C1C; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px; border:1px solid #FECACA;">{freshness_badge}</span>' if freshness_badge else ""

        # 뱃지 색상
        if "고위험" in risk:
            risk_badge = '<span style="background:#FEE2E2; color:#991B1B; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:4px; border:1px solid #FECACA;">🔴 고위험</span>'
        elif "저위험" in risk:
            risk_badge = '<span style="background:#DCFCE7; color:#166534; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:4px; border:1px solid #BBF7D0;">🟢 저위험</span>'
        else:
            risk_badge = '<span style="background:#FEF3C7; color:#92400E; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:4px; border:1px solid #FDE68A;">🟡 중립/유의</span>'

        arch_badge = '<span style="background:#E2E8F0; color:#475569; font-size:0.75rem; font-weight:700; padding:2px 6px; border-radius:4px;">📦 보관됨</span>' if is_archived else ''

        card_bg = "#F8FAFC" if is_archived else "#FFFFFF"
        q_text = rec.get('query', '')
        core_issue = rec.get('core_issue', '')
        active_kws = rec.get('active_keywords', [])
        conc_text = rec.get('briefing_conclusion', '') or ''
        risk_reason = rec.get('risk_reason', '')
        case_comp = rec.get('case_comparison', '')
        checklist = rec.get('checklist', [])
        top_cases = rec.get('top_cases', [])
        knowledge_sources = rec.get('knowledge_sources', []) or rec.get('briefing_full', {}).get('internal_knowledge_sources', [])
        direct_cnt = rec.get('direct_basis_count', 0)
        total_cnt = rec.get('total_results_count', 0)
        model_name = rec.get('model_used', '') or 'AI Assistant'

        kw_pills = "".join([f'<span style="display:inline-block; background:#F1F5F9; color:#475569; font-size:0.75rem; font-weight:600; padding:2px 8px; border-radius:12px; margin-right:4px; margin-top:4px; border:1px solid #E2E8F0;">#{k}</span>' for k in active_kws])

        issue_html = f"""
        <div style="font-size:0.90rem; color:#1E293B; margin-bottom:8px; display:flex; align-items:flex-start; gap:6px;">
            <span style="color:#003876; font-weight:800; white-space:nowrap;">🎯 핵심 쟁점:</span>
            <span style="font-weight:600;">{core_issue}</span>
        </div>
        """ if core_issue else ""

        kw_block = f'<div style="margin-bottom:10px;">{kw_pills}</div>' if active_kws else ""

        risk_reason_html = f"""
        <div style="font-size:0.83rem; color:#991B1B; background:#FEF2F2; border:1px solid #FECACA; border-radius:6px; padding:7px 12px; margin-bottom:8px; line-height:1.45;">
            <strong>⚠️ 리스크 요인 분석:</strong> {risk_reason}
        </div>
        """ if risk_reason else ""

        basis_info = f'<span style="background:#F0FDF4; color:#166534; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px; border:1px solid #BBF7D0;">⚖️ 직접근거 {direct_cnt}건 / 총 {total_cnt}건</span>' if total_cnt else ""
        model_info = f'<span style="background:#F8FAFC; color:#64748B; font-size:0.74rem; font-weight:600; padding:2px 6px; border-radius:4px; border:1px solid #E2E8F0;">🤖 {model_name}</span>'

        # st.html()을 사용하여 브라우저 DOM에 직접 주입 (마크다운 파서 완전 우회)
        card_html = f"""
        <div style="background:{card_bg}; border:1px solid #E2E8F0; border-radius:10px; padding:16px 18px 14px 18px; margin-bottom:8px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                    <span style="background:#EFF8FF; color:#003876; font-size:0.78rem; font-weight:800; padding:2px 8px; border-radius:4px; border:1px solid #B2DDFF;">
                        [{tax}]
                    </span>
                    {risk_badge}
                    <span style="background:#F1F5F9; color:#475569; font-size:0.75rem; font-weight:600; padding:2px 6px; border-radius:4px;">
                        누적 검토 {rev_count}회
                    </span>
                    {basis_info}
                    <span style="background:#F8FAFC; color:#334155; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px; border:1px solid #CBD5E1;">{knowledge_status_badge}</span>
                    {feedback_badge_html}
                    {freshness_badge_html}
                    {arch_badge}
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    {model_info}
                    <div style="font-size:0.78rem; color:#94A3B8;">
                        최종: {last_dt}
                    </div>
                </div>
            </div>
            <div style="font-size:1.03rem; font-weight:800; color:#0F172A; line-height:1.45; margin-bottom:6px;">
                📌 {q_text}
            </div>
            {issue_html}
            {kw_block}
            <div style="font-size:0.85rem; color:#334155; line-height:1.6; background:#F8FAFC; border:1px solid #F1F5F9; border-radius:6px; padding:10px 14px; margin-bottom:6px;">
                <div style="font-weight:800; color:#003876; margin-bottom:4px; font-size:0.88rem;">💡 AI 실무 진단 및 해석 결론</div>
                {risk_reason_html}
                <div style="white-space:pre-line;">{conc_text}</div>
            </div>
        </div>
        """
        st.html(card_html)

        # 당시 상세 진단 리포트 & 인용 판례 Expander
        with st.expander(f"📑 당시 상세 진단 리포트 & 인용 판례 전문 열람 (판례 {len(top_cases)}건 · 증빙 {len(checklist)}종)", expanded=False):
            if feedback_rating:
                feedback_text = "도움됨" if feedback_rating == "helpful" else "수정 필요"
                st.info(
                    f"사용자 피드백: {feedback_text} · {rec.get('feedback_note', '') or '추가 의견 없음'} "
                    f"({rec.get('feedback_by', '-')}, {rec.get('feedback_at', '-')})"
                )
            # 1. 증빙 체크리스트
            if checklist:
                chk_items_html = "".join([f'<li style="margin-bottom:6px; color:#1E293B;"><strong>[구비 필요]</strong> {item}</li>' for item in checklist])
                st.html(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-left:4px solid #0284C7; border-radius:6px; padding:12px 16px; margin-bottom:12px;">
                    <div style="font-size:0.88rem; font-weight:800; color:#003876; margin-bottom:8px;">📋 과세관청 입증 대비 필수 증빙 체크리스트</div>
                    <ul style="margin:0; padding-left:18px; font-size:0.84rem; line-height:1.6;">
                        {chk_items_html}
                    </ul>
                </div>
                """)

            # 2. 판례 비교 분석
            if case_comp:
                st.html(f"""
                <div style="background:#F0FDF4; border:1px solid #DCFCE7; border-left:4px solid #16A34A; border-radius:6px; padding:12px 16px; margin-bottom:12px;">
                    <div style="font-size:0.88rem; font-weight:800; color:#166534; margin-bottom:6px;">🔍 유사 / 상충 판례 비교 분석 (Case Comparison)</div>
                    <div style="font-size:0.84rem; color:#1E293B; line-height:1.6; white-space:pre-line;">{case_comp}</div>
                </div>
                """)

            # 3. 주요 인용 판례 목록
            if knowledge_sources:
                st.markdown(f"**📚 당시 사용한 내부 TAX 지식 ({len(knowledge_sources)}건)**")
                for source in knowledge_sources:
                    source_kind = "승인 지식" if source.get("knowledge_type") == "approved_review" else "Obsidian"
                    st.markdown(f"- **[{source_kind}] {source.get('title', '제목 없음')}**")
                    st.caption(
                        f"K{source.get('document_id', '-')} · {source.get('source_path', '')} · "
                        f"검색점수 {source.get('score', 0)}"
                    )

            # 4. 주요 인용 판례 목록
            if top_cases:
                cases_html_list = []
                for c in top_cases:
                    c_num = c.get("case_number", "")
                    c_title = c.get("title", "")
                    c_court = c.get("court", "")
                    c_date = c.get("date", "")
                    c_score = c.get("relevance_score", 0)
                    c_basis = c.get("basis_type", "")
                    c_summary = c.get("summary", "")
                    cases_html_list.append(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:10px 14px; margin-bottom:8px; box-shadow:0 1px 2px rgba(0,0,0,0.02);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <div>
                                <span style="font-weight:800; color:#003876; font-size:0.86rem;">{c_num}</span>
                                <span style="font-size:0.80rem; color:#475569; margin-left:6px;">({c_court} {c_date})</span>
                                <span style="background:#EFF8FF; color:#0284C7; font-size:0.72rem; font-weight:700; padding:1px 6px; border-radius:3px; margin-left:6px;">{c_basis or '참고자료'}</span>
                            </div>
                            <div style="font-size:0.78rem; font-weight:800; color:#0284C7;">
                                적합도 {c_score}%
                            </div>
                        </div>
                        <div style="font-weight:600; color:#1E293B; font-size:0.84rem; margin-bottom:4px;">
                            {c_title}
                        </div>
                        <div style="font-size:0.80rem; color:#64748B; line-height:1.45;">
                            {c_summary}
                        </div>
                    </div>
                    """)
                st.html(f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px 16px; margin-bottom:12px;">
                    <div style="font-size:0.88rem; font-weight:800; color:#003876; margin-bottom:8px;">⚖️ 인용된 핵심 판례 및 행정해석 ({len(top_cases)}건)</div>
                    {''.join(cases_html_list)}
                </div>
                """)

            # 5. 재검토 변경 이력 (Revisions Audit Trail)
            revisions = rec.get("revisions", [])
            if len(revisions) > 1:
                rev_rows = []
                for rev in reversed(revisions):
                    r_idx = rev.get("review_index", 1)
                    r_at = rev.get("reviewed_at", "-")
                    r_risk = rev.get("risk_level", "-")
                    r_cat = rev.get("selected_category", "전체")
                    r_kws = ", ".join(rev.get("active_keywords", [])) or "-"
                    r_direct = rev.get("direct_basis_count", 0)
                    r_tot = rev.get("total_results_count", 0)
                    r_conc = rev.get("briefing_conclusion", "")[:80]
                    rev_rows.append(f"""
                    <tr style="border-bottom: 1px solid #F1F5F9; font-size:0.78rem;">
                        <td style="padding: 6px 8px; font-weight:700; color:#003876;">#{r_idx}회차</td>
                        <td style="padding: 6px 8px; color:#64748B;">{r_at}</td>
                        <td style="padding: 6px 8px;"><span style="font-weight:700;">{r_risk}</span></td>
                        <td style="padding: 6px 8px; color:#475569;">{r_cat}</td>
                        <td style="padding: 6px 8px; color:#475569;">{r_kws}</td>
                        <td style="padding: 6px 8px; color:#166534;">{r_direct}/{r_tot}건</td>
                        <td style="padding: 6px 8px; color:#64748B;">{r_conc}...</td>
                    </tr>
                    """)
                st.html(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:12px 16px; margin-bottom:12px;">
                    <div style="font-size:0.88rem; font-weight:800; color:#003876; margin-bottom:8px;">🕒 질의 재검토 및 조건 변경 이력 ({len(revisions)}회차 누적)</div>
                    <table style="width:100%; border-collapse:collapse; text-align:left;">
                        <thead>
                            <tr style="background:#F8FAFC; border-bottom:2px solid #E2E8F0; font-size:0.76rem; color:#475569;">
                                <th style="padding:6px 8px;">회차</th>
                                <th style="padding:6px 8px;">검토일시</th>
                                <th style="padding:6px 8px;">리스크</th>
                                <th style="padding:6px 8px;">검색영역</th>
                                <th style="padding:6px 8px;">활성 키워드</th>
                                <th style="padding:6px 8px;">직접/전체 판례</th>
                                <th style="padding:6px 8px;">결론 요약</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(rev_rows)}
                        </tbody>
                    </table>
                </div>
                """)

            # 6. 검토 메타데이터
            st.html(f"""
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94A3B8; padding:6px 2px; border-top:1px dashed #E2E8F0;">
                <div><strong>검토 ID:</strong> {rec_id} &nbsp;|&nbsp; <strong>질의 지문:</strong> <code>{rec.get('query_fingerprint', '')[:16]}</code></div>
                <div><strong>기준 세법:</strong> {rec.get('applied_tax_base_date', '2026-01-01')} &nbsp;|&nbsp; <strong>분석 엔진:</strong> {model_name}</div>
            </div>
            """)

        with st.expander(f"🛡️ 지식 승인 관리 · {knowledge_status_badge}", expanded=False):
            st.caption("AI 결과는 승인 전까지 다음 질문의 확정 지식으로 사용되지 않습니다. 결론과 공식 근거를 확인한 뒤 상태를 변경하세요.")
            status_keys = list(KNOWLEDGE_STATUS_LABELS.keys())
            selected_label = st.selectbox(
                "처리 상태",
                options=status_keys,
                index=status_keys.index(knowledge_status) if knowledge_status in status_keys else 0,
                format_func=lambda value: KNOWLEDGE_STATUS_LABELS[value],
                key=f"knowledge_status_{rec_id}",
            )
            reviewer = st.text_input(
                "검토자",
                value=rec.get("knowledge_reviewed_by", "") or "jongmin.park1@cj.net",
                key=f"knowledge_reviewer_{rec_id}",
                disabled=True,
                help="현재 로그인 사용자로 기록됩니다.",
            )
            review_note = st.text_area(
                "검토 메모",
                value=rec.get("knowledge_review_note", "") or "",
                placeholder="승인 근거, 반려 사유 또는 대체된 최신 기준을 기록하세요.",
                key=f"knowledge_note_{rec_id}",
                height=80,
            )
            approval_confirmed = True
            if selected_label == "approved":
                approval_confirmed = st.checkbox(
                    "AI 결론과 인용된 공식 근거를 직접 확인했습니다.",
                    key=f"knowledge_confirm_{rec_id}",
                )
            if st.button("💾 지식 상태 저장", key=f"knowledge_save_{rec_id}", type="primary", use_container_width=True):
                if selected_label == "approved" and not approval_confirmed:
                    st.warning("승인하려면 결론과 공식 근거 확인 항목을 체크해 주세요.")
                elif selected_label in {"rejected", "superseded"} and not review_note.strip():
                    st.warning("반려 또는 대체 처리에는 검토 메모가 필요합니다.")
                elif not reviewer.strip():
                    st.warning("검토자를 입력해 주세요.")
                else:
                    try:
                        if repo.set_knowledge_status(rec_id, selected_label, reviewer, review_note):
                            st.toast("지식 승인 상태를 저장했습니다.", icon="✅")
                            st.rerun()
                        else:
                            st.error("상태를 저장하지 못했습니다. 다시 시도해 주세요.")
                    except ValueError as exc:
                        st.warning(str(exc))

        if feedback_rating == "needs_correction":
            resolved_at = rec.get("feedback_resolved_at", "")
            title = "✅ 품질 개선 처리 완료" if resolved_at else "🛠️ 수정 필요 작업"
            with st.expander(title, expanded=not bool(resolved_at)):
                st.write(rec.get("feedback_note", "") or "수정 사유가 없습니다.")
                if resolved_at:
                    st.success(
                        f"{rec.get('feedback_resolved_by', '-')} · {resolved_at}\n\n"
                        f"{rec.get('feedback_resolution_note', '')}"
                    )
                else:
                    resolution_note = st.text_area(
                        "처리 내용",
                        placeholder="무엇을 확인하고 어떻게 수정했는지 기록하세요.",
                        key=f"feedback_resolution_{rec_id}",
                    )
                    if st.button("✅ 처리 완료", key=f"feedback_resolve_{rec_id}", use_container_width=True):
                        try:
                            if repo.resolve_feedback(rec_id, "jongmin.park1@cj.net", resolution_note):
                                st.toast("품질 개선 작업을 완료했습니다.", icon="✅")
                                st.rerun()
                            else:
                                st.error("처리 상태를 저장하지 못했습니다.")
                        except ValueError as exc:
                            st.warning(str(exc))

        if knowledge_status == "rejected":
            st.error(
                f"반려 사유: {rec.get('knowledge_review_note', '') or '사유 미기재'}  \n"
                f"처리자: {rec.get('knowledge_reviewed_by', '-')} · {rec.get('knowledge_reviewed_at', '-')}"
            )
            if st.button("↩️ 재검토 요청", key=f"restore_rejected_{rec_id}", type="primary", use_container_width=True):
                try:
                    if repo.set_knowledge_status(
                        rec_id, "candidate", "jongmin.park1@cj.net", "반려 보관함에서 재검토 요청"
                    ):
                        st.toast("승인 대기 목록으로 복원했습니다.", icon="↩️")
                        st.rerun()
                    else:
                        st.error("재검토 요청을 저장하지 못했습니다.")
                except ValueError as exc:
                    st.warning(str(exc))

        # 액션 버튼 영역
        b1, b2 = st.columns([2, 1.2])
        with b1:
            if st.button("🔄 이 조건으로 재검토", key=f"reeval_{rec_id}", use_container_width=True, help="메인 검색창에 해당 질문을 채우고 최신 세법으로 즉시 재실행합니다."):
                st.session_state["search_input"] = rec.get("query", "")
                st.session_state["main_prompt_text"] = rec.get("query", "")
                st.session_state["selected_tax_type"] = rec.get("tax_category", "전체")
                st.session_state["active_view"] = "new_review"
                st.rerun()

        with b2:
            if not is_archived:
                if st.button("📦 보관(숨김)", key=f"arch_{rec_id}", use_container_width=True, help="목록에서 숨기며 감사 로그에는 안전하게 보존됩니다."):
                    repo.archive_record(rec_id, user_id="jongmin.park1@cj.net", reason="사용자 보관 요청")
                    st.rerun()
            else:
                if st.button("↩️ 복원", key=f"rest_{rec_id}", use_container_width=True, help="활성 목록으로 복원합니다."):
                    repo.restore_record(rec_id, user_id="jongmin.park1@cj.net")
                    st.rerun()

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
