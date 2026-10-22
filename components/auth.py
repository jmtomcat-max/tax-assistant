# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무 판례 AI 비서 - 보안 로그인 및 접근 제어 게이트키퍼 모듈 (auth.py)
- 클라우드 배포 시 비인가자 접근을 원천 차단
- 미인증 시 메인 화면 및 사이드바 렌더링 전 st.stop() 차단
- 브루트포스(무차별 대입) 지연 방어
- 세션 상태 격리 및 안전한 로그아웃
"""
import time
import streamlit as st
import config


def is_authenticated() -> bool:
    """현재 세션의 인증 상태 확인"""
    if not config.is_auth_enabled():
        return True
    return bool(st.session_state.get("is_authenticated", False))


def get_current_user() -> dict:
    """현재 로그인된 사용자 정보 반환"""
    return {
        "id": st.session_state.get("user_id", "guest"),
        "name": st.session_state.get("user_name", "손님"),
        "role": st.session_state.get("user_role", "viewer")
    }


def logout_user():
    """세션 인증 초기화 및 로그아웃"""
    st.session_state["is_authenticated"] = False
    st.session_state.pop("user_id", None)
    st.session_state.pop("user_name", None)
    st.session_state.pop("user_role", None)
    st.session_state["login_failed_count"] = 0
    st.rerun()


def render_login_view():
    """CJ CI/BI 스타일의 카드형 보안 로그인 화면 렌더링"""
    # 기본 레이아웃 구성 (가운데 정렬)
    _, col_center, _ = st.columns([1, 1.8, 1])

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; margin-top: 40px; margin-bottom: 25px;">
                <div style="font-size: 42px; margin-bottom: 8px;">⚖️</div>
                <h2 style="color: #003876; font-weight: 800; margin: 0; font-size: 24px; letter-spacing: -0.5px;">
                    CJ프레시웨이 세무 리서치 & AI 검토
                </h2>
                <p style="color: #666666; font-size: 13.5px; margin-top: 6px;">
                    사내 보안 로그인 · Enterprise Authentication Gate
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.container(border=True):
            st.markdown(
                """
                <div style="background-color: #F8FAFC; border-left: 4px solid #008F69; padding: 10px 14px; border-radius: 4px; margin-bottom: 18px;">
                    <div style="font-size: 12px; color: #334155; line-height: 1.45;">
                        🔒 <b>사내 정보보호 안내</b><br>
                        본 시스템은 국세법령·판례 및 사내 회계 검토 지식을 다룹니다.<br>
                        인가된 임직원 및 세무 실무자만 로그인할 수 있습니다.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 로그인 실패 횟수 관리
            if "login_failed_count" not in st.session_state:
                st.session_state["login_failed_count"] = 0

            with st.form("enterprise_login_form", clear_on_submit=False):
                username_input = st.text_input(
                    "아이디 (사번 또는 계정 ID)",
                    placeholder="예: admin 또는 user",
                    help="사내 부여된 계정 아이디를 입력하세요."
                ).strip()

                password_input = st.text_input(
                    "비밀번호",
                    type="password",
                    placeholder="비밀번호를 입력하세요",
                    help="계정 비밀번호를 입력하세요."
                ).strip()

                submit_btn = st.form_submit_button(
                    "보안 로그인",
                    use_container_width=True,
                    type="primary"
                )

                if submit_btn:
                    # 무차별 대입 공격 지연 (3회 이상 실패 시)
                    if st.session_state["login_failed_count"] >= 3:
                        delay = min(3.0, st.session_state["login_failed_count"] * 0.5)
                        time.sleep(delay)

                    success, user_info = config.verify_user_credentials(username_input, password_input)

                    if success and user_info:
                        st.session_state["is_authenticated"] = True
                        st.session_state["user_id"] = user_info["id"]
                        st.session_state["user_name"] = user_info["name"]
                        st.session_state["user_role"] = user_info["role"]
                        st.session_state["login_failed_count"] = 0
                        st.success(f"인증 성공! {user_info['name']}님 환영합니다.")
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.session_state["login_failed_count"] += 1
                        st.error("아이디 또는 비밀번호가 올바르지 않습니다. 다시 확인해 주세요.")

        st.markdown(
            """
            <div style="text-align: center; margin-top: 18px; font-size: 11.5px; color: #94A3B8;">
                CJ Freshway Accounting & Tax AI Assistant · v2.5 Enterprise Edition<br>
                계정 발급 및 문의: 경영지원담당 회계팀
            </div>
            """,
            unsafe_allow_html=True
        )


def check_authentication() -> bool:
    """
    애플리케이션 진입점 게이트키퍼
    인증되지 않은 경우 로그인 화면을 띄우고 st.stop()을 호출하여 후속 사이드바/본문 차단
    """
    if is_authenticated():
        return True

    render_login_view()
    st.stop()
    return False
