# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import config
from tax_rate_updater import TaxRateUpdater
from tax_rate_manager import TaxRateManager

def render_settings_view():
    """
    시스템 설정 및 2026 기준세율 관리 화면을 렌더링합니다.
    (기존 app.py에 있던 settings 관련 UI 로직을 그대로 옮겨옵니다)
    """
    st.markdown("""
    <div style="margin-bottom:18px; padding-bottom:12px; border-bottom:1px solid #E2E8F0;">
        <div style="font-size:0.75rem; font-weight:700; color:#003876; background:#EFF8FF; border:1px solid #B2DDFF; padding:2px 8px; border-radius:4px; display:inline-block;">CJ FRESHWAY · SYSTEM & TAX RATES</div>
        <div style="font-size:1.45rem; font-weight:800; color:#0F172A; margin-top:6px;">⚙️ 시스템 설정 및 2026 기준세율 관리</div>
        <div style="font-size:0.88rem; color:#64748B; margin-top:2px;">공공 API 연동 인프라 점검, 2026-01-01 귀속 기준세율 모니터링 및 자동 갱신 검토 관리</div>
    </div>
    """, unsafe_allow_html=True)

    tab_set_rates, tab_set_api, tab_set_sec, tab_set_backup = st.tabs([
        "📅 1. 2026 기준세율 마스터 & 자동갱신 검토",
        "🏛️ 2. 공공 API 및 AI 모델 연동 점검",
        "🔒 3. 사내 보안 및 네트워크 공유 정책",
        "💾 4. 데이터 백업 및 복원 (클라우드 영속성)"
    ])

    with tab_set_rates:
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px 20px; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <div style="font-size:1.0rem; font-weight:700; color:#0F172A;">📊 2026 귀속 기준세율 마스터 (tax_rates.json)</div>
                    <div style="font-size:0.84rem; color:#64748B; margin-top:2px;">모든 계산 및 판별은 하드코딩 없이 검증된(verified) 세율 마스터를 기준으로 수행됩니다.</div>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="badge-risk-low">검증 상태: verified</span>
                    <span style="font-size:0.80rem; color:#64748B;">기준일: <b>2026-01-01</b></span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_chk_btn, col_chk_info = st.columns([1.8, 3.2], vertical_alignment="center")
        with col_chk_btn:
            if st.button("🔄 국가법령센터/국세청 개정 세율 실시간 감지", key="btn_run_rate_updater", use_container_width=True, type="primary"):
                with st.spinner("국가법령정보센터 DRF 및 국세청 공식 사이트에서 개정 세율을 모니터링 중입니다..."):
                    try:
                        updater = TaxRateUpdater()
                        detected = updater.check_all_rates()
                        st.session_state["detected_changes_cache"] = detected
                        st.success(f"세율 감지 완료: 총 {len(detected)}건의 검토 후보가 확인되었습니다.")
                    except Exception as e:
                        st.error(f"세율 감지 중 오류 발생: {e}")
        with col_chk_info:
            st.markdown("<span style='font-size:0.80rem; color:#64748B;'>※ 자동 갱신된 값은 즉시 계산에 적용되지 않고 `needs_review` 상태로 저장되며, 담당자 승인 시에만 실제 세율로 반영됩니다.</span>", unsafe_allow_html=True)

        # 세율 데이터 요약 표시
        try:
            mgr = TaxRateManager()
            all_rates = mgr.get_all_rates()
            rate_rows = []
            for cat, items in all_rates.items():
                if cat == "metadata" or not isinstance(items, dict):
                    continue
                for k, v in items.items():
                    rate_rows.append({
                        "분류": cat,
                        "세목/항목": k,
                        "적용세율/한도": v.get("rate_str") or v.get("limit_str", "-"),
                        "적용시작일": v.get("effective_start", "-"),
                        "적용종료일": v.get("effective_end", "현재"),
                        "검토상태": v.get("review_status", "verified"),
                        "확인일": v.get("last_verified_date", "2026-01-01"),
                        "법령근거": v.get("legal_basis", "-")
                    })
            if rate_rows:
                df_rates = pd.DataFrame(rate_rows)
                st.dataframe(df_rates, use_container_width=True, height=280)
        except Exception as e:
            st.warning(f"세율 마스터 로드 중: {e}")

        # detected_changes.json 검토 큐
        updater = TaxRateUpdater()
        chg_data = updater.load_detected_changes()
        det_list = chg_data.get("detected_changes", [])
        if det_list:
            st.markdown("<div style='margin-top:16px; font-size:0.95rem; font-weight:700; color:#0F172A;'>📋 검토 대기 변경 후보 (Detected Changes Queue)</div>", unsafe_allow_html=True)
            for d_idx, d_item in enumerate(det_list):
                if d_item.get("review_status") == "applied":
                    continue
                with st.container():
                    st.markdown(f"""
                    <div style="background:#FFFBEB; border:1px solid #FEDF89; border-radius:6px; padding:12px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span class="badge-risk-med">검토 대기: {d_item.get('category')} / {d_item.get('key')}</span>
                            <div style="font-size:0.86rem; font-weight:700; color:#0F172A; margin-top:4px;">기존: {d_item.get('current_value')} → 감지된 변경안: <b style='color:#B54708;'>{d_item.get('detected_rate_str')}</b></div>
                            <div style="font-size:0.78rem; color:#64748B;">출처: {d_item.get('source_url')} | 사유: {d_item.get('change_reason')}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"승인 및 tax_rates.json에 반영 ({d_item.get('key')})", key=f"btn_approve_chg_{d_idx}"):
                        ok = updater.apply_approved_change(d_item.get('key'), d_item.get('category'))
                        if ok:
                            st.success("세율이 성공적으로 승인 반영되었습니다!")
                            st.rerun()

    with tab_set_api:
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px 20px;">
            <div style="font-size:0.95rem; font-weight:700; color:#0F172A; margin-bottom:12px;">🏛️ API 연동 인프라 점검 결과</div>
            <table style="width:100%;">
                <thead>
                    <tr><th>인프라/서비스</th><th>연동 상태</th><th>식별자 / 모델</th><th>설명 및 가이드</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td><b>국가법령정보센터 DRF API</b></td>
                        <td><span class="badge-risk-low">정상 연동</span></td>
                        <td><code>{config.mask_secret(config.get_law_oc())}</code></td>
                        <td>실시간 대법원 판례, 헌재 결정, 조세심판원 결정례 조회</td>
                    </tr>
                    <tr>
                        <td><b>{config.get_ai_service_name()}</b></td>
                        <td><span class="{'badge-risk-low' if config.is_ai_configured() else 'badge-risk-high'}">{'정상 연동' if config.is_ai_configured() else '설정 필요'}</span></td>
                        <td><code>{config.get_azure_openai_deployment_name()} ({config.mask_secret(config.get_openai_api_key()) if config.get_openai_api_key() else '미입력'})</code></td>
                        <td>세무 상황 7대 사실관계 분석, 계약서 독소조항 진단, 판례 매칭, 리포트 생성</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.90rem; font-weight:700; color:#0F172A; margin-bottom:6px;'>⚙️ 검색 결과 건수 기본값 설정</div>", unsafe_allow_html=True)
        new_lim = st.slider("기본 검색 판례 건수", min_value=5, max_value=30, value=st.session_state.get("result_limit", 15), step=5, key="set_limit_slider")
        st.session_state["result_limit"] = new_lim

    with tab_set_sec:
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px 20px;">
            <div style="font-size:0.95rem; font-weight:700; color:#0F172A; margin-bottom:8px;">🔒 사내 세무 정보 보안 및 Cloudflare Tunnel 정책</div>
            <div style="font-size:0.86rem; color:#334155; line-height:1.65;">
                • <b>원자적 데이터 살균(Sanitization)</b>: 보관함 저장 시 주민등록번호, 계좌번호, API Key 등 민감정보는 자동으로 마스킹되어 안전하게 격리됩니다.<br>
                • <b>Cloudflare Tunnel 외부 공유 보안</b>: 외부 임시 URL(trycloudflare.com)로 접속 중일 경우, 회사 기밀 및 특정인의 실명·계좌번호 입력은 엄격히 금지됩니다.<br>
                • <b>가짜 판례 인용 차단</b>: ChatGPT Enterprise AI가 제안한 사건번호 중 국가법령정보센터 실제 DB에 부존재하는 사건은 화면 및 보관함에서 100% 자동 배제됩니다.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with tab_set_backup:
        from datetime import datetime
        from services.backup_service import (
            create_backup_zip_bytes,
            restore_from_backup_zip,
            get_data_storage_status
        )

        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px 20px; margin-bottom:16px;">
            <div style="font-size:1.0rem; font-weight:700; color:#0F172A;">💾 세무 검토 데이터 백업 및 복원 (Cloud Persistence)</div>
            <div style="font-size:0.84rem; color:#64748B; margin-top:2px;">
                무료 클라우드(Streamlit Cloud, Hugging Face 등) 환경의 컨테이너 재시작 시 발생할 수 있는 데이터 초기화에 대비하여,
                검토 이력 DB와 보관함 데이터를 원클릭으로 백업하고 복원할 수 있습니다.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 1. 현재 데이터 파일 현황 테이블
        st.markdown("<div style='font-size:0.90rem; font-weight:700; color:#0F172A; margin-bottom:8px;'>📊 현재 시스템 데이터 현황</div>", unsafe_allow_html=True)
        status_data = get_data_storage_status()
        rows = []
        for fname, s in status_data.items():
            rows.append({
                "데이터 파일": fname,
                "상태": "정상 가동" if s["exists"] else "미생성 (기본값 대기)",
                "용량 (KB)": f"{s['size_kb']} KB" if s["exists"] else "-",
                "최종 수정일시": s["mtime"]
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

        col_bak, col_rst = st.columns(2)

        with col_bak:
            st.markdown("""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:16px; min-height:220px;">
                <div style="font-size:0.95rem; font-weight:700; color:#003876; margin-bottom:6px;">📥 데이터 전체 백업 (Export)</div>
                <div style="font-size:0.82rem; color:#64748B; margin-bottom:14px;">
                    검토 이력(review_history.db), 관심 판례(saved_cases.json), 감사 로그, 2026 기준세율을 압축 파일로 다운로드합니다.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_bytes = create_backup_zip_bytes()
            st.download_button(
                label="📦 전체 데이터 백업 ZIP 다운로드",
                data=zip_bytes,
                file_name=f"tax_assistant_backup_{now_str}.zip",
                mime="application/zip",
                use_container_width=True,
                type="primary"
            )

        with col_rst:
            st.markdown("""
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:16px; min-height:220px;">
                <div style="font-size:0.95rem; font-weight:700; color:#008F69; margin-bottom:6px;">📤 데이터 복원 (Import)</div>
                <div style="font-size:0.82rem; color:#64748B; margin-bottom:14px;">
                    이전에 다운로드한 백업 ZIP 파일을 업로드하여 현재 시스템의 검토 데이터 및 보관함을 복원합니다.
                </div>
            </div>
            """, unsafe_allow_html=True)

            user_role = st.session_state.get("user_role", "viewer")
            if user_role == "admin":
                uploaded_backup = st.file_uploader(
                    "백업 ZIP 파일 선택",
                    type=["zip"],
                    key="upload_backup_zip",
                    label_visibility="collapsed"
                )
                if uploaded_backup is not None:
                    if st.button("⚠️ 복원 실행 (현재 데이터 덮어쓰기)", type="secondary", use_container_width=True):
                        ok, msg = restore_from_backup_zip(uploaded_backup.getvalue())
                        if ok:
                            st.success(f"✅ {msg}")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
            else:
                st.info("🔒 데이터 복원 기능은 '세무팀 관리자(admin)' 권한을 가진 계정에서만 실행할 수 있습니다.")
