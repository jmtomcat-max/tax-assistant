# -*- coding: utf-8 -*-
import io
import streamlit as st
import pandas as pd

from config import STOP_KEYWORDS
from storage import save_saved_cases



def build_multi_case_report(saved_cases: dict) -> str:
    """세무검토 사례관리 보관함 종합 요약형 보고서(TXT)"""
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "[CJ프레시웨이] 세무검토 사례관리 보관함 종합 검토의견서 (요약형)",
        f"· 추출 일시: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        f"· 보관 사례 수: 총 {len(saved_cases)}건",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    for idx, (cid, item) in enumerate(saved_cases.items(), 1):
        t = item.get("title", "")
        tax = item.get("tax_category", "조세일반")
        status = item.get("review_status", "검토중")
        risk = item.get("risk_level", "중립/유의")
        tags_str = ", ".join(item.get("issue_tags", []))
        c_at = item.get("created_at", item.get("saved_at", "-"))
        
        facts = item.get("facts_summary", {})
        ai_op = item.get("ai_opinion", {})
        user_q = item.get("user_query", "")
        memo = item.get("user_memo", "")
        
        lines.append(f"【사례 #{idx}】 {t}")
        lines.append(f"• 세목: [{tax}] | 검토상태: [{status}] | 리스크 등급: [{risk}]")
        if tags_str:
            lines.append(f"• 쟁점 태그: {tags_str}")
        lines.append(f"• 등록일시: {c_at}")
        
        if user_q:
            lines.append(f"• 검토 대상 질문: {user_q[:120]}...")
            
        if facts:
            lines.append("• 사실관계 요약:")
            lines.append(f"  - 거래유형: {facts.get('trans_type','-')} | 거래상대방: {facts.get('counterparty','-')}")
            lines.append(f"  - 거래금액: {facts.get('amount','-')} | 보유증빙: {facts.get('evidence_held','-')}")
            
        if ai_op:
            lines.append("• AI 검토 결론:")
            conc = ai_op.get("conclusion", "").strip()
            lines.append(f"  {conc[:300]}..." if len(conc) > 300 else f"  {conc}")
            lines.append(f"• 필수 점검 체크리스트: {ai_op.get('checklist', '').strip()[:200]}...")
            
        if memo:
            lines.append(f"• 사용자 메모: {memo}")
            
        lines.append("────────────────────────────────────────────────────────────\n")
    lines.append("* 출처: CJ프레시웨이 TAX AI 비서 (국가법령정보센터 DB & ChatGPT Enterprise 분석)")
    return "\n".join(lines)


def build_single_case_txt_report(item: dict) -> str:
    """개별 세무검토 사례 카드 상세 텍스트 보고서 생성"""
    t = item.get("title", "")
    tax = item.get("tax_category", "조세일반")
    status = item.get("review_status", "검토중")
    risk = item.get("risk_level", "중립/유의")
    tags_str = ", ".join(item.get("issue_tags", []))
    c_at = item.get("created_at", item.get("saved_at", "-"))
    u_at = item.get("updated_at", c_at)
    
    facts = item.get("facts_summary", {})
    legal_refs = item.get("legal_references", [])
    ai_op = item.get("ai_opinion", {})
    user_q = item.get("user_query", "")
    memo = item.get("user_memo", "")
    
    lines = [
        "════════════════════════════════════════════════════════════",
        f"[CJ프레시웨이 세무검토 사례 보고서] {t}",
        "════════════════════════════════════════════════════════════",
        f"1. 기본 정보",
        f"  • 관리번호: {item.get('case_id', '-')}",
        f"  • 세    목: {tax}",
        f"  • 검토상태: {status}",
        f"  • 리스크등급: {risk}",
        f"  • 쟁점태그: {tags_str or '미지정'}",
        f"  • 등 록 일: {c_at} (최종수정: {u_at})",
        "",
        "2. 사용자 질문 및 검토 요청 내용",
        f"  {user_q or '미기재'}",
        "",
        "3. 구조화 사실관계 요약",
        f"  • 거래 유형: {facts.get('trans_type', '-')}",
        f"  • 거래 상대방: {facts.get('counterparty', '-')}",
        f"  • 거래 금액: {facts.get('amount', '-')}",
        f"  • 귀속 시기: {facts.get('tax_period', '-')}",
        f"  • 보유 증빙: {facts.get('evidence_held', '-')}",
        f"  • 검토 목적: {facts.get('purpose', '-')}",
        "",
        "4. 관련 법령 및 공식 판례·예규 근거",
    ]
    
    if not legal_refs:
        lines.append("  (등록된 개별 판례 링크 없음 - 종합 검색 풀 참조)")
    else:
        for idx, lr in enumerate(legal_refs, 1):
            lines.append(f"  [{idx}] {lr.get('court','')} {lr.get('case_number','')} ({lr.get('date','')})")
            lines.append(f"      사건명: {lr.get('title','')}")
            if lr.get('link'):
                lines.append(f"      링크: {lr.get('link')}")
                
    lines.extend([
        "",
        "5. AI 세무 종합 검토의견",
        f"  • 근거 강도: [{ai_op.get('basis_strength', '-')}] ({ai_op.get('basis_rationale', '-')})",
        f"  • 핵심 결론:",
        f"    {ai_op.get('conclusion', '').strip()}",
        "",
        f"  • 실무 필수 증빙 체크리스트:",
        f"    {ai_op.get('checklist', '').strip()}",
        "",
        "6. 담당자 실무 메모 및 후속 조치",
        f"  {memo or '(등록된 메모 없음)'}",
        "════════════════════════════════════════════════════════════",
        f"※ 본 문서는 CJ프레시웨이 TAX AI 비서에서 작성된 사내 사전 검토용 의견서입니다."
    ])
    
    return "\n".join(lines)


def build_vault_excel_report(saved_cases_dict: dict) -> bytes:
    """세무검토 사례 목록을 구조화된 상세 엑셀 바이트로 생성"""
    rows = []
    for cid, item in saved_cases_dict.items():
        facts = item.get("facts_summary", {})
        ai_op = item.get("ai_opinion", {})
        refs = item.get("legal_references", [])
        ref_summary = "; ".join([f"{r.get('court','')} {r.get('case_number','')} ({r.get('title','')})" for r in refs[:3]])
        
        rows.append({
            "사례ID": item.get("case_id", cid),
            "제목": item.get("title", ""),
            "세목": item.get("tax_category", "조세일반"),
            "검토상태": item.get("review_status", "검토중"),
            "리스크등급": item.get("risk_level", "중립/유의"),
            "쟁점태그": ", ".join(item.get("issue_tags", [])),
            "사용자질문": item.get("user_query", ""),
            "거래유형": facts.get("trans_type", ""),
            "거래상대방": facts.get("counterparty", ""),
            "거래금액": facts.get("amount", ""),
            "귀속시기": facts.get("tax_period", ""),
            "보유증빙": facts.get("evidence_held", ""),
            "검토목적": facts.get("purpose", ""),
            "관련판례_법령": ref_summary,
            "AI_근거강도": ai_op.get("basis_strength", ""),
            "AI_검토결론": ai_op.get("conclusion", ""),
            "실무체크리스트": ai_op.get("checklist", ""),
            "사용자메모": item.get("user_memo", ""),
            "등록일시": item.get("created_at", item.get("saved_at", "")),
            "최종수정일": item.get("updated_at", "")
        })
        
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='세무검토사례관리')
    return buf.getvalue()




def render_vault_view():
    """
    세무검토 사례관리 보관함 뷰 (Vault View) - 3단 칸반 보드 (Kanban Board) 레이아웃
    """

    st.markdown("""
    <div class="compact-header">
        <div class="cj-badge">
            <span class="cj-dot"></span>
            CJ FRESHWAY · TAX INTELLIGENCE
        </div>
        <div class="service-title">📁 세무검토 사례관리 보관함 (Kanban Board)</div>
        <div class="service-subtitle">접수된 세무 검토 사례의 진행 상태(<b>대기 중 / 세무팀 검토 중 / 최종 회신 완료</b>)를 3단 칸반 보드로 한눈에 파악하고 관리합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    # 민감정보 보호 및 보안 안내 배너
    st.markdown("""
    <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-left:4px solid #005B45; border-radius:8px; padding:10px 14px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
        <div style="font-size:0.83rem; color:#166534; line-height:1.5;">
            🔒 <b>보안 및 민감정보 보호 안내</b>: 저장 시 주민등록번호, 계좌번호, API Key 등은 자동 마스킹 처리됩니다.
        </div>
        <div style="font-size:0.78rem; color:#005B45; font-weight:700; background:#DCFCE7; padding:3px 8px; border-radius:4px;">
            원자적 안전 저장 (Atomic Storage) 활성
        </div>
    </div>
    """, unsafe_allow_html=True)

    all_cases_dict = st.session_state.get("saved_cases", {})

    # 1. 데이터 상태(status) 초기화: status 키가 없으면 기본값으로 "대기 중" 부여
    needs_save = False
    for cid, item in all_cases_dict.items():
        if "status" not in item or not item.get("status"):
            rev_st = item.get("review_status", "")
            if rev_st == "최종 완료":
                item["status"] = "회신 완료"
            elif rev_st in ["검토중", "1차 완료", "회계사 확인 필요"]:
                item["status"] = "검토 중"
            else:
                item["status"] = "대기 중"
            needs_save = True

    if needs_save:
        st.session_state["saved_cases"] = all_cases_dict
        save_saved_cases(all_cases_dict)

    all_items = list(all_cases_dict.items())

    if not all_items:
        st.markdown("""
        <div class="notion-block nb-gray" style="margin-top:20px; padding:36px 24px; text-align:center; display:block;">
            <div style="font-size:2.4rem; margin-bottom:12px;">📁</div>
            <div style="font-size:1.15rem; font-weight:700; color:#0F172A; margin-bottom:8px;">현재 보관함에 저장된 세무검토 사례가 없습니다</div>
            <div style="font-size:0.92rem; color:#64748B; line-height:1.6; margin-bottom:20px;">
                세무 상황 질문 검색 후 <b>[☆ 사례 보관함 저장]</b> 버튼을 누르시면,<br>
                질문 내용, 7대 사실관계 요약, 공식 판례 근거, AI 검토의견이 <b>칸반 카드</b> 형태로 이곳에 영구 저장됩니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
        col_empty_s1, col_empty_btn, col_empty_s2 = st.columns([1.5, 2, 1.5])
        with col_empty_btn:
            if st.button("🔍 세무 상황 진단 및 판례 검색하러 가기", key="btn_go_search_from_empty", use_container_width=True, type="primary"):
                st.session_state["active_view"] = "search"
                st.rerun()
        return

    # 다차원 검색 및 필터 툴바
    with st.expander("🔍 세무검토 사례 검색 및 리포트 다운로드", expanded=False):
        col_f_kw, col_f_tax = st.columns([3.5, 2.5], vertical_alignment="center")
        with col_f_kw:
            f_keyword = st.text_input("통합 키워드 검색", placeholder="제목, 사건번호, 질문, 메모, 쟁점태그 검색", key="vault_f_kw")
        with col_f_tax:
            f_tax_opts = ["전체 세목", "법인세", "부가가치세", "소득세·원천세", "상속·증여세", "조세일반"]
            f_tax = st.selectbox("세목 필터", f_tax_opts, index=0, key="vault_f_tax")

    # 필터링 로직 적용
    filtered_items = []
    for cid, it in all_items:
        if f_tax != "전체 세목" and it.get("tax_category") != f_tax:
            continue
        if f_keyword and f_keyword.strip():
            kw = f_keyword.strip().lower()
            target_str = (
                it.get("title", "") + " " +
                it.get("case_number", "") + " " +
                it.get("user_query", "") + " " +
                it.get("user_memo", "") + " " +
                " ".join(it.get("issue_tags", []))
            ).lower()
            if kw not in target_str:
                continue
        filtered_items.append((cid, it))

    # 상단 일괄 액션 바 (카운트 | TXT 다운로드 | 엑셀 다운로드 | 전체 비우기)
    col_v_count, col_v_txt, col_v_excel, col_v_clear = st.columns([2.0, 1.8, 1.8, 1.4], vertical_alignment="center")
    with col_v_count:
        st.markdown(f"<div style='font-size:0.90rem; color:#475569;'>보관 <b>{len(all_items)}건</b> (필터 <b>{len(filtered_items)}건</b>)</div>", unsafe_allow_html=True)
    with col_v_txt:
        filtered_dict = {cid: it for cid, it in filtered_items}
        multi_txt_report = build_multi_case_report(filtered_dict)
        st.download_button(
            label="📄 요약 TXT 다운로드",
            data=multi_txt_report.encode("utf-8"),
            file_name=f"CJ프레시웨이_세무검토사례_요약_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
            key="btn_dl_vault_txt"
        )
    with col_v_excel:
        excel_bytes = build_vault_excel_report(filtered_dict)
        st.download_button(
            label="📥 상세 Excel 다운로드",
            data=excel_bytes,
            file_name=f"CJ프레시웨이_세무검토사례_상세_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="btn_dl_vault_excel"
        )
    with col_v_clear:
        if st.button("🗑️ 전체 비우기", key="btn_clear_all_vault", use_container_width=True):
            st.session_state["confirm_clear_all_vault"] = True
            st.rerun()

    if st.session_state.get("confirm_clear_all_vault", False):
        st.markdown(f"""
        <div style="background:#FEF2F2; border:1.5px solid #FCA5A5; border-left:5px solid #DC2626; border-radius:8px; padding:12px 16px; margin: 10px 0;">
            <div style="font-weight:700; color:#991B1B; font-size:0.92rem;">🚨 [보관함 일괄 삭제 재확인]</div>
            <div style="color:#B91C1C; font-size:0.84rem; margin-top:4px;">정말로 보관함의 모든 세무검토 사례를 영구 삭제하시겠습니까?</div>
        </div>
        """, unsafe_allow_html=True)
        col_c_yes, col_c_no, _ = st.columns([2.0, 1.5, 3.5])
        with col_c_yes:
            if st.button("🚨 예, 전체 영구 삭제합니다", key="btn_confirm_clear_yes", use_container_width=True, type="primary"):
                st.session_state["saved_cases"] = {}
                save_saved_cases({})
                st.session_state["confirm_clear_all_vault"] = False
                st.rerun()
        with col_c_no:
            if st.button("❌ 취소", key="btn_confirm_clear_no", use_container_width=True):
                st.session_state["confirm_clear_all_vault"] = False
                st.rerun()

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # 3단 상태 그룹별 분류
    items_pending = [(cid, it) for cid, it in filtered_items if it.get("status") in ["대기 중", "대기중"]]
    items_reviewing = [(cid, it) for cid, it in filtered_items if it.get("status") in ["검토 중", "검토중"]]
    items_completed = [(cid, it) for cid, it in filtered_items if it.get("status") in ["회신 완료", "최종 회신 완료", "완료", "회신완료"]]

    # =========================================================================
    # 2. 3단 칸반 보드 레이아웃 (col1, col2, col3)
    # =========================================================================
    col1, col2, col3 = st.columns(3)

    def get_tax_badge_html(cat_str):
        if cat_str == "법인세":
            return '<span class="tax-badge tax-corp">🏢 법인세</span>'
        elif cat_str == "부가가치세":
            return '<span class="tax-badge tax-vat">🧾 부가가치세</span>'
        elif cat_str == "소득세·원천세":
            return '<span class="tax-badge tax-income">👤 소득세·원천세</span>'
        elif cat_str == "상속·증여세":
            return '<span class="tax-badge tax-etc">🎁 상속·증여세</span>'
        else:
            return f'<span class="tax-badge tax-etc">⚖️ {cat_str}</span>'

    def get_risk_badge_html(risk_str):
        if "고위험" in str(risk_str):
            return '<span class="badge-risk-high">🔴 리스크: 高</span>'
        elif "저위험" in str(risk_str) or "안전" in str(risk_str):
            return '<span class="badge-risk-low">🟢 리스크: 低</span>'
        else:
            return '<span class="badge-risk-med">🟡 리스크: 中</span>'

    def get_card_tags_html(item):
        tags = item.get("issue_tags", []) or item.get("keywords", [])
        if not tags:
            full_text = (item.get("title", "") + " " + item.get("user_query", "")).lower()
            candidates = ["부당행위계산", "특수관계인", "손금산입", "익금산입", "원천징수", "세금계산서", "가산세", "조세특례", "지방세", "부가가치세", "법인세", "시가산정", "명의신탁"]
            found = [c for c in candidates if c in full_text]
            if found:
                tags = found[:3]
            else:
                tags = ["세무검토", "사례분석"]
        
        tags = tags[:3]
        chips = []
        for t in tags:
            t_clean = str(t).strip()
            if not t_clean.startswith("#"):
                t_clean = "#" + t_clean
            chips.append(f'<span style="background:#F1F5F9; color:#475569; border:1px solid #E2E8F0; padding:2px 7px; border-radius:12px; font-size:0.72rem; font-weight:500; display:inline-block; margin-right:4px; margin-bottom:4px;">{t_clean}</span>')
        return f'<div style="margin-top:4px; margin-bottom:4px;">{"".join(chips)}</div>'

    def render_card_details_expander(item, cid, idx, is_reviewing=False):
        with st.expander("📄 상세 검토 내용 & 7대 요건", expanded=False):
            # 1) 최초 원문 질의 내용 (요약)
            user_q = item.get("user_query", "").strip()
            st.markdown("**❓ 최초 원문 질의**")
            if user_q:
                st.markdown(f"> {user_q[:300]}..." if len(user_q) > 300 else f"> {user_q}")
            else:
                st.caption("등록된 질의 내용이 없습니다.")

            # 2) AI 7대 요건 사실관계
            facts = item.get("facts_summary", {})
            if facts:
                st.markdown("<div style='margin-top:8px;'><b>📋 7대 요건 사실관계</b></div>", unsafe_allow_html=True)
                f_items = []
                if facts.get("trans_type"): f_items.append(f"• **거래유형**: {facts.get('trans_type')}")
                if facts.get("counterparty"): f_items.append(f"• **상대방**: {facts.get('counterparty')}")
                if facts.get("amount"): f_items.append(f"• **거래금액**: {facts.get('amount')}")
                if facts.get("tax_period"): f_items.append(f"• **귀속시기**: {facts.get('tax_period')}")
                if facts.get("evidence_held"): f_items.append(f"• **보유증빙**: {facts.get('evidence_held')}")
                if facts.get("purpose"): f_items.append(f"• **검토목적**: {facts.get('purpose')}")
                if f_items:
                    st.markdown("\n".join(f_items))
                else:
                    st.caption("기재된 사실관계 요약이 없습니다.")

            # 3) 주요 인용 판례 1~2개
            refs = item.get("legal_references", []) or item.get("precedents", [])
            if refs:
                st.markdown("<div style='margin-top:8px;'><b>⚖️ 주요 인용 판례·예규</b></div>", unsafe_allow_html=True)
                for r_idx, r in enumerate(refs[:2], 1):
                    if isinstance(r, dict):
                        court = r.get("court", r.get("org", "판례"))
                        c_num = r.get("case_number", r.get("number", ""))
                        rtitle = r.get("title", "")
                        rlink = r.get("link", "")
                        if rlink:
                            st.markdown(f"{r_idx}. [{court} {c_num}]({rlink}) - {rtitle}")
                        else:
                            st.markdown(f"{r_idx}. **{court} {c_num}** - {rtitle}")
                    elif isinstance(r, str):
                        st.markdown(f"{r_idx}. {r}")

            # 4) 담당자 메모
            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
            if is_reviewing:
                memo_val = st.text_area("📝 담당자 메모", value=item.get("user_memo", ""), key=f"kanban_memo_{cid}_{idx}", height=70)
                if st.button("💾 메모 저장", key=f"btn_save_memo_kanban_{cid}_{idx}", use_container_width=True):
                    item["user_memo"] = memo_val
                    st.session_state["saved_cases"][cid] = item
                    save_saved_cases(st.session_state["saved_cases"])
                    st.toast("메모가 저장되었습니다.", icon="💾")
                    st.rerun()


    def restore_case_to_search_view(item):
        user_q = item.get("user_query") or item.get("title", "")
        tax_cat = item.get("tax_category", "전체")
        
        st.session_state["search_input"] = user_q
        if tax_cat in ["법인세", "부가가치세", "소득세·원천세"]:
            st.session_state["selected_tax_type"] = tax_cat
        else:
            st.session_state["selected_tax_type"] = "전체"
            
        st.session_state["temp_files_data"] = []
        st.session_state["input_version"] = st.session_state.get("input_version", 0) + 1
        
        # ---------------------------------------------------------
        # 저장된 리포트 데이터를 세션에 사전 주입 (재검색/재분석 완전 방지)
        # ---------------------------------------------------------
        files_hash_str = "no_files"
        intent_key = f"intent_v5_{hash(user_q)}_{hash(files_hash_str)}"
        
        raw_tags = item.get("issue_tags", [])
        valid_tags = [t for t in raw_tags if t not in STOP_KEYWORDS]
        if not valid_tags:
            valid_tags = [tax_cat if tax_cat != "전체" else "세무검토"]
            
        intent_data = {
            "tax_category": tax_cat,
            "search_keywords": valid_tags,
            "core_issue": item.get("title", ""),
            "situation_summary": item.get("title", ""),
            "structured_facts": item.get("facts_summary", {})
        }
        st.session_state[intent_key] = intent_data
        
        # 키워드 풀 사전 주입
        kw_pool_key = f"kw_pool_{hash(user_q)}"
        kw_active_key = f"kw_active_{hash(user_q)}"
        st.session_state[kw_pool_key] = valid_tags
        st.session_state[kw_active_key] = valid_tags
        
        # 판례 검색 결과 사전 주입
        category_choice = st.session_state.get("selected_category", "전체")
        current_tax_type = st.session_state.get("selected_tax_type", "전체")
        kw_hash_str = "_".join(sorted(valid_tags))
        search_cache_key = f"search_v5_{hash(user_q)}_{category_choice}_{current_tax_type}_{kw_hash_str}"
        
        refs = item.get("legal_references", []) or item.get("precedents", [])
        raw_items = []
        cited_cases_norm = []
        for r in refs:
            if isinstance(r, dict):
                score_raw = r.get("relevance_score", 0)
                try:
                    score_val = int(float(score_raw)) if score_raw not in (None, "") and str(score_raw).strip() != "" else 0
                except (ValueError, TypeError):
                    score_val = 0
                r_norm = {
                    "tax_category": r.get("tax_category", tax_cat),
                    "court": r.get("court", r.get("Court", r.get("org", "판례"))),
                    "case_number": r.get("case_number", r.get("CaseNumber", r.get("number", "-"))),
                    "date": r.get("date", r.get("Date", "-")),
                    "title": r.get("title", r.get("Title", "-")),
                    "source": r.get("source", r.get("Source", "국가법령정보센터")),
                    "link": r.get("link", r.get("Link", "")),
                    "prec_id": r.get("prec_id", r.get("PrecId", "")),
                    "basis_type": r.get("basis_type", "참고자료"),
                    "relevance_score": score_val,
                    "is_high_relevance": bool(r.get("is_high_relevance", score_val >= 50)),
                    "match_reason": r.get("match_reason", ""),
                    "matched_keywords": r.get("matched_keywords", []),
                    "Title": r.get("title", r.get("Title", "-")),
                    "CaseNumber": r.get("case_number", r.get("CaseNumber", r.get("number", "-"))),
                    "Court": r.get("court", r.get("Court", r.get("org", "판례"))),
                    "Date": r.get("date", r.get("Date", "-")),
                    "Link": r.get("link", r.get("Link", "")),
                    "Source": r.get("source", r.get("Source", "국가법령정보센터")),
                    "PrecId": r.get("prec_id", r.get("PrecId", "")),
                    "Judgement": r.get("title", r.get("Title", "-"))
                }
                raw_items.append(r_norm)
                cited_cases_norm.append(r_norm)

        search_res = {
            "items": raw_items,
            "total": len(raw_items)
        }
        st.session_state[search_cache_key] = search_res
        
        # AI 브리핑 리포트 결과 사전 주입
        ai_op = item.get("ai_opinion", {})
        briefing_res = {
            "risk_level": item.get("risk_level", "중립/유의"),
            "basis_strength": ai_op.get("basis_strength", "유의 필요"),
            "basis_rationale": ai_op.get("basis_rationale", "보관함 사례 저장 데이터"),
            "conclusion": ai_op.get("conclusion", ""),
            "case_comparison": ai_op.get("case_comparison", ""),
            "checklist": ai_op.get("checklist", ""),
            "cited_cases": cited_cases_norm
        }
        briefing_key = f"briefing_{hash(user_q)}_{len(raw_items)}"
        st.session_state[briefing_key] = briefing_res

        
        # 뷰 전환 및 화면 갱신
        st.session_state["active_view"] = "search"
        st.toast(f"'{item.get('title','')[:15]}...' 보관 리포트를 즉시 표시합니다.", icon="📁")
        st.rerun()


    # -------------------------------------------------------------------------
    # 컬럼 1: 📥 신규 접수 / 대기 중
    # -------------------------------------------------------------------------
    with col1:
        st.markdown(f"""
        <div style="background:#F1F5F9; border:1px solid #CBD5E1; border-top:4px solid #64748B; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
            <div style="font-size:0.96rem; font-weight:800; color:#1E293B;">📥 신규 접수 / 대기 중</div>
            <div style="font-size:0.78rem; color:#64748B; margin-top:2px;">총 <b>{len(items_pending)}건</b></div>
        </div>
        """, unsafe_allow_html=True)

        if not items_pending:
            st.caption("대기 중인 사례가 없습니다.")

        for idx, (cid, item) in enumerate(items_pending):
            title = item.get("title", "제목 미지정")
            tax_cat = item.get("tax_category", "조세일반")
            created_at = item.get("created_at", item.get("saved_at", "-"))
            risk_level = item.get("risk_level", "중립/유의")

            with st.container(border=True):
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div>{get_tax_badge_html(tax_cat)} {get_risk_badge_html(risk_level)}</div>
                    <span style="font-size:0.73rem; color:#94A3B8;">{created_at}</span>
                </div>
                {get_card_tags_html(item)}
                <div style="font-size:0.92rem; font-weight:700; color:#0F172A; line-height:1.4; margin-top:4px; margin-bottom:8px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis;" title="{title}">{title}</div>
                """, unsafe_allow_html=True)

                render_card_details_expander(item, cid, idx, is_reviewing=False)

                btn_c1, btn_c2 = st.columns([1.2, 1.3])
                with btn_c1:
                    if st.button("➡️ 검토 시작", key=f"btn_start_review_{cid}_{idx}", use_container_width=True):
                        item["status"] = "검토 중"
                        item["review_status"] = "검토중"
                        st.session_state["saved_cases"][cid] = item
                        save_saved_cases(st.session_state["saved_cases"])
                        st.toast(f"'{title[:15]}...' 항목을 '검토 중'으로 이동했습니다.", icon="➡️")
                        st.rerun()
                with btn_c2:
                    if st.button("📊 리포트 보기", key=f"btn_restore_{cid}_{idx}", use_container_width=True):
                        restore_case_to_search_view(item)

    # -------------------------------------------------------------------------
    # 컬럼 2: 🔍 세무팀 검토 중
    # -------------------------------------------------------------------------
    with col2:
        st.markdown(f"""
        <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-top:4px solid #2563EB; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
            <div style="font-size:0.96rem; font-weight:800; color:#1E40AF;">🔍 세무팀 검토 중</div>
            <div style="font-size:0.78rem; color:#1D4ED8; margin-top:2px;">총 <b>{len(items_reviewing)}건</b></div>
        </div>
        """, unsafe_allow_html=True)

        if not items_reviewing:
            st.caption("현재 검토 중인 사례가 없습니다.")

        for idx, (cid, item) in enumerate(items_reviewing):
            title = item.get("title", "제목 미지정")
            tax_cat = item.get("tax_category", "조세일반")
            created_at = item.get("created_at", item.get("saved_at", "-"))
            risk_level = item.get("risk_level", "중립/유의")

            with st.container(border=True):
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div>{get_tax_badge_html(tax_cat)} {get_risk_badge_html(risk_level)}</div>
                    <span style="font-size:0.73rem; color:#94A3B8;">{created_at}</span>
                </div>
                {get_card_tags_html(item)}
                <div style="font-size:0.92rem; font-weight:700; color:#0F172A; line-height:1.4; margin-top:4px; margin-bottom:8px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis;" title="{title}">{title}</div>
                """, unsafe_allow_html=True)

                render_card_details_expander(item, cid, idx, is_reviewing=True)

                btn_c1, btn_c2, btn_c3 = st.columns([1.0, 1.0, 1.3])
                with btn_c1:
                    if st.button("✅ 완료", key=f"btn_complete_{cid}_{idx}", use_container_width=True, type="primary"):
                        item["status"] = "회신 완료"
                        item["review_status"] = "최종 완료"
                        st.session_state["saved_cases"][cid] = item
                        save_saved_cases(st.session_state["saved_cases"])
                        st.toast(f"'{title[:15]}...' 사례를 '회신 완료' 처리했습니다.", icon="✅")
                        st.rerun()
                with btn_c2:
                    if st.button("⬅️ 대기", key=f"btn_reset_{cid}_{idx}", use_container_width=True):
                        item["status"] = "대기 중"
                        item["review_status"] = "검토중"
                        st.session_state["saved_cases"][cid] = item
                        save_saved_cases(st.session_state["saved_cases"])
                        st.toast(f"'{title[:15]}...' 사례를 '대기 중'으로 원복했습니다.", icon="⬅️")
                        st.rerun()
                with btn_c3:
                    if st.button("📊 리포트 보기", key=f"btn_restore_{cid}_{idx}", use_container_width=True):
                        restore_case_to_search_view(item)

    # -------------------------------------------------------------------------
    # 컬럼 3: ✅ 최종 회신 완료
    # -------------------------------------------------------------------------
    with col3:
        st.markdown(f"""
        <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-top:4px solid #16A34A; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
            <div style="font-size:0.96rem; font-weight:800; color:#15803D;">✅ 최종 회신 완료</div>
            <div style="font-size:0.78rem; color:#16A34A; margin-top:2px;">총 <b>{len(items_completed)}건</b></div>
        </div>
        """, unsafe_allow_html=True)

        if not items_completed:
            st.caption("완료된 사례가 없습니다.")

        for idx, (cid, item) in enumerate(items_completed):
            title = item.get("title", "제목 미지정")
            tax_cat = item.get("tax_category", "조세일반")
            created_at = item.get("created_at", item.get("saved_at", "-"))
            risk_level = item.get("risk_level", "중립/유의")

            with st.container(border=True):
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <div>{get_tax_badge_html(tax_cat)} {get_risk_badge_html(risk_level)}</div>
                    <span style="font-size:0.73rem; color:#94A3B8;">{created_at}</span>
                </div>
                {get_card_tags_html(item)}
                <div style="font-size:0.92rem; font-weight:700; color:#0F172A; line-height:1.4; margin-top:4px; margin-bottom:8px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis;" title="{title}">{title}</div>
                """, unsafe_allow_html=True)

                render_card_details_expander(item, cid, idx, is_reviewing=False)

                btn_c1, btn_c2 = st.columns([1.0, 1.4])
                with btn_c1:
                    if st.button("🗑️ 삭제", key=f"btn_delete_{cid}_{idx}", use_container_width=True):
                        if cid in st.session_state["saved_cases"]:
                            del st.session_state["saved_cases"][cid]
                            save_saved_cases(st.session_state["saved_cases"])
                            st.toast("사례가 보관함에서 삭제되었습니다.", icon="🗑️")
                            st.rerun()
                with btn_c2:
                    if st.button("📊 리포트 보기", key=f"btn_restore_{cid}_{idx}", use_container_width=True):
                        restore_case_to_search_view(item)





