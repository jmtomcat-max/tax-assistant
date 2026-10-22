# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무·조세 판례 실시간 검색 및 AI 분석 비서 - 디자인 시스템 (CSS)
- components/ui_elements.py 에서 분리됨 (2026-09-14 리팩토링)
- 순수 스타일 정의만 담당. 비즈니스 로직/렌더링 로직은 포함하지 않음
"""
import streamlit as st


def apply_custom_css():
    st.markdown("""
    <style>
        /* =========================================================================
           CJ프레시웨이 세무 리서치 & AI 검토 - 전문가용(Big 4 / 로펌) 디자인 시스템
           - Primary: #005B45 (포레스트 다크그린)
           - Navy: #003876 (CJ 딥 네이비)
           - Background: #F8FAFC (Slate 50)
           - Surface: #FFFFFF (Clean White)
           - Border: #E2E8F0 (Slate 200)
           - Main Text: #0F172A (Slate 900)
           - Sub Text: #64748B (Slate 500)
           - High Risk: #B42318 (Red) / Medium: #B54708 (Amber) / Low: #027A48 (Green)
           ========================================================================= */

        @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");

        :root {
            --primary: #005B45;
            --primary-hover: #004736;
            --navy: #003876;
            --bg: #F8FAFC;
            --surface: #FFFFFF;
            --border: #E2E8F0;
            --text-main: #0F172A;
            --text-sub: #64748B;
            --risk-high: #B42318;
            --risk-med: #B54708;
            --risk-low: #027A48;
        }

        /* 0. 스크롤 설정 (전역 smooth-scroll 제거: 스트림릿 리런 시 상단 스크롤 점프 방지) */
        html {
            scroll-behavior: auto !important;
        }

        .card-scroll-anchor {
            display: block;
            position: relative;
            top: -85px;
            visibility: hidden;
            height: 0;
        }

        /* 1. 타이포그래피 */
        html, body, .stApp, 
        p, h1, h2, h3, h4, h5, h6, 
        label, input, textarea, select, 
        div:not([data-testid*="Icon"]):not([class*="material-"]):not(.material-symbols-rounded):not(.material-symbols-outlined), 
        span:not([data-testid*="Icon"]):not([class*="material-"]):not(.material-symbols-rounded):not(.material-symbols-outlined) {
            font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, "Helvetica Neue", "Segoe UI", sans-serif;
            -webkit-font-smoothing: antialiased;
            color: #0F172A;
            letter-spacing: -0.015em;
        }

        /* 2. 전체 앱 배경 */
        /* 2. 전체 앱 배경 (본문은 순백색, 사이드바는 미니멀 연회색) */
        .stApp {
            background-color: #FFFFFF !important;
        }
        .block-container {
            padding-top: 1.25rem !important;
            padding-bottom: 5rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 1440px !important;
            background-color: #FFFFFF !important;
        }

        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.08); opacity: 0.85; }
            100% { transform: scale(1); opacity: 1; }
        }

        /* 머티리얼 심볼 복원 */
        [data-testid*="Icon"], [data-testid="stIconMaterial"], [class*="material-"] {
            font-family: "Material Symbols Rounded", "Material Icons" !important;
            display: inline-block !important;
        }

        /* =========================================================================
           3. 미니멀 고정형 사이드바 (레퍼런스 이미지 Arc 스타일 100% 구현)
           - 배경색: #ECECEC (차분하고 깨끗한 연회색)
           - 우측 경계선: 1px solid #E0E0E0
           - 너비: 210px
           - 비선택 메뉴: 테두리/배경 전혀 없는 순수 플랫 텍스트 행 (#555555, 높이 30px)
           - 선택 메뉴: 순백색(#FFFFFF) 라운드 카드 (8px 모서리, 미세 테두리, 그림자, 진한 글자 #111111)
           ========================================================================= */
        section[data-testid="stSidebar"] {
            background-color: #ECECEC !important;
            background: #ECECEC !important;
            border-right: 1px solid #E0E0E0 !important;
            width: 210px !important;
            min-width: 180px !important;
            max-width: 240px !important;
            box-shadow: none !important;
        }
        section[data-testid="stSidebar"] > div:first-child {
            background-color: #ECECEC !important;
            background: #ECECEC !important;
            width: 210px !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            background-color: #ECECEC !important;
            background: #ECECEC !important;
            padding: 0.5rem 0.45rem 1rem 0.45rem !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
        }

        /* 스트림릿 기본 세로 블록 간격 최소화 (레퍼런스 같은 밀도감 확보) */
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 1px !important;
        }
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }

        /* 상단 컴팩트 헤더 */
        .sb-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 4px 6px 8px 6px;
            min-height: 38px;
        }
        .sb-brand {
            display: flex;
            align-items: center;
            gap: 7px;
        }
        .sb-brand-logo {
            width: 24px;
            height: 24px;
            background: #FFFFFF;
            border: 1px solid #DEDEDE;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        }
        .sb-brand-meta {
            display: flex;
            flex-direction: column;
            line-height: 1.1;
        }
        .sb-service-name {
            font-size: 0.82rem;
            font-weight: 800;
            color: #111111;
            letter-spacing: -0.01em;
        }
        .sb-org-name {
            font-size: 0.65rem;
            font-weight: 500;
            color: #888888;
        }
        .sb-header-actions {
            display: flex;
            align-items: center;
        }
        .sb-version-dot {
            width: 6px;
            height: 6px;
            background-color: #10B981;
            border-radius: 50%;
            display: inline-block;
        }
        .sb-divider-top {
            height: 1px;
            background-color: #E0E0E0;
            margin: 2px 4px 6px 4px;
        }
        .sb-divider-bottom {
            height: 1px;
            background-color: #E0E0E0;
            margin: 10px 4px 4px 4px;
        }
        .sb-group-title {
            font-size: 11px;
            font-weight: 600;
            color: #777777;
            letter-spacing: 0.01em;
            padding: 7px 8px 2px 8px;
            margin: 0;
            user-select: none;
        }
        .sb-badge {
            font-size: 10px;
            font-weight: 700;
            background-color: #DEDEDE;
            color: #555555;
            padding: 1px 5px;
            border-radius: 8px;
            margin-left: 4px;
        }
        .sb-spacer {
            height: 8px;
        }

        /* 하단 사용자 계정 및 인프라 카드 */
        .sb-user-card {
            display: flex;
            align-items: center;
            gap: 7px;
            padding: 5px 8px;
            margin: 2px 0 4px 0;
            border-radius: 6px;
            background: transparent;
        }
        .sb-user-avatar {
            width: 22px;
            height: 22px;
            background: #DEDEDE;
            color: #444444;
            font-size: 10px;
            font-weight: 700;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .sb-user-info {
            flex: 1;
            overflow: hidden;
            line-height: 1.15;
        }
        .sb-user-name {
            font-size: 11.5px;
            font-weight: 600;
            color: #222222;
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
        }
        .sb-user-role {
            font-size: 10px;
            color: #888888;
            white-space: nowrap;
            text-overflow: ellipsis;
            overflow: hidden;
        }
        .sb-status-dot {
            width: 5px;
            height: 5px;
            background-color: #10B981;
            border-radius: 50%;
        }
        .sb-infra-footer {
            font-size: 10px;
            color: #777777;
            padding: 2px 8px 6px 8px;
            line-height: 1.3;
        }

        /* =========================================================================
           사이드바 버튼: 비선택(Secondary) 상태 - 순수 플랫 텍스트 행
           - 테두리 없음, 배경 투명, 그림자 없음
           - 높이 31px, 좌우 패딩 8px, 은은한 hover
           ========================================================================= */
        section[data-testid="stSidebar"] div[data-testid="stButton"],
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
        }

        section[data-testid="stSidebar"] button,
        section[data-testid="stSidebar"] button[kind="secondary"],
        section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"],
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
            height: 31px !important;
            min-height: 31px !important;
            max-height: 31px !important;
            background-color: transparent !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
            color: #555555 !important;
            font-weight: 450 !important;
            font-size: 13px !important;
            border-radius: 7px !important;
            text-align: left !important;
            justify-content: flex-start !important;
            padding: 0 8px !important;
            margin: 1px 0 !important;
            transition: background-color 0.12s ease, color 0.12s ease !important;
            letter-spacing: -0.01em !important;
        }
        section[data-testid="stSidebar"] button p,
        section[data-testid="stSidebar"] button span,
        section[data-testid="stSidebar"] button div,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button p,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button span,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button div {
            color: #555555 !important;
            font-size: 13px !important;
            font-weight: 450 !important;
        }

        /* Hover 상태: 배경만 아주 연한 회색(#DFDFDF), 텍스트 약간 진하게 */
        section[data-testid="stSidebar"] button:hover,
        section[data-testid="stSidebar"] button[kind="secondary"]:hover,
        section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
            background-color: #DFDFDF !important;
            background: #DFDFDF !important;
            border: none !important;
            box-shadow: none !important;
            color: #111111 !important;
        }
        section[data-testid="stSidebar"] button:hover p,
        section[data-testid="stSidebar"] button:hover span,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover p,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover span {
            color: #111111 !important;
        }

        /* =========================================================================
           사이드바 버튼: 선택된(Active / Primary) 상태 - 레퍼런스의 "New Tab" 흰색 카드
           - 오직 이 항목만 순백색 카드(#FFFFFF)
           - 얇은 1px 테두리 + 부드러운 미세 그림자 + 진한 글자(#111111, 볼드)
           ========================================================================= */
        section[data-testid="stSidebar"] button[kind="primary"],
        section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"],
        section[data-testid="stSidebar"] button[data-testid="baseButton-primary"],
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"],
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
            background-color: #FFFFFF !important;
            background: #FFFFFF !important;
            border: 1px solid rgba(0, 0, 0, 0.08) !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04) !important;
            color: #111111 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            border-radius: 7px !important;
            height: 32px !important;
            min-height: 32px !important;
            max-height: 32px !important;
            padding: 0 8px !important;
            margin: 1px 0 !important;
        }
        section[data-testid="stSidebar"] button[kind="primary"]:hover,
        section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover {
            background-color: #FFFFFF !important;
            background: #FFFFFF !important;
            border: 1px solid rgba(0, 0, 0, 0.12) !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
            color: #000000 !important;
        }
        section[data-testid="stSidebar"] button[kind="primary"] p,
        section[data-testid="stSidebar"] button[kind="primary"] span,
        section[data-testid="stSidebar"] button[kind="primary"] div,
        section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] p,
        section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] span,
        section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] div,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] p,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] span,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] div,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"] p,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"] span,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"] div,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] p,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] span,
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] div {
            color: #111111 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }

        /* 4. 본문 전용 버튼 스타일링 (CJ프레시웨이 포레스트 다크그린 #005B45 주요 버튼 vs 흰색/회색 보조 버튼)
           - 사이드바에는 절대 적용되지 않도록 .stMain 으로 엄격히 스코핑 */
        .stMain button[kind="primary"], 
        .stMain button[kind="primaryFormSubmit"],
        .stMain button[data-testid="baseButton-primary"], 
        .stMain button[data-testid="stBaseButton-primary"],
        .stMain div[data-testid="stFormSubmitButton"] > button,
        .stMain div[data-testid="stFormSubmitButton"] button {
            background-color: #005B45 !important;
            background: #005B45 !important;
            border: 1px solid #004D3A !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border-radius: 6px !important;
            box-shadow: 0 1px 3px rgba(0, 91, 69, 0.15) !important;
            transition: all 0.15s ease !important;
        }
        .stMain button[kind="primary"]:hover, 
        .stMain button[kind="primaryFormSubmit"]:hover,
        .stMain button[data-testid="baseButton-primary"]:hover, 
        .stMain button[data-testid="stBaseButton-primary"]:hover,
        .stMain div[data-testid="stFormSubmitButton"] > button:hover,
        .stMain div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #004736 !important;
            background: #004736 !important;
            border-color: #003828 !important;
            color: #FFFFFF !important;
            box-shadow: 0 3px 8px rgba(0, 91, 69, 0.22) !important;
        }
        .stMain button[kind="primary"] *, 
        .stMain button[kind="primaryFormSubmit"] *,
        .stMain button[data-testid="baseButton-primary"] *, 
        .stMain button[data-testid="stBaseButton-primary"] *,
        .stMain div[data-testid="stFormSubmitButton"] button * {
            color: #FFFFFF !important;
        }

        /* 본문 보조 버튼 */
        .stMain div[data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):not([data-testid="stBaseButton-primary"]) {
            background-color: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            color: #334155 !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
        }

        .stMain div[data-testid="stButton"] > button:not([kind="primary"]):not([data-testid="baseButton-primary"]):not([data-testid="stBaseButton-primary"]):hover {
            background-color: #F8FAFC !important;
            border-color: #94A3B8 !important;
            color: #0F172A !important;
        }

        /* 판례 카드 AI 버튼은 화면 상태와 무관하게 항상 녹색 */
        div[class*="st-key-ai_review_button_"] button {
            background: #005B45 !important;
            border-color: #004D3A !important;
            color: #FFFFFF !important;
            opacity: 1 !important;
        }
        div[class*="st-key-ai_review_button_"] button * {
            color: #FFFFFF !important;
        }
        div[class*="st-key-ai_review_button_"] button:hover {
            background: #004736 !important;
        }

        /* 🚨 스트림릿 부모 컨테이너의 가로 넓이 제한(클리핑) 해제 🚨 */
        [data-testid="stMarkdownContainer"] {
            overflow-x: auto !important; 
            max-width: 100% !important;
        }
        
        /* 우리가 만든 테이블이 강제로 줄어들지 않도록 보호 */
        .stMarkdown table {
            min-width: 1100px !important;
            table-layout: fixed !important; 
            border-collapse: collapse !important;
            font-size: 0.88rem !important;
            word-break: keep-all !important;
        }

        div[data-testid="stMarkdownContainer"] table.custom-case-table,
        table.custom-case-table {
            min-width: 1240px !important;
            width: 100% !important;
        }
        
        .stMarkdown table th:nth-child(4), 
        .stMarkdown table td:nth-child(4) {
            width: 130px !important; /* '결론' 배지 컬럼 너비 강제 확보 */
            min-width: 125px !important;
        }

        .stMarkdown table th:nth-child(5), 
        .stMarkdown table td:nth-child(5) {
            width: 270px !important; /* '판단 기준' 컬럼 너비 */
            min-width: 250px !important;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
        }

        .custom-case-table th,
        .custom-case-table td {
            box-sizing: border-box !important;
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
        }

        .custom-case-table .col-chk {
            width: 50px !important;
            min-width: 50px !important;
            max-width: 50px !important;
            text-align: center !important;
        }
        .custom-case-table .col-no {
            width: 190px !important;
            min-width: 180px !important;
            word-break: break-all !important;
            white-space: normal !important;
        }
        .custom-case-table .col-issue {
            width: 180px !important;
            min-width: 160px !important;
            word-break: keep-all !important;
            white-space: normal !important;
        }
        .custom-case-table .col-quality {
            width: 170px !important;
            min-width: 155px !important;
            word-break: keep-all !important;
            white-space: normal !important;
            line-height: 1.45 !important;
        }
        .custom-case-table .col-outcome {
            width: 130px !important;
            min-width: 125px !important;
            max-width: 135px !important;
            text-align: center !important;
            white-space: nowrap !important;
        }
        .custom-case-table .col-criterion {
            width: 270px !important;
            min-width: 250px !important;
            word-break: keep-all !important;
            white-space: normal !important;
            line-height: 1.5 !important;
        }
        .custom-case-table .col-app {
            width: 220px !important;
            min-width: 190px !important;
            word-break: keep-all !important;
            white-space: normal !important;
            line-height: 1.45 !important;
        }
        .custom-case-table .col-link {
            width: 60px !important;
            min-width: 55px !important;
            max-width: 60px !important;
            text-align: center !important;
        }

        /* 표 행 hover: 아주 은은한 회색 배경 */
        .stMarkdown table tbody tr:hover td {
            background-color: #F8FAFC !important;
        }

        /* 6. 판례 피드 카드 & 보관함 카드 (세련된 초록 계열 hover 및 부드러운 -2px 부상) */
        .case-container {
            background-color: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-left: 4px solid transparent !important;
            border-radius: 8px !important;
            padding: 18px 22px !important;
            margin-bottom: 12px !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
            cursor: pointer;
        }
        .case-container:hover {
            background: linear-gradient(135deg, #F0FDF4 0%, #FAFDFB 60%, #FFFFFF 100%) !important;
            border-color: #A7D7C9 !important;
            border-left: 4px solid #005B45 !important;
            box-shadow: 0 6px 18px rgba(0, 91, 69, 0.10), 0 2px 6px rgba(15, 23, 42, 0.04) !important;
            transform: translateY(-2px) !important;
        }
        .case-container:hover .case-title {
            color: #004D3A !important;
            transition: color 0.15s ease !important;
        }
        .case-container.case-focused {
            background: #F0FDF4 !important;
            border-color: #005B45 !important;
            border-left: 4px solid #005B45 !important;
            box-shadow: 0 6px 20px rgba(0, 91, 69, 0.12) !important;
        }
        .case-title {
            font-size: 1.12rem !important;
            font-weight: 700 !important;
            color: #0F172A !important;
            line-height: 1.45 !important;
            margin: 8px 0 6px 0 !important;
            transition: color 0.15s ease !important;
        }

        /* 최근 보관 사례 및 추천 시나리오 카드 호버 */
        .recent-case-card {
            background-color: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-left: 3px solid transparent !important;
            border-radius: 8px !important;
            padding: 12px 14px !important;
            margin-bottom: 8px !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }
        .recent-case-card:hover {
            background: #F0FDF4 !important;
            border-color: #A7D7C9 !important;
            border-left: 3px solid #005B45 !important;
            box-shadow: 0 4px 14px rgba(0, 91, 69, 0.08) !important;
            transform: translateY(-2px) !important;
        }

        div.scenario-card-container div[data-testid="stButton"] > button {
            height: auto !important;
            min-height: 68px !important;
            background: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 8px !important;
            padding: 12px 16px !important;
            text-align: left !important;
            justify-content: flex-start !important;
            font-size: 0.88rem !important;
            line-height: 1.45 !important;
            color: #1E293B !important;
            font-weight: 600 !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
            white-space: normal !important;
        }
        div.scenario-card-container div[data-testid="stButton"] > button:hover {
            border-color: #A7D7C9 !important;
            background: #F0FDF4 !important;
            color: #005B45 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 14px rgba(0, 91, 69, 0.08) !important;
        }

        /* 위험도 배지 공통 */
        .badge-risk-high,
        .badge-risk-med,
        .badge-risk-low {
            display: inline-flex;
            align-items: center;
            white-space: nowrap;
            line-height: 1.2;
            font-weight: 700;
            border-radius: 5px;
            padding: 3px 9px;
        }

        .badge-risk-high {
            background-color: #FEF3F2 !important;
            color: #B42318 !important;
            border: 1px solid #FECDCA !important;
        }
        .badge-risk-med {
            background-color: #FFFAEB !important;
            color: #B54708 !important;
            border: 1px solid #FEDF89 !important;
        }
        .badge-risk-low {
            background-color: #ECFDF3 !important;
            color: #027A48 !important;
            border: 1px solid #A6F4C5 !important;
        }
        .badge-risk-info {
            background-color: #EFF8FF !important;
            color: #003876 !important;
            border: 1px solid #B2DDFF !important;
            font-weight: 700 !important;
            font-size: 0.78rem !important;
            padding: 3px 9px !important;
            border-radius: 5px !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 4px !important;
        }

        .tax-badge {
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            padding: 3px 9px !important;
            border-radius: 5px !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 3px !important;
        }
        .tax-corp { color: #005B45 !important; background-color: #ECFDF5 !important; border: 1px solid #A7F3D0 !important; }
        .tax-vat { color: #003876 !important; background-color: #EFF8FF !important; border: 1px solid #B2DDFF !important; }
        .tax-income { color: #B54708 !important; background-color: #FFFAEB !important; border: 1px solid #FEDF89 !important; }
        .tax-etc { color: #475569 !important; background-color: #F1F5F9 !important; border: 1px solid #CBD5E1 !important; }

        .case-badge-court {
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            color: #003876 !important;
            background-color: #F0F5FA !important;
            border: 1px solid #D0E0F2 !important;
            padding: 3px 9px !important;
            border-radius: 5px !important;
        }
        .case-badge-nts {
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            color: #78350F !important;
            background-color: #FEF3C7 !important;
            border: 1px solid #FDE68A !important;
            padding: 3px 9px !important;
            border-radius: 5px !important;
        }

        /* 판례 비교표 결론 배지 (4종) */
        .badge-outcome-taxpayer {
            background-color: #ECFDF5 !important;
            color: #027A48 !important;
            border: 1px solid #A6F4C5 !important;
            font-weight: 700 !important;
            font-size: 0.76rem !important;
            padding: 3px 8px !important;
            border-radius: 5px !important;
            display: inline-flex !important;
            align-items: center !important;
            white-space: nowrap !important;
        }
        .badge-outcome-office {
            background-color: #FEF3F2 !important;
            color: #B42318 !important;
            border: 1px solid #FECDCA !important;
            font-weight: 700 !important;
            font-size: 0.76rem !important;
            padding: 3px 8px !important;
            border-radius: 5px !important;
            display: inline-flex !important;
            align-items: center !important;
            white-space: nowrap !important;
        }
        .badge-outcome-partial {
            background-color: #FFFAEB !important;
            color: #B54708 !important;
            border: 1px solid #FEDF89 !important;
            font-weight: 700 !important;
            font-size: 0.76rem !important;
            padding: 3px 8px !important;
            border-radius: 5px !important;
            display: inline-flex !important;
            align-items: center !important;
            white-space: nowrap !important;
        }
        .badge-outcome-unclear {
            background-color: #FFFBEB !important;
            color: #B45309 !important;
            border: 1px solid #FDE68A !important;
            font-weight: 700 !important;
            font-size: 0.76rem !important;
            padding: 3px 8px !important;
            border-radius: 5px !important;
            display: inline-flex !important;
            align-items: center !important;
            white-space: nowrap !important;
        }

        /* 8. 탭 (st.tabs) 스타일링 */
        div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
            gap: 6px !important;
            border-bottom: 2px solid #E2E8F0 !important;
            margin-bottom: 16px !important;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            font-size: 0.90rem !important;
            font-weight: 600 !important;
            color: #64748B !important;
            padding: 8px 16px !important;
            border-radius: 6px 6px 0 0 !important;
            transition: all 0.15s ease !important;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
            color: #005B45 !important;
            background-color: #F8FAFC !important;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: #005B45 !important;
            font-weight: 700 !important;
            border-bottom: 2px solid #005B45 !important;
        }

        /* 9. 액션 버튼 영역 높이 통일 */
        div.card-actions div[data-testid="stButton"] > button {
            height: 36px !important;
            min-height: 36px !important;
            border-radius: 6px !important;
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            padding: 0 10px !important;
        }

        /* 10. 아코디언 & 인풋 */
        div[data-testid="stExpander"] {
            border: 1px solid #E2E8F0 !important;
            border-radius: 8px !important;
            background-color: #FFFFFF !important;
            margin-bottom: 12px !important;
        }
        div[data-testid="stExpander"] summary {
            padding: 10px 16px !important;
            font-size: 0.90rem !important;
            font-weight: 600 !important;
        }

        /* 11. 노션 스타일 심층 검토 콜아웃 블록 (AI 심층 검토 5대 섹션) */
        .notion-block {
            display: flex !important;
            align-items: flex-start !important;
            padding: 16px 20px !important;
            border-radius: 8px !important;
            margin: 10px 0 !important;
            font-size: 0.90rem !important;
            line-height: 1.68 !important;
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03) !important;
            transition: all 0.15s ease !important;
        }
        .notion-block:hover {
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06) !important;
        }
        .notion-icon {
            font-size: 1.25rem !important;
            margin-right: 12px !important;
            line-height: 1.3 !important;
            flex-shrink: 0 !important;
        }
        .notion-body {
            flex: 1 !important;
            color: #1E293B !important;
            min-width: 0 !important;
        }
        .notion-title {
            font-weight: 700 !important;
            font-size: 0.92rem !important;
            color: #0F172A !important;
            margin-bottom: 6px !important;
            letter-spacing: -0.01em !important;
        }
        .nb-cjblue { background-color: #F0F7FF !important; border: 1px solid #BAE6FD !important; border-left: 4px solid #003876 !important; }
        .nb-orange { background-color: #FFF7ED !important; border: 1px solid #FED7AA !important; border-left: 4px solid #EA580C !important; }
        .nb-gray { background-color: #F8FAFC !important; border: 1px solid #E2E8F0 !important; border-left: 4px solid #64748B !important; }
        .nb-green { background-color: #F0FDF4 !important; border: 1px solid #BBF7D0 !important; border-left: 4px solid #005B45 !important; }
        .nb-red { background-color: #FEF2F2 !important; border: 1px solid #FECDD3 !important; border-left: 4px solid #DC2626 !important; }
        .nb-yellow { background-color: #FEFCE8 !important; border: 1px solid #FEF08A !important; border-left: 4px solid #CA8A04 !important; }
        .nb-purple { background-color: #FAF5FF !important; border: 1px solid #E9D5FF !important; border-left: 4px solid #7E22CE !important; }

        /* 12. 판결 요지 박스 (📄 판결 요지 ▾) */
        .ruling-summary-box {
            background-color: #F8FAFC !important;
            border: 1.5px solid #CBD5E1 !important;
            border-left: 4px solid #003876 !important;
            border-radius: 8px !important;
            padding: 16px 20px !important;
            margin: 12px 0 !important;
        }
        .ruling-header {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            flex-wrap: wrap !important;
            gap: 6px !important;
            margin-bottom: 10px !important;
            padding-bottom: 8px !important;
            border-bottom: 1px solid #E2E8F0 !important;
        }
        .ruling-badge {
            display: inline-flex !important;
            align-items: center !important;
            gap: 6px !important;
            font-size: 0.88rem !important;
            font-weight: 700 !important;
            color: #003876 !important;
        }
        .ruling-section-title {
            font-size: 0.88rem !important;
            font-weight: 700 !important;
            color: #0F172A !important;
            margin-top: 10px !important;
            margin-bottom: 4px !important;
        }
        .ruling-text {
            font-size: 0.86rem !important;
            line-height: 1.65 !important;
            color: #334155 !important;
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 6px !important;
            padding: 10px 14px !important;
            margin-bottom: 8px !important;
        }
        .ruling-article-tag {
            display: inline-block !important;
            background-color: #EFF8FF !important;
            color: #003876 !important;
            border: 1px solid #B2DDFF !important;
            font-size: 0.76rem !important;
            font-weight: 600 !important;
            padding: 2px 8px !important;
            border-radius: 4px !important;
            margin-right: 4px !important;
            margin-bottom: 4px !important;
        }

        /* 상단 메뉴 숨김 */
        [data-testid="stDecoration"], [data-testid="stToolbarActions"], #MainMenu {
            display: none !important;
        }
        header[data-testid="stHeader"] {
            background: transparent !important;
            pointer-events: none !important;
        }

        /* -------------------------------------------------------------
           AI 심층 검토 & 공식 요지 - 미니멀 로딩 인디케이터 (st.spinner 커스텀)
           ------------------------------------------------------------- */
        div[data-testid="stSpinner"], .stSpinner {
            display: flex !important;
            align-items: center !important;
            gap: 12px !important;
            background: linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%) !important;
            border: 1.5px solid #86EFAC !important;
            border-left: 4px solid #005B45 !important;
            border-radius: 8px !important;
            padding: 12px 18px !important;
            margin: 10px 0 12px 0 !important;
            box-shadow: 0 2px 8px rgba(0, 91, 69, 0.06) !important;
            animation: aiSpinnerPulse 1.8s infinite ease-in-out !important;
        }

        @keyframes aiSpinnerPulse {
            0%, 100% { border-color: #86EFAC; }
            50% { border-color: #005B45; }
        }

        div[data-testid="stSpinner"] > div, .stSpinner > div {
            color: #005B45 !important;
            font-size: 0.88rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em !important;
        }

        div[data-testid="stSpinner"] svg, .stSpinner svg {
            color: #005B45 !important;
            stroke: #005B45 !important;
            width: 22px !important;
            height: 22px !important;
        }
    </style>
    """, unsafe_allow_html=True)

