# ----------------- 특수관계자 판별기 전용 렌더러 -----------------
def render_tax_relations_view():
    """지배구조(출자/친족/임원) 기반 특수관계자 판별기 뷰"""
    st.markdown("""
    <div class="compact-header">
        <div class="cj-badge">
            <span class="cj-dot"></span>
            CJ FRESHWAY · TAX INTELLIGENCE
        </div>
        <div class="service-title">👥 지배구조 기반 세법상 특수관계인(특수관계자) 정밀 판별기</div>
        <div class="service-subtitle">
            법인 및 주주 출자 지분율, 친족 관계(배우자·4촌이내 혈족·3촌이내 인척), 임원 현황을 바탕으로<br>
            선택한 기준 주체(법인 또는 개인)와 <b>법인세법·국세기본법·상증세법상 특수관계가 성립하는 전원</b>과 그 <b>법적 조항 근거</b>를 일괄 도출합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 기본 샘플 데이터 초기화
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

    # 상단 탭: [ 📊 구조도 입력 및 편집 ] vs [ 🎯 특관자 판별 결과 리포트 ]
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

        # 1. 지분율 데이터 에디터
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
        # 엔진 구동
        engine = TaxRelationEngine()
        engine.load_structure(
            st.session_state["rel_shares"],
            st.session_state["rel_kinships"],
            st.session_state["rel_execs"]
        )

        all_entities = sorted(list(engine.entities.keys()))
        if not all_entities:
            st.warning("먼저 1단계에서 주주 및 법인 정보를 최소 1건 이상 입력해 주세요.")
            return

        # 기준 주체 선택 툴바
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

        # 분석 실행
        law_keyword = "법인세법" if "법인세" in sel_law else ("상증세법" if "상속" in sel_law else "국세기본법")
        analysis = engine.analyze_relations(sel_subject, law_type=law_keyword)

        # 상단 핵심 요약 지표 카드
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

        # 결과 테이블 및 카드 렌더링
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

        # 클립보드 복사 영역
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