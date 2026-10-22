# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd

from tax_manual_data import MANUAL_CATEGORIES, WIZARDS, TEMPLATES
from tax_account_master import ACCOUNTS_DATA, ACCOUNT_CATEGORIES
from tax_relations import TaxRelationEngine


from components.ui_elements import render_copy_button


def render_manual_view():
    """
    CJ프레시웨이 실무 세무 매뉴얼 & 현업 FAQ 가이드 화면을 렌더링합니다.
    """
    st.markdown("""
    <div class="compact-header">
        <div class="cj-badge">
            <span class="cj-dot"></span>
            CJ FRESHWAY · TAX INTELLIGENCE
        </div>
        <div class="service-title">📖 CJ프레시웨이 실무 세무 매뉴얼 & 현업 FAQ 가이드</div>
        <div class="service-subtitle">
            영업·MD·물류·운영 현업에서 빈번하게 발생하는 세무 의사결정을 <b>3초 판별 마법사</b>로 해결하고, <b>6대 분야별 표준 세무 매뉴얼</b> 및 <b>사내 배포용 템플릿</b>을 제공합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_wiz, tab_acc, tab_faq, tab_tmpl, tab_rel = st.tabs([
        "⚡ 3초 판별 의사결정 마법사",
        "📚 실무 계정과목 마스터 사전",
        "📂 6대 분야별 실무 FAQ & 표준 매뉴얼",
        "📄 사내 공지/현업 배포용 원클릭 템플릿",
        "👥 특수관계인 판별기"
    ])

    # -------------------------------------------------------------
    # 탭 1: 3초 판별 의사결정 마법사 (Interactive Decision Wizards)
    # -------------------------------------------------------------
    with tab_wiz:
        st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#005B45; margin:8px 0 4px 0;'>🎯 현업 실무 의사결정 시뮬레이터</div>", unsafe_allow_html=True)
        st.caption("복잡한 세법 규정을 몰라도 2~3개 질문에 응답하면 회계 계정과목, 부가가치세 공제 여부, 세무조사 필수 증빙을 즉시 도출합니다.")
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

        wiz_choice = st.radio(
            "판별기 선택",
            options=["cost_type", "sales_incentive", "inventory_loss"],
            format_func=lambda k: WIZARDS[k]["title"],
            horizontal=True,
            label_visibility="collapsed",
            key="wiz_selector"
        )
        selected_wiz = WIZARDS[wiz_choice]

        st.markdown(f"""
        <div style="background:#F0FDF4; border:1px solid #A7D7C9; border-left:5px solid #005B45; border-radius:8px; padding:14px 18px; margin:12px 0 16px 0;">
            <div style="font-size:1.02rem; font-weight:800; color:#005B45;">{selected_wiz['title']}</div>
            <div style="font-size:0.86rem; color:#475569; margin-top:4px;">{selected_wiz['desc']}</div>
        </div>
        """, unsafe_allow_html=True)

        user_answers = {}
        cols_q = st.columns(len(selected_wiz["steps"]))
        for q_idx, step in enumerate(selected_wiz["steps"]):
            with cols_q[q_idx]:
                st.markdown(f"<div style='font-size:0.88rem; font-weight:700; color:#1E293B; margin-bottom:6px;'>{step['label']}</div>", unsafe_allow_html=True)
                ans = st.selectbox(
                    step["label"],
                    options=step["options"],
                    key=f"wiz_{wiz_choice}_{step['id']}",
                    label_visibility="collapsed"
                )
                user_answers[step["id"]] = ans

        # 판정 실행
        wiz_eval = selected_wiz["evaluate"](user_answers)

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        
        # 판정 결과 카드
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1.5px solid #005B45; border-radius:10px; padding:18px 22px; box-shadow:0 4px 16px rgba(0,91,69,0.08);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; border-bottom:1px solid #E2E8F0; padding-bottom:12px; margin-bottom:14px;">
                <div>
                    <span style="font-size:1.15rem; font-weight:800;">{wiz_eval['result_badge']}</span>
                </div>
                <div>
                    <span style="font-size:0.82rem; font-weight:700; color:#005B45; background:#EBF7F2; padding:4px 10px; border-radius:20px; border:1px solid #C1E5D9;">
                        판정 항목: {wiz_eval.get('subject', '')}
                    </span>
                </div>
            </div>
            <div style="font-size:0.95rem; line-height:1.65; color:#1E293B; margin-bottom:14px;">
                {wiz_eval.get('summary', '')}
            </div>
        """, unsafe_allow_html=True)

        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown("""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 16px; height:100%;">
                <div style="font-size:0.86rem; font-weight:700; color:#003876; margin-bottom:6px;">📋 필수 구비 증빙 체크리스트</div>
            """, unsafe_allow_html=True)
            for chk in wiz_eval.get("checklist", []):
                st.markdown(f"<div style='font-size:0.83rem; color:#334155; margin-bottom:4px;'>✓ {chk}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_res2:
            st.markdown(f"""
            <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; padding:12px 16px; height:100%;">
                <div style="font-size:0.86rem; font-weight:700; color:#92400E; margin-bottom:6px;">⚠️ 실무 주의사항 및 리스크</div>
                <div style="font-size:0.83rem; color:#78350F; line-height:1.5;">{wiz_eval.get('warning', '')}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 탭 2: 실무 계정과목 마스터 사전 (Classic Catalog & Detail Guide)
    # -------------------------------------------------------------
    with tab_acc:
        st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#005B45; margin:8px 0 4px 0;'>📚 실무 빈출 25개 핵심 계정과목 마스터 사전</div>", unsafe_allow_html=True)
        st.caption("좌측 목록에서 계정과목을 클릭하면 표준 정의, 회계 분개 예시, 부가가치세 매입세액 공제 여부, 세무조정 유의사항을 바로 확인할 수 있습니다.")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        col_cat_sel, col_acc_search = st.columns([4, 2], vertical_alignment="center")
        with col_cat_sel:
            cat_opts = list(ACCOUNT_CATEGORIES.keys())
            sel_acc_cat = st.segmented_control(
                "분류 선택",
                options=cat_opts,
                format_func=lambda k: ACCOUNT_CATEGORIES[k]["title"],
                default=cat_opts[0],
                key="seg_account_cat"
            )
        with col_acc_search:
            acc_kw = st.text_input("계정과목 검색", placeholder="🔍 계정과목명 또는 코드 검색 (예: 복리, 813)", label_visibility="collapsed", key="in_acc_search")

        # 해당 카테고리의 계정과목 코드 목록 필터링
        filtered_codes = list(ACCOUNT_CATEGORIES[sel_acc_cat]["accounts"])
        if acc_kw:
            kw_clean = acc_kw.strip().lower()
            filtered_codes = [
                c for c in ACCOUNTS_DATA.keys()
                if kw_clean in ACCOUNTS_DATA[c]["name"].lower()
                or kw_clean in ACCOUNTS_DATA[c]["code"]
                or kw_clean in ACCOUNTS_DATA[c]["summary"].lower()
                or any(kw_clean in ex.lower() for ex in ACCOUNTS_DATA[c]["examples"])
            ]

        if not filtered_codes:
            st.info(f"'{acc_kw}' 검색어와 일치하는 계정과목이 없습니다.")
        else:
            col_list, col_detail = st.columns([1.6, 3.4])
            
            with col_list:
                st.markdown("<div class='acc-sidebar-marker' style='display:none;'></div>", unsafe_allow_html=True)
                st.markdown("<div style='font-size:0.82rem; font-weight:700; color:#787774; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.04em;'>📋 계정과목 목록</div>", unsafe_allow_html=True)
                
                # 선택된 계정 세션 상태
                if "sel_account_code" not in st.session_state or st.session_state["sel_account_code"] not in filtered_codes:
                    st.session_state["sel_account_code"] = filtered_codes[0]

                for code in filtered_codes:
                    acc_info = ACCOUNTS_DATA[code]
                    is_selected = (st.session_state["sel_account_code"] == code)
                    
                    btn_label = f"📄 [{acc_info['code']}] {acc_info['name']}"
                    if st.button(btn_label, key=f"btn_acc_pick_{code}", use_container_width=True, type="primary" if is_selected else "secondary"):
                        st.session_state["sel_account_code"] = code
                        st.rerun()

            with col_detail:
                curr_code = st.session_state.get("sel_account_code", filtered_codes[0])
                if curr_code in ACCOUNTS_DATA:
                    cur_acc = ACCOUNTS_DATA[curr_code]
                    cat_info = ACCOUNT_CATEGORIES.get(cur_acc["category"], {"title": "실무 계정과목"})
                    
                    # 1. 노션 스타일 페이지 컨테이너 시작
                    st.markdown(f"""
                    <div class="notion-page-card">
                        <div class="notion-page-title">
                            <span style="font-size:1.75rem; margin-right:6px;">📑</span>
                            <span>[{cur_acc['code']}] {cur_acc['name']}</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px; margin:10px 0 16px 0; flex-wrap:wrap;">
                            <span class="notion-tag notion-tag-green">🏷️ {cat_info['title']}</span>
                            <span class="notion-tag notion-tag-gray">🔤 {cur_acc['en_name']}</span>
                            <span class="notion-tag notion-tag-orange">📌 계정코드: {cur_acc['code']}</span>
                        </div>
                        <div style="font-size:0.98rem; color:#37352F; line-height:1.7; background:#FBFAF8; border-left:3.5px solid #005B45; padding:10px 16px; border-radius:0 6px 6px 0; margin-bottom:18px;">
                            {cur_acc['summary']}
                        </div>
                        <hr style="border:none; border-top:1px solid #EDEDEC; margin:16px 0 18px 0;">
                    """, unsafe_allow_html=True)

                    # 2. 주요 적용 지출 사례 (노션 그레이 콜아웃)
                    examples_html = "".join([f"<li style='margin-bottom:4px;'>{ex}</li>" for ex in cur_acc["examples"]])
                    st.markdown(f"""
                    <div class="notion-block nb-gray" style="margin-bottom:12px;">
                        <div class="notion-icon">💡</div>
                        <div class="notion-body">
                            <div class="notion-title">주요 적용 지출 사례</div>
                            <ul style="margin:6px 0 0 16px; padding:0; color:#37352F; font-size:0.90rem; line-height:1.6;">
                                {examples_html}
                            </ul>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 3. 부가가치세 & 법인세 세무조정 (그린 & 옐로우 콜아웃 2열)
                    col_dt_vat, col_dt_adj = st.columns(2)
                    with col_dt_vat:
                        st.markdown(f"""
                        <div class="notion-block nb-green" style="height:100%; margin:0;">
                            <div class="notion-icon">🧾</div>
                            <div class="notion-body">
                                <div class="notion-title" style="color:#0F5132;">부가가치세 매입세액 공제</div>
                                <div style="font-size:0.88rem; color:#1C3829; line-height:1.6; margin-top:4px;">
                                    {cur_acc['vat_rule']}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_dt_adj:
                        tax_adj_formatted = cur_acc['tax_adjustment'].replace('\n', '<br>')
                        st.markdown(f"""
                        <div class="notion-block nb-yellow" style="height:100%; margin:0;">
                            <div class="notion-icon">⚖️</div>
                            <div class="notion-body">
                                <div class="notion-title" style="color:#8F5B00;">법인세 손금산입 & 세무조정</div>
                                <div style="font-size:0.88rem; color:#49290E; line-height:1.6; margin-top:4px;">
                                    {tax_adj_formatted}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

                    # 4. 표준 회계 전표 분개 (노션 코드/전표 블록)
                    journal_escaped = cur_acc['journal'].replace('\n', '<br>')
                    st.markdown(f"""
                    <div class="notion-block nb-gray" style="border-radius:8px; margin-bottom:12px;">
                        <div class="notion-icon">💼</div>
                        <div class="notion-body" style="width:100%;">
                            <div class="notion-title">표준 회계 전표 분개 예시</div>
                            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:12px 14px; margin-top:8px; font-family:'Courier New', Consolas, monospace; font-size:0.87rem; color:#1E293B; line-height:1.7;">
                                {journal_escaped}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 5. 실무 필수 유의사항 & 리스크 (노션 레드 콜아웃)
                    precautions_html = "".join([f"<div style='margin-bottom:6px;'>⚠️ {p}</div>" for p in cur_acc["precautions"]])
                    checklist_tags = " ".join([f"<span class='notion-tag notion-tag-blue'>✓ {c}</span>" for c in cur_acc.get("checklist", [])])
                    
                    st.markdown(f"""
                    <div class="notion-block nb-red" style="margin-bottom:12px;">
                        <div class="notion-icon">🚨</div>
                        <div class="notion-body">
                            <div class="notion-title" style="color:#A11515;">실무 필수 유의사항 & 세무조사 리스크</div>
                            <div style="font-size:0.88rem; color:#5D1715; line-height:1.6; margin-top:6px;">
                                {precautions_html}
                            </div>
                            <div style="margin-top:10px; padding-top:10px; border-top:1px dashed #F8D7DA;">
                                <div style="font-size:0.82rem; font-weight:700; color:#5D1715; margin-bottom:6px;">📎 필수 구비 증빙 서류:</div>
                                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                                    {checklist_tags}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 6. 유사 계정과목 구분 (노션 블루 콜아웃)
                    st.markdown(f"""
                    <div class="notion-block nb-cjblue" style="margin-bottom:8px;">
                        <div class="notion-icon">🔄</div>
                        <div class="notion-body">
                            <div class="notion-title" style="color:#003876;">유사 계정과목 구분 및 주의사항</div>
                            <div style="font-size:0.88rem; color:#0B2937; line-height:1.6; margin-top:4px;">
                                {cur_acc['compare']}
                            </div>
                        </div>
                    </div>
                    </div> <!-- notion-page-card 닫기 -->
                    """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 탭 3: 6대 분야별 실무 FAQ & 표준 매뉴얼 (FAQ Accordion)
    # -------------------------------------------------------------
    with tab_faq:
        col_faq_h, col_faq_srch = st.columns([3.5, 2.5], vertical_alignment="center")
        with col_faq_h:
            st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#005B45;'>📂 6대 실무 카테고리별 표준 매뉴얼 & FAQ</div>", unsafe_allow_html=True)
            st.caption("카테고리를 클릭하거나 키워드를 검색하여 관련 법령, 회계 전표 분개, 실무 팁을 확인하세요.")
        with col_faq_srch:
            faq_keyword = st.text_input("FAQ 검색", placeholder="🔍 키워드 검색 (예: 경조사비, 수정세금계산서, 간이영수증)", label_visibility="collapsed", key="in_faq_search")

        cat_keys = list(MANUAL_CATEGORIES.keys())
        selected_cat_key = st.segmented_control(
            "카테고리 선택",
            options=cat_keys,
            format_func=lambda k: MANUAL_CATEGORIES[k]["title"],
            default=cat_keys[0],
            key="seg_manual_cat"
        )
        
        cat_data = MANUAL_CATEGORIES[selected_cat_key]
        st.markdown(f"<div style='font-size:0.84rem; color:#64748B; margin:8px 0 12px 0;'>💡 {cat_data['desc']}</div>", unsafe_allow_html=True)

        rendered_cnt = 0
        for faq in cat_data["faqs"]:
            if faq_keyword and (faq_keyword.lower() not in faq["q"].lower() and faq_keyword.lower() not in faq["summary"].lower() and faq_keyword.lower() not in " ".join(faq["rules"]).lower()):
                continue

            rendered_cnt += 1
            with st.expander(f"Q. {faq['q']}", expanded=(rendered_cnt == 1)):
                st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #A7D7C9; border-radius:6px; padding:10px 14px; margin-bottom:12px;">
                    <span style="font-weight:800; color:#005B45; font-size:0.88rem;">[핵심 요약]</span>
                    <span style="color:#065F46; font-size:0.88rem; margin-left:6px; font-weight:600;">{faq['summary']}</span>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("##### 📜 표준 업무 처리 지침")
                for r in faq["rules"]:
                    st.markdown(f"- {r}")

                col_acc, col_leg = st.columns([1.5, 1.0])
                with col_acc:
                    st.markdown("##### 💼 표준 회계 전표 분개")
                    st.code(faq["accounting"], language="markdown")
                with col_leg:
                    st.markdown("##### ⚖️ 관련 법적 근거")
                    st.markdown(f"<div style='font-size:0.84rem; color:#475569; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:10px;'>{faq['legal_basis']}</div>", unsafe_allow_html=True)

                st.markdown(f"""
                <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:6px; padding:10px 14px; margin-top:10px;">
                    <span style="font-size:0.84rem; font-weight:700; color:#92400E;">💡 실무 적용 팁: </span>
                    <span style="font-size:0.84rem; color:#78350F;">{faq['action_tip']}</span>
                </div>
                """, unsafe_allow_html=True)

        if rendered_cnt == 0:
            st.info(f"'{faq_keyword}'에 부합하는 FAQ 질의가 이 카테고리에 없습니다. 다른 검색어나 카테고리를 선택해 보세요.")

    # -------------------------------------------------------------
    # 탭 4: 사내 공지/현업 배포용 원클릭 템플릿 (Templates)
    # -------------------------------------------------------------
    with tab_tmpl:
        st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#005B45; margin:8px 0 4px 0;'>📄 현업 부서 배포용 표준 공지 템플릿</div>", unsafe_allow_html=True)
        st.caption("현업(영업, MD, 물류, 사업장)에 사내 메신저나 이메일로 바로 공지할 수 있는 완성형 지침 텍스트입니다. 원클릭으로 복사하여 활용하세요.")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        for tmpl_key, tmpl in TEMPLATES.items():
            st.markdown(f"""
            <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:14px 18px; margin-bottom:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span style="font-size:0.96rem; font-weight:800; color:#0F172A;">{tmpl['title']}</span>
                </div>
            """, unsafe_allow_html=True)
            col_t_body, col_t_btn = st.columns([5, 1], vertical_alignment="top")
            with col_t_body:
                st.code(tmpl["content"], language="markdown")
            with col_t_btn:
                render_copy_button(tmpl["content"], f"cp_tmpl_{tmpl_key}")
            st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 탭 5: 지배구조 기반 특수관계자 판별기 (Relations)
    # -------------------------------------------------------------
    with tab_rel:
        if "rel_shares" not in st.session_state:
            st.session_state["rel_shares"] = [
                {"company": "법인A", "shareholder": "갑", "ratio": 40.0},
                {"company": "법인A", "shareholder": "을", "ratio": 30.0},
                {"company": "법인A", "shareholder": "병", "ratio": 30.0},
                {"company": "법인B", "shareholder": "법인A", "ratio": 100.0},
                {"company": "법인B", "shareholder": "정", "ratio": 0.0},
            ]
        if "rel_kinships" not in st.session_state:
            st.session_state["rel_kinships"] = [
                {"person1": "갑", "person2": "을", "relation": "배우자"}
            ]
        if "rel_execs" not in st.session_state:
            st.session_state["rel_execs"] = [
                {"person": "갑", "company": "법인A", "role": "대표이사"},
                {"person": "정", "company": "법인B", "role": "대표이사"}
            ]

        tab_input, tab_res = st.tabs(["📝 1단계: 지배구조 및 주주·친족 정보 입력", "🎯 2단계: 기준 주체별 특관자 판정 리포트"])

        with tab_input:
            col_preset, col_reset = st.columns([4, 1.2], vertical_alignment="center")
            with col_preset:
                st.markdown("<div style='font-size:0.90rem; font-weight:700; color:#1E293B;'>⚡ 실무 구조도 프리셋 불러오기</div>", unsafe_allow_html=True)
            with col_reset:
                if st.button("🔄 기본 예시로 초기화", key="btn_reset_rel", use_container_width=True):
                    st.session_state["rel_shares"] = [
                        {"company": "법인A", "shareholder": "갑", "ratio": 40.0},
                        {"company": "법인A", "shareholder": "을", "ratio": 30.0},
                        {"company": "법인A", "shareholder": "병", "ratio": 30.0},
                        {"company": "법인B", "shareholder": "법인A", "ratio": 100.0},
                        {"company": "법인B", "shareholder": "정", "ratio": 0.0},
                    ]
                    st.session_state["rel_kinships"] = [
                        {"person1": "갑", "person2": "을", "relation": "배우자"}
                    ]
                    st.session_state["rel_execs"] = [
                        {"person": "갑", "company": "법인A", "role": "대표이사"},
                        {"person": "정", "company": "법인B", "role": "대표이사"}
                    ]
                    st.toast("기본 예시 구조도로 초기화되었습니다.", icon="🔄")
                    st.rerun()

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            st.markdown("##### 🏢 1. 법인별 주주 출자 지분율 구조")
            st.caption("회사명, 주주명(개인 또는 모법인), 지분율(%)을 입력하세요. (자회사, 손자회사 등 다단계 출자 모두 지원)")
            df_shares = pd.DataFrame(st.session_state["rel_shares"])
            edited_shares = st.data_editor(
                df_shares,
                num_rows="dynamic",
                column_config={
                    "company": st.column_config.TextColumn("법인명(피출자회사)", required=True),
                    "shareholder": st.column_config.TextColumn("주주명(개인/법인)", required=True),
                    "ratio": st.column_config.NumberColumn("지분율 (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f%%", required=True)
                },
                use_container_width=True,
                key="editor_shares"
            )
            st.session_state["rel_shares"] = edited_shares.to_dict("records")

            col_mid1, col_mid2 = st.columns(2)
            with col_mid1:
                st.markdown("##### 👨‍👩‍👧‍👦 2. 주요 주주 간 친족 관계")
                st.caption("배우자(사실혼 포함), 4촌 이내 혈족, 3촌 이내 인척 관계를 입력하세요.")
                df_kin = pd.DataFrame(st.session_state["rel_kinships"])
                edited_kin = st.data_editor(
                    df_kin,
                    num_rows="dynamic",
                    column_config={
                        "person1": st.column_config.TextColumn("주주 1", required=True),
                        "person2": st.column_config.TextColumn("주주 2", required=True),
                        "relation": st.column_config.SelectboxColumn("친족 관계", options=["배우자", "직계존비속(부모/자녀)", "형제자매(2촌)", "4촌이내혈족", "3촌이내인척", "생계유지자"], required=True)
                    },
                    use_container_width=True,
                    key="editor_kin"
                )
                st.session_state["rel_kinships"] = edited_kin.to_dict("records")

            with col_mid2:
                st.markdown("##### 👔 3. 임원(등기/미등기/대표이사) 현황")
                st.caption("각 법인의 대표이사 또는 등기/미등기 임원으로 재직 중인 주주·개인을 입력하세요.")
                df_ex = pd.DataFrame(st.session_state["rel_execs"])
                edited_ex = st.data_editor(
                    df_ex,
                    num_rows="dynamic",
                    column_config={
                        "person": st.column_config.TextColumn("임원 성명", required=True),
                        "company": st.column_config.TextColumn("소속 법인명", required=True),
                        "role": st.column_config.SelectboxColumn("직책", options=["대표이사", "등기임원", "미등기임원", "지배적사용인", "직원"], required=True)
                    },
                    use_container_width=True,
                    key="editor_exec"
                )
                st.session_state["rel_execs"] = edited_ex.to_dict("records")

        with tab_res:
            engine = TaxRelationEngine()
            engine.load_structure(
                st.session_state["rel_shares"],
                st.session_state["rel_kinships"],
                st.session_state["rel_execs"]
            )

            all_entities = sorted(list(engine.entities.keys()))
            if not all_entities:
                st.warning("먼저 1단계에서 주주 및 법인 정보를 최소 1건 이상 입력해 주세요.")
            else:
                col_f_target, col_f_law, col_f_btn = st.columns([3.5, 2.5, 1.5], vertical_alignment="center")
                with col_f_target:
                    sel_subject = st.selectbox(
                        "🎯 분석 기준 주체 선택 (누구를 기준으로 특관자를 찾을까요?)",
                        options=all_entities,
                        index=0,
                        key="sb_subject_choice"
                    )
                with col_f_law:
                    sel_law = st.selectbox(
                        "⚖️ 적용 법률 기준",
                        options=["법인세법 (부당행위/가지급금)", "상속세및증여세법 (일감몰아주기/저가양수)", "국세기본법 (제2차납세의무)"],
                        index=0,
                        key="sb_law_choice"
                    )
                with col_f_btn:
                    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                    run_eval = st.button("🚀 특관자 정밀 판별", key="btn_run_eval", type="primary", use_container_width=True)

                law_keyword = "법인세법" if "법인세" in sel_law else ("상증세법" if "상속" in sel_law else "국세기본법")
                analysis = engine.analyze_relations(sel_subject, law_type=law_keyword)

                sub_type = analysis["subject_type"]
                rel_cnt = analysis["related_count"]
                tot_cnt = analysis["total_targets"]

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-left:5px solid #005B45; border-radius:8px; padding:14px 18px; margin-bottom:18px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                        <div>
                            <span style="font-size:0.84rem; font-weight:700; color:#005B45; background:#DCFCE7; padding:3px 8px; border-radius:4px;">
                                🎯 분석 기준: {sel_subject} ({sub_type})
                            </span>
                            <span style="font-size:0.84rem; font-weight:700; color:#1E3A8A; background:#DBEAFE; padding:3px 8px; border-radius:4px; margin-left:6px;">
                                ⚖️ {sel_law.split()[0]}
                            </span>
                            <div style="font-size:1.15rem; font-weight:800; color:#0F172A; margin-top:6px;">
                                총 {tot_cnt}개 주체 중 <span style="color:#DC2626; font-size:1.28rem;">{rel_cnt}명(개사)</span>이 법률상 특수관계인에 해당합니다.
                            </div>
                        </div>
                        <div style="font-size:0.82rem; color:#475569; text-align:right;">
                            ※ 쌍방관계 원칙(타방 특관자 포함) 및 최신 친족 범위(4촌/3촌) 완벽 적용
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### 📋 특수관계 성립 대상자 명부 및 법적 사유 요약")
            
                table_rows = []
                for item in analysis["items"]:
                    tar = item["target"]
                    t_type = item["target_type"]
                    stat = item["status"]
                    rtype = item["rel_type"]
                    basis = item["legal_basis"]

                    badge_color = "#DC2626" if item["is_related"] else "#64748B"
                    badge_bg = "#FEE2E2" if item["is_related"] else "#F1F5F9"
                    stat_html = f'<span style="background:{badge_bg}; color:{badge_color}; font-weight:700; padding:2px 8px; border-radius:4px;">{stat}</span>'

                    table_rows.append({
                        "대상자": f"{tar} ({t_type})",
                        "특수관계 여부": stat_html,
                        "관계 유형": rtype,
                        "적용 법조항 및 판단 근거": basis
                    })

                df_display = pd.DataFrame(table_rows)
                st.markdown(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

                st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

                clip_lines = [
                    f"■ [CJ프레시웨이] 세법상 특수관계인 판정 보고서",
                    f"1. 분석 기준 주체: {sel_subject} ({sub_type})",
                    f"2. 검토 적용 법률: {sel_law}",
                    f"3. 총 검토 대상: {tot_cnt}명(사) 중 특수관계 성립 {rel_cnt}명(사)",
                    f"",
                    f"4. 특수관계 성립 상세 내역:"
                ]
                for it in analysis["items"]:
                    if it["is_related"]:
                        clip_lines.append(f" - [{it['target']}] ({it['rel_type']})")
                        clip_lines.append(f"   · 법적 근거: {it['legal_basis']}")

                clip_lines.append("\n※ 본 검토서는 법인세법 제2조 제12호 및 동법 시행령 제2조 제5항/제6항(쌍방주의), 국세기본법 제2조 제20호를 근거로 산출되었습니다.")
                full_clip_text = "\n".join(clip_lines)

                col_clip_t, col_clip_btn = st.columns([4, 1.5], vertical_alignment="center")
                with col_clip_t:
                    st.markdown("##### 📄 사내 보고용 판정 결과 전문")
                with col_clip_btn:
                    render_copy_button(full_clip_text, f"cp_rel_{hash(sel_subject)}")

                st.code(full_clip_text, language="markdown")
