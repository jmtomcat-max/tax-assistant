# 화면 4: 부가가치세 가산세 계산기 (VAT Penalty View - 중복적용 배제 & 법령 메타데이터)
# =========================================================================
elif st.session_state["active_view"] == "penalty":
    st.markdown("""
    <div class="compact-header">
        <div class="cj-badge">
            <span class="cj-dot"></span>
            CJ FRESHWAY · TAX INTELLIGENCE
        </div>
        <div class="service-title">🧮 부가가치세 세금계산서 가산세 계산기 (법령 기준일 & 중복적용 배제)</div>
        <div class="service-subtitle">
            유통업 실무에서 빈번하게 발생하는 세금계산서 지연발급·미발급·전송지연·합계표 누락 등 가산세를 계산합니다.<br>
            <b>거래일자별 법정 세율·한도 마스터(tax_rates.json)</b>와 <b>부가가치세법 제60조 제9항(가산세 중복 적용의 배제)</b>을 엄격하게 적용합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. 거래 기본 정보 및 거래일자 입력 영역
    st.markdown("##### 💼 1. 거래 기본 정보 및 적용 거래일자 입력")
    col_p0, col_p1, col_p2, col_p3 = st.columns([2, 3, 2, 2.5], vertical_alignment="center")
    
    with col_p0:
        import datetime
        v_trans_date = st.date_input(
            "📅 거래/공급일자",
            value=datetime.date.today(),
            help="거래일자 기준으로 당시 시행 중이던 검증된 세율을 자동 적용합니다.",
            key="input_vat_trans_date"
        )
        trans_date_str = v_trans_date.strftime("%Y-%m-%d")

    with col_p1:
        v_supply_val = st.number_input(
            "거래 공급가액 (원)",
            min_value=0,
            value=st.session_state.get("vat_calc_supply", 100000000), # 기본 1억원
            step=1000000,
            format="%d",
            key="input_vat_supply"
        )
        st.session_state["vat_calc_supply"] = v_supply_val

    with col_p2:
        v_trans_type = st.radio(
            "거래 유형",
            options=["매출 (공급자)", "매입 (공급받는자)"],
            horizontal=True,
            key="radio_vat_trans_type"
        )
        trans_keyword = "매출" if "매출" in v_trans_type else "매입"

    with col_p3:
        v_tax_val = int(v_supply_val * 0.1)
        st.markdown(f"""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:8px 12px;">
            <div style="font-size:0.72rem; color:#64748B;">부가가치세액 (10%) · 적용일자: {trans_date_str}</div>
            <div style="font-size:1.05rem; font-weight:700; color:#0F172A;">{v_tax_val:,} 원</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # 2. 위반 유형 체크리스트
    st.markdown(f"##### ⚠️ 2. {trans_keyword} 관련 세법상 위반 항목 선택 (다중 선택 가능)")
    st.caption(f"※ 실무에서 발생한 위반 행위를 체크하세요. [{trans_date_str}] 기준 유효하며 검증(verified)된 법정 세율이 적용됩니다.")

    selected_violations = []

    if trans_keyword == "매출":
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("<div style='font-size:0.86rem; font-weight:700; color:#003876; margin-bottom:6px;'>[세금계산서 발급/전송 관련]</div>", unsafe_allow_html=True)
            chk_m_no = st.checkbox("❌ 세금계산서 미발급 (2.0%)", help="공급시기 속하는 과세기간 확정신고기한까지 미발급", key="chk_m_no")
            chk_m_late = st.checkbox("⏳ 세금계산서 지연발급 (1.0%)", help="공급시기 경과 후 확정신고기한 내 발급", key="chk_m_late")
            chk_m_fake = st.checkbox("🚨 가공(무거래/가짜) 세금계산서 발급 (3.0%)", help="재화·용역 공급 없이 세금계산서만 수수", key="chk_m_fake")
            chk_m_shadow = st.checkbox("👤 위장(타인명의) 세금계산서 발급 (2.0%)", help="실제 공급자가 아닌 타인 명의로 발급", key="chk_m_shadow")
            chk_m_diff = st.checkbox("📝 사실과 다른 세금계산서(부실기재) (1.0%)", help="필요적 기재사항 착오 또는 사실과 다르게 기재", key="chk_m_diff")

        with col_m2:
            st.markdown("<div style='font-size:0.86rem; font-weight:700; color:#005B45; margin-bottom:6px;'>[국세청 전송 및 합계표 관련]</div>", unsafe_allow_html=True)
            chk_m_notx = st.checkbox("📡 전자세금계산서 미전송 (0.5%)", help="발급일 다음 날까지 미전송 (확정신고기한 경과 후 전송)", key="chk_m_notx")
            chk_m_latetx = st.checkbox("⏱️ 전자세금계산서 지연전송 (0.3%)", help="발급일 다음 날 경과 후 확정신고기한 내 전송", key="chk_m_latetx")
            chk_m_nosum = st.checkbox("📊 매출처별 합계표 미제출/부실기재 (0.5%)", help="합계표 미제출 또는 거래처별 기재사항 누락·오류", key="chk_m_nosum")
            chk_m_latesum = st.checkbox("📑 매출처별 합계표 지연제출 (0.3%)", help="예정신고 누락분을 확정신고 시 제출", key="chk_m_latesum")

        if chk_m_no: selected_violations.append("세금계산서_미발급")
        if chk_m_late: selected_violations.append("세금계산서_지연발급")
        if chk_m_fake: selected_violations.append("가공_세금계산서_발급")
        if chk_m_shadow: selected_violations.append("위장_세금계산서_발급")
        if chk_m_diff: selected_violations.append("사실과다른_세금계산서_발급")
        if chk_m_notx: selected_violations.append("전자세금계산서_미전송")
        if chk_m_latetx: selected_violations.append("전자세금계산서_지연전송")
        if chk_m_nosum: selected_violations.append("매출처별합계표_미제출")
        if chk_m_latesum: selected_violations.append("매출처별합계표_지연제출")

    else:
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            st.markdown("<div style='font-size:0.86rem; font-weight:700; color:#003876; margin-bottom:6px;'>[매입 세금계산서 수취 관련]</div>", unsafe_allow_html=True)
            chk_in_late = st.checkbox("⏳ 세금계산서 지연수취 (0.5%)", help="공급시기 경과 후 확정신고기한 내 수취 (매입세액공제 가능)", key="chk_in_late")
            chk_in_fake = st.checkbox("🚨 가공(무거래) 세금계산서 수취 (3.0%)", help="매입세액 전액 불공제 + 3% 가산세", key="chk_in_fake")
            chk_in_shadow = st.checkbox("👤 위장(타인명의) 세금계산서 수취 (2.0%)", help="매입세액 전액 불공제 + 2% 가산세", key="chk_in_shadow")

        with col_in2:
            st.markdown("<div style='font-size:0.86rem; font-weight:700; color:#005B45; margin-bottom:6px;'>[매입처별 합계표 관련]</div>", unsafe_allow_html=True)
            chk_in_sum = st.checkbox("📊 매입처별 합계표 미제출/부실기재 (0.5%)", help="매입처별 합계표 미제출 또는 부실기재", key="chk_in_sum")

        if chk_in_late: selected_violations.append("세금계산서_지연수취")
        if chk_in_fake: selected_violations.append("가공_세금계산서_수취")
        if chk_in_shadow: selected_violations.append("위장_세금계산서_수취")
        if chk_in_sum: selected_violations.append("매입처별합계표_불성실")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # 3. 국세기본법 신고불성실 및 납부지연 가산세 연동 옵션
    with st.expander("➕ [선택] 부가가치세 과소신고 및 납부지연 가산세 동시 계산 (수정신고 감면 적용)", expanded=False):
        col_rep1, col_rep2, col_rep3 = st.columns([2, 2, 2.5])
        with col_rep1:
            use_rep = st.checkbox("과소신고/납부지연 포함", value=False, key="chk_use_rep")
        with col_rep2:
            delay_days_val = st.number_input("납부지연 경과일수 (일)", min_value=0, max_value=3650, value=90, step=10, key="in_delay_days")
        with col_rep3:
            amend_opt = st.selectbox(
                "수정신고 시점 (국세기본법 제48조 감면)",
                options=["1개월이내 (75% 감면)", "3개월이내 (50% 감면)", "6개월이내 (30% 감면)", "1년이내 (20% 감면)", "1년6개월이내 (15% 감면)", "2년이내 (10% 감면)", "미신고/경정 (감면 없음)"],
                index=1,
                key="sb_amend_opt"
            )
            amend_code = amend_opt.split()[0]

    # 가산세 엔진 계산 실행 (거래일자 전달)
    pen_engine = VatPenaltyEngine()
    calc_res = pen_engine.calculate(
        supply_value=v_supply_val,
        trans_type=trans_keyword,
        selected_violations=selected_violations,
        include_reporting_penalty=st.session_state.get("chk_use_rep", False),
        unpaid_tax_amount=v_tax_val,
        delay_days=delay_days_val if st.session_state.get("chk_use_rep", False) else 0,
        is_fraud=("가공_세금계산서_발급" in selected_violations or "가공_세금계산서_수취" in selected_violations),
        amendment_period=amend_code if st.session_state.get("chk_use_rep", False) else "미신고/경정",
        transaction_date=trans_date_str
    )

    # 4. 가산세 계산 결과 및 중복배제 리포트
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    grand_tot = calc_res["grand_total"]
    vat_tot = calc_res["vat_penalty_total"]
    rep_tot = calc_res["reporting_penalty_total"]
    saved_tot = calc_res["saved_amount"]

    # 핵심 총괄 카드 (기준일 및 검증 상태 표시)
    st.markdown(f"""
    <div style="background:#FFF1F2; border:1px solid #FECDD3; border-left:5px solid #E61E2B; border-radius:8px; padding:16px 20px; margin-bottom:18px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <span style="font-size:0.84rem; font-weight:700; color:#9F1239; background:#FFE4E6; padding:3px 8px; border-radius:4px;">
                    🚨 최종 부담 가산세 합계
                </span>
                <span style="font-size:0.84rem; font-weight:700; color:#1E3A8A; background:#DBEAFE; padding:3px 8px; border-radius:4px; margin-left:6px;">
                    공급가액 {v_supply_val:,}원 기준
                </span>
                <span style="font-size:0.80rem; font-weight:700; color:#065F46; background:#ECFDF5; border:1px solid #A7F3D0; padding:3px 8px; border-radius:4px; margin-left:6px;">
                    📅 적용 기준일: {calc_res['transaction_date']} (verified)
                </span>
                <div style="font-size:1.6rem; font-weight:900; color:#E61E2B; margin-top:6px;">
                    {int(grand_tot):,} 원
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.86rem; color:#475569;">
                    · 세금계산서 가산세: <b>{int(vat_tot):,}원</b><br>
                    · 신고/납부지연 가산세: <b>{int(rep_tot):,}원</b>
                </div>
                <div style="font-size:0.84rem; font-weight:700; color:#005B45; margin-top:4px;">
                    🛡️ 중복배제로 절감된 금액: <b>{int(saved_tot):,}원</b>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 5. 중복적용 배제 상세 내역 박스
    if calc_res["excluded_records"]:
        st.markdown("""
        <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; padding:12px 16px; margin-bottom:16px;">
            <div style="font-size:0.90rem; font-weight:700; color:#065F46; display:flex; align-items:center; gap:6px;">
                <span>🛡️ 부가가치세법 제60조 제9항에 따른 '중복적용 배제' 면제 내역</span>
            </div>
            <div style="font-size:0.82rem; color:#047857; margin-top:4px;">
                동일한 거래 행위에 대해 이중 처벌을 방지하기 위하여 아래 가산세 항목은 세법에 의해 자동으로 부과 면제되었습니다:
            </div>
        </div>
        """, unsafe_allow_html=True)

        for ex in calc_res["excluded_records"]:
            st.markdown(f"""
            <div style="background:#F8FAFC; border:1px dashed #CBD5E1; border-radius:6px; padding:10px 14px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:700; color:#64748B; text-decoration:line-through;">
                        {ex['item']['name']} ({ex['item']['rate_str']}) - {int(ex['item']['raw_amount']):,}원
                    </span>
                    <span style="font-size:0.80rem; font-weight:700; background:#DCFCE7; color:#005B45; padding:2px 8px; border-radius:4px;">
                        [중복배제 면제]
                    </span>
                </div>
                <div style="font-size:0.80rem; color:#475569; margin-top:4px;">
                    ⚖️ 면제 근거: {ex['reason']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 6. 최종 부과 대상 가산세 명세서 테이블 (요구사항 7: 적용 세율, 기준일, 법령근거, 마지막 확인일 표시)
    st.markdown("#### 📋 최종 고지 대상 가산세 상세 명세표 (법령 메타데이터 포함)")
    table_items = []
    for it in calc_res["active_vat_items"]:
        src_link = f"<a href='{it['source_url']}' target='_blank' style='color:#003876; text-decoration:underline;'>법제처 원문</a>" if it.get("source_url") else "-"
        table_items.append({
            "가산세 구분": it["category"],
            "적용 항목명": it["name"],
            "적용 세율": f"<b>{it['rate_str']}</b>",
            "기준일": it.get("effective_start", "-"),
            "마지막 확인일": it.get("last_verified_date", "-"),
            "과세표준": f"{int(it['base']):,} 원",
            "산출 가산세액": f"<b style='color:#E61E2B;'>{int(it['final_amount']):,} 원</b>",
            "법령 근거": f"{it['legal_basis']} ({src_link})"
        })

    for rp in calc_res["reporting_items"]:
        src_link = f"<a href='{rp.get('source_url', '')}' target='_blank' style='color:#003876; text-decoration:underline;'>법제처 원문</a>" if rp.get("source_url") else "-"
        table_items.append({
            "가산세 구분": rp["category"],
            "적용 항목명": rp["name"],
            "적용 세율": f"<b>{rp['rate_str']}</b>",
            "기준일": calc_res["transaction_date"],
            "마지막 확인일": rp.get("last_verified_date", "2026-01-01"),
            "과세표준": f"{int(rp['base']):,} 원",
            "산출 가산세액": f"<b style='color:#E61E2B;'>{int(rp['final_amount']):,} 원</b>",
            "법령 근거": f"{rp['legal_basis']} ({rp['reduction_str']}) ({src_link})"
        })

    if table_items:
        df_pen = pd.DataFrame(table_items)
        st.markdown(df_pen.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.info("선택된 위반 항목이 없습니다. 상단에서 거래 위반 유형을 체크해 주세요.")

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # 7. 사내 보고용 텍스트 클립보드 복사
    clip_lines = [
        f"■ [CJ프레시웨이] 부가가치세 세금계산서 가산세 검토 보고서",
        f"1. 검토 대상 거래: {trans_keyword} 거래 (공급가액: {int(v_supply_val):,}원 / 부가세: {v_tax_val:,}원)",
        f"2. 적용 거래일자/기준일: {calc_res['transaction_date']} (공식 DB 검증된 세율 적용)",
        f"3. 최종 예상 가산세 합계: {int(grand_tot):,} 원",
        f"   - 세금계산서 관련 가산세: {int(vat_tot):,} 원",
        f"   - 신고불성실 및 납부지연 가산세: {int(rep_tot):,} 원",
        f"",
        f"4. 중복적용 배제(법 제60조 제9항) 절감액: {int(saved_tot):,} 원",
        f"5. 세부 적용 항목:"
    ]
    for it in calc_res["active_vat_items"]:
        clip_lines.append(f"   · {it['name']} (적용세율: {it['rate_str']} | 기준일: {it.get('effective_start','-')} | 확인일: {it.get('last_verified_date','-')}): {int(it['final_amount']):,}원 [{it['legal_basis']}]")
    for rp in calc_res["reporting_items"]:
        clip_lines.append(f"   · {rp['name']} (적용세율: {rp['rate_str']}): {int(rp['final_amount']):,}원 [{rp['legal_basis']}]")

    if calc_res["excluded_records"]:
        clip_lines.append("\n6. 중복배제 면제 항목:")
        for ex in calc_res["excluded_records"]:
            clip_lines.append(f"   · [면제] {ex['item']['name']} ({int(ex['item']['raw_amount']):,}원) - 사유: {ex['reason']}")

    clip_lines.append("\n※ 본 검토서는 부가가치세법 제60조(가산세) 및 국세기본법 제47조~제48조(tax_rates.json 마스터)를 근거로 산출되었습니다.")
    full_vat_clip = "\n".join(clip_lines)

    col_cp_t, col_cp_b = st.columns([4, 1.5], vertical_alignment="center")
    with col_cp_t:
        st.markdown("##### 📄 사내 보고용 가산세 검토의견서 전문")
    with col_cp_b:
        render_copy_button(full_vat_clip, f"cp_vat_{hash(str(grand_tot))}")

    st.code(full_vat_clip, language="markdown")

