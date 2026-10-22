# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무·조세 판례 실시간 검색 및 AI 분석 비서 - UI 컴포넌트 & 디자인 시스템
- 커스텀 CSS 테마 (CJ 딥 블루 & 시그니처 포레스트 다크그린)
- 공통 UI 엘리먼트 (노션 포맷터, 원클릭 복사 버튼, 판례 비교표, 판례 카드 등)
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import html
import re
import json
from storage import save_saved_cases, check_duplicate_case
from law_api import fetch_prec_detail
from summarizer import summarize_case, generate_ruling_summary


# ----------------- CJ프레시웨이 테마 커스텀 CSS 적용 -----------------
from components.styles import apply_custom_css
from components.case_logic import determine_case_outcome, derive_case_application, get_basis_quality_meta

# 참고: apply_custom_css / determine_case_outcome / derive_case_application / get_basis_quality_meta 는
# 각각 components/styles.py, components/case_logic.py 로 분리되었습니다 (2026-09-14 리팩토링).
# 기존 코드(app.py, views/*)가 "from components.ui_elements import X" 형태로 계속 불러올 수 있도록
# 여기서 재-import 하여 노출만 해줍니다. 새 코드를 작성할 때는 위 두 모듈에서 직접 import 하세요.




# ----------------- 노션 리포트용 포맷터 및 태그 정제 -----------------
def clean_index_tags(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\[\^?\d+\]', '', text)
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\[\s*\]', '', text)
    text = re.sub(r'【\s*】', '', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def format_notion_content(text: str) -> str:
    if not text:
        return ""
    text = clean_index_tags(str(text))
    # AI 응답의 HTML은 화면 구조를 깨뜨릴 수 있으므로 제거하고 나머지 문자는 안전하게 표시한다.
    text = re.sub(r'</?[A-Za-z][^>]*>', '', text).strip()
    if not text:
        return ""
    
    code_blocks = []
    def code_replacer(match):
        code_content = match.group(2).strip()
        code_blocks.append(code_content)
        return f"\n___CODE_BLOCK_{len(code_blocks)-1}___\n"

    processed = re.sub(r'```([a-zA-Z0-9_-]*)\n?(.*?)```', code_replacer, text, flags=re.DOTALL)
    processed = html.escape(processed)
    processed = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#0F172A; font-weight:700;">\1</strong>', processed)
    processed = re.sub(r'`([^`]+)`', r'<code style="background:#F1F5F9; color:#005B45; padding:2px 6px; border-radius:4px; font-size:0.88em; font-family:monospace;">\1</code>', processed)

    lines = processed.split("\n")
    output_lines = []
    
    for line in lines:
        s = line.strip()
        if not s:
            continue
        
        placeholder_match = re.match(r'^___CODE_BLOCK_(\d+)___$', s)
        if placeholder_match:
            idx = int(placeholder_match.group(1))
            code_text = code_blocks[idx]
            escaped_code = html.escape(code_text).replace('\n', '<br>')
            output_lines.append(
                f'<div style="background:#F8FAFC; border:1px solid #CBD5E1; border-left:4px solid #005B45; padding:10px 14px; border-radius:6px; font-family:\'Pretendard\', monospace; font-size:0.88rem; color:#1E293B; margin:8px 0; line-height:1.6;">{escaped_code}</div>'
            )
            continue
            
        if s.startswith("#### "):
            output_lines.append(f'<div style="font-size:0.96rem; font-weight:700; color:#004D3A; margin:14px 0 6px 0;">📌 {s[5:]}</div>')
        elif s.startswith("### "):
            output_lines.append(f'<div style="font-size:1.02rem; font-weight:700; color:#004D3A; margin:16px 0 8px 0;">📌 {s[4:]}</div>')
        elif s.startswith("## "):
            output_lines.append(f'<div style="font-size:1.1rem; font-weight:800; color:#004D3A; margin:18px 0 10px 0;">📌 {s[3:]}</div>')
        elif s.startswith("* ") or s.startswith("- ") or s.startswith("• "):
            content = s[2:].strip()
            output_lines.append(f'<div style="margin-left:6px; line-height:1.6;"><span style="color:#005B45; font-weight:bold;">•</span> {content}</div>')
        elif re.match(r'^\d+\.\s+', s):
            num_match = re.match(r'^(\d+\.)\s+(.*)', s)
            if num_match:
                output_lines.append(f'<div style="margin-left:6px; line-height:1.6;"><span style="color:#005B45; font-weight:700;">{num_match.group(1)}</span> {num_match.group(2)}</div>')
            else:
                output_lines.append(f'<div style="line-height:1.6;">{s}</div>')
        elif s == "---":
            output_lines.append('<hr style="border:none; border-top:1px solid #E2E8F0; margin:12px 0;">')
        else:
            output_lines.append(f'<div style="line-height:1.6;">{s}</div>')

    return "".join(output_lines)


def toggle_card_state(key_name: str):
    """Callback to instantly flip toggle state before page render (single-click response)."""
    st.session_state[key_name] = not st.session_state.get(key_name, False)


def _notion_block_html(css_class: str, icon: str, title: str, content: str) -> str:
    """Build a compact HTML block that Streamlit cannot misread as indented Markdown."""
    formatted = format_notion_content(content)
    if not formatted.strip():
        formatted = '<div style="color:#64748B; font-size:0.86rem; font-style:italic;">원문 판시사항 또는 AI 심층 분석 내용을 정리 중입니다.</div>'
    return (
        f'<div class="notion-block {css_class}">'
        f'<div class="notion-icon">{icon}</div>'
        f'<div class="notion-body">'
        f'<div class="notion-title">{title}</div>'
        f'{formatted}'
        f'</div></div>'
    )



# ----------------- 원클릭 복사 버튼 컴포넌트 -----------------
def render_copy_button(clip_text: str, key_id: str):
    json_text = json.dumps(clip_text, ensure_ascii=False)
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      body {{ margin: 0; padding: 0; background: transparent; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
      .copy-btn {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #334155;
        cursor: pointer;
        transition: all 0.2s ease;
      }}
      .copy-btn:hover {{
        background-color: #F8FAFC;
        border-color: #005B45;
        color: #005B45;
      }}
      .copy-btn.copied {{
        background-color: #ECFDF5;
        border-color: #059669;
        color: #059669;
      }}
      .btn-icon {{ font-size: 0.95rem; }}
    </style>
    </head>
    <body>
    <button class="copy-btn" id="btn_{key_id}" onclick="copyReport()">
      <span class="btn-icon" id="icon_{key_id}">📋</span>
      <span id="label_{key_id}">사내 보고용 텍스트 복사</span>
    </button>

    <script>
    const reportText = {json_text};

    function copyReport() {{
      const btn = document.getElementById('btn_{key_id}');
      const icon = document.getElementById('icon_{key_id}');
      const label = document.getElementById('label_{key_id}');

      function showCopied() {{
        btn.classList.add('copied');
        icon.textContent = '✓';
        label.textContent = '복사 완료!';
        
        setTimeout(() => {{
          btn.classList.remove('copied');
          icon.textContent = '📋';
          label.textContent = '사내 보고용 텍스트 복사';
        }}, 2200);
      }}

      try {{
        const ta = document.createElement('textarea');
        ta.value = reportText;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        ta.style.top = '-9999px';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        const success = document.execCommand('copy');
        document.body.removeChild(ta);
        if (success) {{
          showCopied();
          return;
        }}
      }} catch (e) {{}}

      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(reportText).then(showCopied).catch(e => {{
          window.parent.postMessage({{type: 'copy', text: reportText}}, '*');
          showCopied();
        }});
      }}
    }}
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=44)


# ----------------- 판례 결과 판단 배지 생성 -----------------


def render_case_comparison_table(
    pool_cases: list,
    user_query: str = "",
    facts_summary: dict = None,
    table_id_prefix: str = "search_comp"
):
    """
    유사 판례 비교표 컴포넌트
    """
    if not pool_cases or len(pool_cases) < 2:
        return

    unique_cases = []
    seen_nos = set()
    for c in pool_cases:
        c_no = c.get("case_number") or c.get("prec_id") or ""
        if c_no and c_no not in seen_nos:
            seen_nos.add(c_no)
            unique_cases.append(c)
        elif not c_no:
            unique_cases.append(c)

    if len(unique_cases) < 2:
        return

    selected_case_ids = st.session_state.get("selected_compare_case_ids", set())
    has_selected_filter = len(selected_case_ids) >= 2
    view_selected_only_key = f"{table_id_prefix}_view_selected_only"
    view_selected_only = st.session_state.get(view_selected_only_key, False)

    if view_selected_only and has_selected_filter:
        display_cases = [c for c in unique_cases if (c.get("case_number") in selected_case_ids or str(c.get("prec_id")) in selected_case_ids)]
        if len(display_cases) < 1:
            display_cases = unique_cases
    else:
        display_cases = unique_cases

    expand_key = f"{table_id_prefix}_expand_all"
    is_expanded = st.session_state.get(expand_key, False)
    
    limit = len(display_cases) if is_expanded else 5
    showing_cases = display_cases[:limit]

    st.markdown("""
    <div style="background:#FFFFFF; border:1.5px solid #005B45; border-radius:10px; padding:16px 20px; margin: 18px 0 16px 0; box-shadow:0 2px 12px rgba(0,91,69,0.06);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:1.15rem; font-weight:800; color:#005B45;">⚖️ 유사 판례 비교표 (Multi-Case Benchmarking)</span>
                <span style="font-size:0.78rem; font-weight:700; color:#003876; background:#EFF8FF; border:1px solid #B2DDFF; padding:2px 8px; border-radius:12px;">
                    공식 DB 검증 판례 대조
                </span>
            </div>
            <div style="font-size:0.80rem; color:#64748B;">
                사건번호·원문 <b>실제 국가법령정보센터 DB 100% 연동</b>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_t_info, col_t_filter, col_t_more = st.columns([3.5, 2.0, 1.5], vertical_alignment="center")
    with col_t_info:
        cur_cnt_str = f"전체 <b>{len(display_cases)}건</b> 중 <b>{len(showing_cases)}건</b> 비교 중"
        if selected_case_ids:
            cur_cnt_str += f" (체크된 판례: <b style='color:#005B45;'>{len(selected_case_ids)}건</b>)"
        st.markdown(f"<div style='font-size:0.84rem; color:#334155;'>{cur_cnt_str}</div>", unsafe_allow_html=True)

    with col_t_filter:
        if has_selected_filter:
            btn_filter_label = "📋 전체 판례 비교" if view_selected_only else f"✅ 선택 판례만 비교 ({len(selected_case_ids)}건)"
            if st.button(btn_filter_label, key=f"btn_flt_sel_{table_id_prefix}", use_container_width=True):
                st.session_state[view_selected_only_key] = not view_selected_only
                st.rerun()
        elif selected_case_ids:
            if st.button("선택 초기화", key=f"btn_reset_sel_{table_id_prefix}", use_container_width=True):
                st.session_state["selected_compare_case_ids"] = set()
                st.rerun()

    with col_t_more:
        if len(display_cases) > 5:
            more_label = "▲ 상위 5건 축소" if is_expanded else f"▾ 전체 {len(display_cases)}건 비교"
            if st.button(more_label, key=f"btn_more_{table_id_prefix}", use_container_width=True):
                st.session_state[expand_key] = not is_expanded
                st.rerun()

    table_rows_html = []
    for idx, c in enumerate(showing_cases, 1):
        c_no = c.get("case_number") or c.get("prec_id") or f"사건_{idx}"
        c_court = c.get("court", "법원")
        c_date = c.get("date", "-")
        c_title = c.get("title", "")
        c_link = c.get("link", "")
        c_source = c.get("source", "국가법령정보센터")
        c_summary = c.get("summary") or c.get("core_point") or c_title
        quality = get_basis_quality_meta(c)
        
        outcome = determine_case_outcome(c)
        outcome_badge = outcome["badge_html"]

        criterion_compact = c_summary[:95] + "..." if len(c_summary) > 95 else c_summary
        application_text = derive_case_application(c, user_query, facts_summary)
        reason_compact = quality["match_reason"] or "매칭 사유 미기재"
        if len(reason_compact) > 70:
            reason_compact = reason_compact[:70] + "..."
        quality_html = (
            f"<div>{quality['badge_html']}</div>"
            f"<div style='font-size:0.74rem; color:#64748B; margin-top:4px; line-height:1.35;'>{reason_compact}</div>"
        )

        if c_link:
            link_html = f'<a href="{c_link}" target="_blank" style="color:#003876; font-weight:700; text-decoration:underline; font-size:0.78rem;">원문 ↗</a>'
        else:
            link_html = '<span style="color:#94A3B8; font-size:0.78rem;">-</span>'

        is_chk = (c_no in selected_case_ids or str(c.get("prec_id")) in selected_case_ids)
        chk_icon = "☑️" if is_chk else f"[{idx}]"

        c_title_clean = c_title.replace('"', '&quot;').replace("'", "&#39;")
        issue_clamp_html = (
            f"<div style='display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis; line-height:1.45; font-size:0.82rem; font-weight:700; color:#1E293B;' title='{c_title_clean}'>"
            f"{c_title}"
            f"</div>"
        )

        # 🚨 핵심 CSS 수정: word-break: break-all 및 col-no 컬럼 클래스/너비 설정으로 글자 겹침 방지
        row_html = (
            f"<tr style='border-bottom:1px solid #F1F5F9;'>"
            f"<td class='col-chk' style='text-align:center; font-weight:700; color:#005B45; font-size:0.80rem; vertical-align:middle; padding:10px 6px;'>{chk_icon}</td>"
            f"<td class='col-no' style='font-size:0.82rem; vertical-align:middle; padding:10px 8px; white-space:normal; word-break:break-all;'><b style='color:#0F172A; font-family:Consolas, monospace;'>{c_no}</b><br><span style='font-size:0.75rem; color:#64748B; display:inline-block; margin-top:2px;'>{c_court} · {c_date}</span></td>"
            f"<td class='col-issue' style='vertical-align:middle; padding:10px 8px; white-space:normal; word-break:keep-all;'>{issue_clamp_html}</td>"
            f"<td class='col-quality' style='vertical-align:middle; padding:10px 8px; white-space:normal; word-break:keep-all;'>{quality_html}</td>"
            f"<td class='col-outcome' style='text-align:center; vertical-align:middle; padding:10px 6px;'>{outcome_badge}</td>"
            f"<td class='col-criterion' style='font-size:0.80rem; color:#334155; line-height:1.55; vertical-align:middle; padding:10px 8px; white-space:normal; word-break:keep-all;'>{criterion_compact}</td>"
            f"<td class='col-app' style='font-size:0.80rem; color:#005B45; line-height:1.55; vertical-align:middle; padding:10px 8px; white-space:normal; word-break:keep-all;'><div style='background:#F0FDF4; border:1px solid #DCFCE7; border-radius:6px; padding:6px 8px;'>💡 {application_text}</div></td>"
            f"<td class='col-link' style='text-align:center; vertical-align:middle; padding:10px 6px;'>{link_html}</td>"
            f"</tr>"
        )
        table_rows_html.append(row_html)

    # 비교표 컨테이너 및 HTML 테이블 구성 (최소 너비 1240px 보장 및 가로 스크롤 활성화)
    table_full_html = (
        f"<div style='width:100%; overflow-x:auto; margin:10px 0 14px 0; border:1px solid #E2E8F0; border-radius:8px; background:#FFFFFF;'>"
        f"<table class='custom-case-table' style='width:100%; min-width:1240px; border-collapse:collapse; font-size:0.82rem;'>"
        f"<thead>"
        f"<tr style='background:#F8FAFC; border-bottom:2px solid #CBD5E1; color:#475569;'>"
        f"<th class='col-chk' style='padding:10px 6px; text-align:center; vertical-align:middle; font-weight:700;'>구분</th>"
        f"<th class='col-no' style='padding:10px 8px; text-align:left; vertical-align:middle; font-weight:700;'>사건번호 / 선고일자</th>"
        f"<th class='col-issue' style='padding:10px 8px; text-align:left; vertical-align:middle; font-weight:700;'>핵심 쟁점</th>"
        f"<th class='col-quality' style='padding:10px 8px; text-align:left; vertical-align:middle; font-weight:700;'>근거 적합성</th>"
        f"<th class='col-outcome' style='padding:10px 8px; text-align:center; vertical-align:middle; font-weight:700;'>결론</th>"
        f"<th class='col-criterion' style='padding:10px 8px; text-align:left; vertical-align:middle; font-weight:700;'>판단 기준 (법리 요지)</th>"
        f"<th class='col-app' style='padding:10px 8px; text-align:left; vertical-align:middle; font-weight:700;'>우리 상황 적용</th>"
        f"<th class='col-link' style='padding:10px 6px; text-align:center; vertical-align:middle; font-weight:700;'>원문</th>"
        f"</tr>"
        f"</thead>"
        f"<tbody>{''.join(table_rows_html)}</tbody>"
        f"</table>"
        f"</div>"
    )
    st.markdown(table_full_html, unsafe_allow_html=True)

    with st.expander("📄 각 판례별 상세 판결 요지 및 심층 법리 펼치기", expanded=False):
        for idx, sc in enumerate(showing_cases, 1):
            sc_no = sc.get("case_number") or sc.get("prec_id") or f"사건_{idx}"
            sc_court = sc.get("court", "법원")
            sc_date = sc.get("date", "-")
            sc_title = sc.get("title", "")
            sc_summary = sc.get("summary") or sc.get("core_point") or "등록된 요지 정보 없음"
            sc_link = sc.get("link", "")
            sc_outcome = determine_case_outcome(sc)

            item_card_html = (
                f"<div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:12px 16px; margin-bottom:10px;'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:6px;'>"
                f"<div>"
                f"<span style='font-weight:700; color:#0F172A; font-size:0.88rem;'>[{idx}] {sc_court} {sc_no}</span>"
                f"<span style='font-size:0.78rem; color:#64748B; margin-left:6px;'>(선고일자: {sc_date})</span>"
                f"</div>"
                f"<div>{sc_outcome['badge_html']}</div>"
                f"</div>"
                f"<div style='font-size:0.84rem; font-weight:600; color:#003876; margin-bottom:6px;'>사건명: {sc_title}</div>"
                f"<div style='font-size:0.82rem; color:#334155; line-height:1.6; background:#FFFFFF; border:1px solid #E2E8F0; padding:8px 12px; border-radius:6px; margin-bottom:8px;'>"
                f"<b>판결/회신 요지:</b><br>{sc_summary}"
                f"</div>"
                f"<div style='font-size:0.80rem; color:#005B45;'>"
                f"<b>실무 적용 착안점:</b> {derive_case_application(sc, user_query, facts_summary)}"
                f"</div>"
                f"</div>"
            )
            st.markdown(item_card_html, unsafe_allow_html=True)
            if sc_link:
                st.link_button(f"🌐 {sc_no} 국가법령정보센터 원문 보기 ↗", sc_link, key=f"btn_link_dt_{table_id_prefix}_{idx}")


# ----------------- 클립보드 텍스트 빌더 -----------------
def build_clipboard_text(case_item: dict, summary_res: dict) -> str:
    title = case_item.get('title', '')
    case_no = case_item.get('case_number', '')
    court = case_item.get('court', '')
    date_str = case_item.get('date', '')
    link = case_item.get('link', '')

    legal_basis = summary_res.get('legal_basis', '').strip()
    tax_office_view = summary_res.get('tax_office_view', '').strip()
    taxpayer_view = summary_res.get('taxpayer_view', '').strip()
    court_decision = summary_res.get('court_decision', '').strip()
    actionable = summary_res.get('actionable_takeaway', '').strip()

    text = f"""[CJ프레시웨이 세무 검토 의견 요약]
■ 사건 기본 정보
- 사건명: {title}
- 사건번호: {case_no} ({court}, {date_str} 선고/결정)
- 원문 링크: {link}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 관련 세법 조항 및 핵심 쟁점
{legal_basis}

2. 과세관청(국세청) 과세 논거
{tax_office_view}

3. 납세자 방어 논리
{taxpayer_view}

4. 법원 / 심판원 최종 판단 기준
{court_decision}

5. 회계·세무팀 실무 액션 플랜 & 필수 증빙 체크리스트
{actionable}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
* 출처: CJ프레시웨이 TAX AI 비서 (국가법령정보센터 DB & ChatGPT Enterprise 분석)
"""
    return text.strip()


def build_ruling_clipboard_text(case_item: dict, ruling_data: dict) -> str:
    title = case_item.get('title', '')
    case_no = case_item.get('case_number', '')
    court = case_item.get('court', '')
    date_str = case_item.get('date', '')
    link = case_item.get('link', '')

    summary = ruling_data.get('summary', '').strip()
    points = ruling_data.get('points', '').strip()
    articles = ruling_data.get('ref_articles', '').strip()

    text = f"""[공식 세무 판결·예규 요지 요약]
■ 사건명: {title}
■ 사건번호: {case_no} ({court}, {date_str} 선고/결정)
■ 원문 링크: {link}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 판결·예규 요지 (판단 기준)
{summary}

2. 판시사항 및 주요 쟁점
{points}

3. 관련 세법 조항 / 참조조문
{articles}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
* 출처: 국가법령정보센터 DB & CJ프레시웨이 TAX AI 비서
"""
    return text.strip()


# ----------------- 개별 판례/예규 카드 컴포넌트 -----------------
@st.fragment
def render_case_card(item: dict, idx: int, prefix: str = "search"):
    """
    개별 판례/예규 카드
    """
    court = item.get("court", "법원")
    case_no = item.get("case_number", "")
    date_str = item.get("date", "")
    source = item.get("source", "")
    title = item.get("title", "")
    link = item.get("link", "")
    tax_cat = item.get("tax_category", "조세일반")
    cat = item.get("category", "")
    case_id = case_no or item.get("prec_id", f"{prefix}_{idx}")
    is_saved = case_id in st.session_state["saved_cases"]

    # 1. 자료 유형 배지 (법원 판례 / 조세심판례 / 국세청 심사·결정례 / 예규·법령해석)
    if cat == "조세심판례" or "조심" in case_no:
        data_badge_html = '<span style="background:#EEF2FF; color:#4338CA; border:1px solid #C7D2FE; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px;">🏛️ 조세심판례</span>'
    elif cat == "국세청 심사·결정례" or ("심사" in case_no and "국세청" in court):
        data_badge_html = '<span style="background:#ECFDF5; color:#047857; border:1px solid #A7F3D0; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px;">🏢 국세청 심사·결정례</span>'
    elif cat in ("예규/해석례", "예규·법령해석") or "해석" in cat:
        data_badge_html = '<span style="background:#FAF5FF; color:#7E22CE; border:1px solid #E9D5FF; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px;">📜 예규·법령해석</span>'
    else:
        data_badge_html = '<span style="background:#EFF8FF; color:#175CD3; border:1px solid #B2DDFF; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px;">⚖️ 법원 판례</span>'

    # 2. 세목 배지
    if tax_cat == "법인세":
        tax_badge_html = '<span class="tax-badge tax-corp">🏢 법인세</span>'
    elif tax_cat == "부가가치세":
        tax_badge_html = '<span class="tax-badge tax-vat">🧾 부가가치세</span>'
    elif tax_cat == "소득세·원천세":
        tax_badge_html = '<span class="tax-badge tax-income">👤 소득세·원천세</span>'
    elif tax_cat == "상속·증여세":
        tax_badge_html = '<span class="tax-badge tax-etc">🎁 상속·증여세</span>'
    else:
        tax_badge_html = f'<span class="tax-badge tax-etc">⚖️ {tax_cat}</span>'

    # 3. 기관 배지
    if "법원" in court or "대법원" in court:
        court_badge_html = f'<span class="case-badge-court">{court}</span>'
    elif "조세심판원" in court:
        court_badge_html = f'<span style="background:#EEF2FF; color:#3730A3; border:1px solid #C7D2FE; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px;">{court}</span>'
    elif "기획재정부" in court or "기재부" in court:
        court_badge_html = f'<span style="background:#FDF2F8; color:#9D174D; border:1px solid #FBCFE8; font-size:0.75rem; font-weight:700; padding:2px 7px; border-radius:4px;">{court}</span>'
    else:
        court_badge_html = f'<span class="case-badge-nts">{court}</span>'

    # 4. 문서번호 및 일자 라벨 구분
    doc_label = item.get("doc_no_label") or ("문서번호" if cat in ("예규/해석례", "예규·법령해석") else ("청구번호" if "심판" in cat or "조심" in case_no else ("결정번호" if "심사" in cat else "사건번호")))
    date_label = item.get("date_label") or ("회신" if cat in ("예규/해석례", "예규·법령해석") else ("의결" if "심판" in cat or "조심" in case_no else ("결정" if "심사" in cat else "선고")))

    # 5. 검색 경로 배지 (직접 검색 / 유사어 검색 / 리스크 검색 / 증빙 검색 / 자동 복원 검색)
    search_path = item.get("search_path", "직접 검색 결과")
    if search_path == "직접 검색 결과":
        path_badge_html = '<span style="background:#F0FDF4; color:#15803D; border:1px solid #BBF7D0; font-size:0.73rem; font-weight:700; padding:2px 7px; border-radius:4px;">🎯 직접 검색 결과</span>'
    elif search_path == "유사어 검색 결과":
        path_badge_html = '<span style="background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE; font-size:0.73rem; font-weight:700; padding:2px 7px; border-radius:4px;">🔄 유사어 검색 결과</span>'
    elif search_path == "리스크 검색 결과":
        path_badge_html = '<span style="background:#FEF2F2; color:#B91C1C; border:1px solid #FECACA; font-size:0.73rem; font-weight:700; padding:2px 7px; border-radius:4px;">🔴 리스크 검색 결과</span>'
    elif search_path == "증빙 검색 결과":
        path_badge_html = '<span style="background:#FFFBEB; color:#B45309; border:1px solid #FDE68A; font-size:0.73rem; font-weight:700; padding:2px 7px; border-radius:4px;">📑 증빙 검색 결과</span>'
    elif search_path == "자동 복원 검색 결과":
        path_badge_html = '<span style="background:#F1F5F9; color:#475569; border:1px solid #CBD5E1; font-size:0.73rem; font-weight:700; padding:2px 7px; border-radius:4px;">🛟 자동 복원 검색 결과</span>'
    else:
        path_badge_html = f'<span style="background:#F8FAFC; color:#475569; border:1px solid #E2E8F0; font-size:0.73rem; font-weight:600; padding:2px 7px; border-radius:4px;">🔍 {search_path}</span>'

    is_verified = item.get("is_verified", True)
    if is_verified:
        verified_badge_html = "<span class='badge-risk-low' style='font-size:0.75rem; padding:2px 7px;'>✔ 공식 DB 검증</span>"
    else:
        verified_badge_html = "<span class='badge-risk-high' style='font-size:0.75rem; padding:2px 7px;'>⚠️ 미확인 판례 배제</span>"

    raw_score = item.get("relevance_score")
    try:
        rel_score = int(float(raw_score)) if raw_score not in (None, "") and str(raw_score).strip() != "" else None
    except (ValueError, TypeError):
        rel_score = None

    if rel_score is not None and rel_score > 0:
        if rel_score >= 80:
            rel_badge_html = f"<span style='background:#DCFCE7; color:#166534; border:1px solid #86EFAC; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:12px;'>⭐ 관련도 {rel_score}점 (최고 일치)</span>"
        elif rel_score >= 50:
            rel_badge_html = f"<span style='background:#FEF3C7; color:#92400E; border:1px solid #FCD34D; font-size:0.75rem; font-weight:700; padding:2px 8px; border-radius:12px;'>⚡ 관련도 {rel_score}점 (유사 선례)</span>"
        else:
            rel_badge_html = f"<span style='background:#F1F5F9; color:#64748B; border:1px solid #CBD5E1; font-size:0.75rem; font-weight:600; padding:2px 8px; border-radius:12px;'>관련도 {rel_score}점 (참고용)</span>"
    else:
        rel_badge_html = ""

    # 근거 유형 배지 (6대 근거 버킷 지원)
    basis_bucket = item.get("basis_bucket", "")
    basis_type = item.get("basis_type", "")
    if basis_bucket == "direct_basis":
        basis_type_badge = "<span style='background:#DCFCE7; color:#15803D; border:1px solid #86EFAC; font-size:0.74rem; font-weight:700; padding:2px 7px; border-radius:12px;'>🎯 직접근거</span>"
    elif basis_bucket == "risk_basis":
        basis_type_badge = "<span style='background:#FEE2E2; color:#B91C1C; border:1px solid #FCA5A5; font-size:0.74rem; font-weight:700; padding:2px 7px; border-radius:12px;'>🔴 과세리스크</span>"
    elif basis_bucket == "evidence_basis":
        basis_type_badge = "<span style='background:#FEF3C7; color:#B45309; border:1px solid #FDE68A; font-size:0.74rem; font-weight:700; padding:2px 7px; border-radius:12px;'>📑 증빙·입증</span>"
    elif basis_bucket == "similar_basis":
        basis_type_badge = "<span style='background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE; font-size:0.74rem; font-weight:700; padding:2px 7px; border-radius:12px;'>🔄 유사근거</span>"
    elif basis_bucket == "statute_or_admin_basis":
        basis_type_badge = "<span style='background:#F3E8FF; color:#7E22CE; border:1px solid #E9D5FF; font-size:0.74rem; font-weight:700; padding:2px 7px; border-radius:12px;'>📜 예규·해석례</span>"
    elif basis_type == "직접근거 후보":
        basis_type_badge = "<span style='background:#DCFCE7; color:#15803D; border:1px solid #86EFAC; font-size:0.74rem; font-weight:700; padding:2px 7px; border-radius:12px;'>🎯 직접근거</span>"
    elif basis_type == "보조근거 후보":
        basis_type_badge = "<span style='background:#EFF8FF; color:#175CD3; border:1px solid #B2DDFF; font-size:0.74rem; font-weight:600; padding:2px 7px; border-radius:12px;'>📎 보조근거</span>"
    elif basis_type == "참고자료":
        basis_type_badge = "<span style='background:#F4F3FF; color:#5925DC; border:1px solid #D9D6FE; font-size:0.74rem; font-weight:600; padding:2px 7px; border-radius:12px;'>📚 참고자료</span>"
    else:
        basis_type_badge = ""

    signal_badge = ""
    if item.get("has_losing_signal"):
        signal_badge = "<span style='background:#FFF1F2; color:#E11D48; border:1px solid #FECDD3; font-size:0.72rem; font-weight:600; padding:1px 6px; border-radius:10px;'>⚠️ 과세유지·기각</span>"
    elif item.get("has_winning_signal"):
        signal_badge = "<span style='background:#F0FDF4; color:#16A34A; border:1px solid #BBF7D0; font-size:0.72rem; font-weight:600; padding:1px 6px; border-radius:10px;'>🛡️ 인용·승소</span>"

    matched_kws = item.get("matched_keywords", [])
    if matched_kws:
        matched_kws_chips = "".join([f"<span style='background:#EFF6FF; color:#1D4ED8; font-size:0.74rem; font-weight:600; padding:1px 6px; border-radius:4px; margin-right:4px;'>#{kw}</span>" for kw in matched_kws[:4]])
        kws_html = f"<div style='margin-top:4px; display:flex; align-items:center; flex-wrap:wrap; gap:3px;'><span style='font-size:0.75rem; color:#64748B; font-weight:600;'>매칭 키워드:</span> {matched_kws_chips}</div>"
    else:
        kws_html = ""

    match_reason = item.get("match_reason", "")
    if match_reason:
        reason_html = f"<div style='margin-top:3px; font-size:0.76rem; color:#475569; background:#F8FAFC; border-left:2.5px solid #005B45; padding:3px 8px; border-radius:0 4px 4px 0;'>💡 <b>선정 근거:</b> {match_reason}</div>"
    else:
        reason_html = ""

    saved_badge_html = "<span class='badge-risk-med' style='font-size:0.75rem; padding:2px 7px;'>★ 보관됨</span>" if is_saved else ""

    clean_id = re.sub(r'[^0-9a-zA-Z가-힣_]', '_', str(case_id or f"{prefix}_{idx}")).strip('_')
    toggle_key = f"toggle_{clean_id}"
    gist_key = f"gist_{clean_id}"
    analysis_key = f"case_ai_{clean_id}"
    is_open = st.session_state.get(toggle_key, False)
    is_gist_open = st.session_state.get(gist_key, False)

    if is_open and analysis_key not in st.session_state:
        with st.spinner("⚡ AI 세무 쟁점 및 증빙 체크리스트를 정밀 분석 중입니다. 잠시만 기다려 주세요."):
            st.session_state[analysis_key] = summarize_case(item)
    
    is_focused = is_open or is_gist_open
    focused_cls = " case-focused" if is_focused else ""

    with st.container():
        card_html = (
            f'<div class="case-container{focused_cls}">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">'
            f'<div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">'
            f'{data_badge_html} {tax_badge_html} {court_badge_html} {path_badge_html} {basis_type_badge} {signal_badge} {rel_badge_html} {verified_badge_html} {saved_badge_html}'
            f'<span style="font-size:0.74rem; color:#64748B; font-weight:600; margin-left:4px;">[{doc_label}]</span> '
            f'<span style="font-size:0.86rem; color:#1E293B; font-family:Consolas, monospace; font-weight:700;">{case_no}</span>'
            f'</div>'
            f'<div style="color:#64748B; font-size:0.80rem;">{date_label} {date_str}</div>'
            f'</div>'
            f'<div class="case-title">{title}</div>'
            f'{kws_html}'
            f'{reason_html}'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-top:5px;">'
            f'<span style="font-size:0.80rem; color:#64748B;">출처: {source}</span>'
            f'</div>'
            f'</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        st.markdown('<div class="card-actions">', unsafe_allow_html=True)
        col_chk, col_link, col_save, col_gist, col_toggle = st.columns([1.1, 0.9, 1.2, 1.3, 1.5], vertical_alignment="center")

        with col_chk:
            selected_comp = st.session_state.get("selected_compare_case_ids", set())
            is_comp_selected = (case_no in selected_comp or str(item.get("prec_id")) in selected_comp)
            chk_compare = st.checkbox("비교 선택", value=is_comp_selected, key=f"chk_comp_{prefix}_{idx}_{clean_id}")
            if chk_compare != is_comp_selected:
                target_key = case_no if case_no else str(item.get("prec_id"))
                if chk_compare:
                    selected_comp.add(target_key)
                else:
                    selected_comp.discard(target_key)
                st.session_state["selected_compare_case_ids"] = selected_comp
                st.rerun()

        with col_link:
            if link:
                st.link_button("🌐 원문 ↗", link, use_container_width=True, key=f"btn_link_{prefix}_{idx}_{clean_id}")
            else:
                st.button("원문 미제공", disabled=True, use_container_width=True, key=f"btn_nolink_{prefix}_{idx}_{clean_id}")


        with col_save:
            btn_save_label = "승인 후 자동 저장"
            if st.button(btn_save_label, key=f"btn_save_{prefix}_{idx}_{clean_id}", use_container_width=True,
                         disabled=True, help="검토 결과가 승인되면 승인된 자료에 자동 반영됩니다."):
                if is_saved:
                    del st.session_state["saved_cases"][case_id]
                    save_saved_cases(st.session_state["saved_cases"])
                    st.toast(f"보관함에서 삭제되었습니다: {case_no}", icon="🗑️")
                    st.rerun()
                else:
                    current_user_query = st.session_state.get("search_input", "").strip() or item.get("title", "")
                    is_dup, dup_msg, dup_id = check_duplicate_case(st.session_state["saved_cases"], case_no, current_user_query, case_id)
                    if is_dup:
                        st.warning(f"⚠️ {dup_msg}")
                        
                    if analysis_key in st.session_state:
                        summary_res = st.session_state[analysis_key]
                    else:
                        with st.spinner("AI 심층 리포트를 생성하여 보관함에 등록합니다..."):
                            summary_res = summarize_case(item)
                            st.session_state[analysis_key] = summary_res
                    
                    saved_item = dict(item)
                    saved_item["case_id"] = case_id
                    saved_item["review_status"] = "검토중"
                    saved_item["risk_level"] = "중립/유의"
                    saved_item["issue_tags"] = [item.get("tax_category", "조세일반"), item.get("court", "법원")]
                    saved_item["user_query"] = current_user_query
                    saved_item["user_memo"] = ""
                    saved_item["created_at"] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                    saved_item["updated_at"] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                    saved_item["facts_summary"] = {
                        "tax_category": item.get("tax_category", "조세일반"),
                        "trans_type": item.get("title", ""),
                        "counterparty": item.get("court", ""),
                        "amount": "판결문 참조",
                        "tax_period": item.get("date", ""),
                        "evidence_held": "공식 판결/예규 원문",
                        "purpose": "판례 분석 및 실무 검토"
                    }
                    saved_item["legal_references"] = [{
                        "type": "판례/예규",
                        "title": item.get("title", ""),
                        "case_number": case_no,
                        "court": court,
                        "date": date_str,
                        "link": link,
                        "source": source,
                        "prec_id": item.get("prec_id", ""),
                        "basis_type": item.get("basis_type", ""),
                        "relevance_score": item.get("relevance_score", ""),
                        "match_reason": item.get("match_reason", ""),
                        "matched_keywords": item.get("matched_keywords", [])
                    }]
                    saved_item["ai_opinion"] = {
                        "basis_strength": "유의 필요",
                        "basis_rationale": "법원/심판원 공식 판단 기준",
                        "conclusion": summary_res.get("legal_basis", "") or summary_res.get("court_decision", ""),
                        "case_comparison": summary_res.get("court_decision", ""),
                        "checklist": summary_res.get("actionable_takeaway", "")
                    }
                    saved_item["basis_quality"] = {
                        "basis_type": item.get("basis_type", ""),
                        "relevance_score": item.get("relevance_score", ""),
                        "match_reason": item.get("match_reason", ""),
                        "matched_keywords": item.get("matched_keywords", [])
                    }
                    saved_item["ai_summary"] = summary_res
                    saved_item["saved_at"] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
                    
                    st.session_state["saved_cases"][case_id] = saved_item
                    save_saved_cases(st.session_state["saved_cases"])
                    st.toast(f"📁 세무검토 사례 카드로 저장되었습니다! ({case_no})", icon="⭐")
                    st.rerun()

        with col_gist:
            btn_gist_text = f"▲ 요지 닫기" if is_gist_open else f"📄 판결 요지 ▾"
            st.button(
                btn_gist_text,
                key=f"btn_gist_{prefix}_{idx}_{clean_id}",
                on_click=toggle_card_state,
                args=(gist_key,),
                use_container_width=True
            )

        with col_toggle:
            btn_text = "▲ AI 검토 닫기" if is_open else "✨ AI 심층 검토 ▾"
            with st.container(key=f"ai_review_button_{prefix}_{idx}_{clean_id}"):
                st.button(
                    btn_text,
                    key=f"btn_toggle_{prefix}_{idx}_{clean_id}",
                    on_click=toggle_card_state,
                    args=(toggle_key,),
                    use_container_width=True,
                    type="primary",
                )
        st.markdown('</div>', unsafe_allow_html=True)

        if is_gist_open:
            ruling_cache_key = f"ruling_detail_{clean_id}"
            if ruling_cache_key in st.session_state:
                ruling_data = st.session_state[ruling_cache_key]
            else:
                if item.get("summary") and len(item.get("summary", "")) > 15:
                    ruling_data = {
                        "summary": item.get("summary", ""),
                        "points": item.get("title", ""),
                        "ref_articles": item.get("tax_category", ""),
                        "order": "",
                        "source_type": f"{source} ({court})"
                    }
                else:
                    with st.spinner("공식 판결/예규 요지 및 판시사항을 조회 중입니다..."):
                        prec_id = item.get("prec_id", "")
                        raw_detail = fetch_prec_detail(prec_id) if prec_id else {}
                        if raw_detail.get("has_detail"):
                            ruling_data = {
                                "summary": raw_detail.get("summary") or item.get("title", ""),
                                "points": raw_detail.get("points") or item.get("title", ""),
                                "ref_articles": raw_detail.get("ref_articles") or "",
                                "order": raw_detail.get("order") or "",
                                "source_type": f"국가법령정보센터 ({raw_detail.get('court') or court})"
                            }
                        else:
                            ai_ruling = generate_ruling_summary(item)
                            ruling_data = {
                                "summary": ai_ruling.get("summary") or item.get("title", ""),
                                "points": ai_ruling.get("points") or item.get("title", ""),
                                "ref_articles": ai_ruling.get("ref_articles") or "",
                                "order": "",
                                "source_type": f"국세법령정보시스템 & AI 공인 요약 ({court})"
                            }
                st.session_state[ruling_cache_key] = ruling_data

            ruling_clip_text = build_ruling_clipboard_text(item, ruling_data)
            ruling_cp_id = f"cp_gist_{prefix}_{idx}_{abs(hash(case_no))}"

            st.markdown(f"""
            <div class="ruling-summary-box">
                <div class="ruling-header">
                    <div class="ruling-badge">
                        <span>📜</span>
                        <span>공식 판결·예규 요지 ({ruling_data.get('source_type', '공식 요지')})</span>
                    </div>
                    <div style="font-size:0.82rem; color:#64748B;">선고/결정: <b>{date_str}</b> | 사건번호: <b>{case_no}</b></div>
                </div>
            """, unsafe_allow_html=True)

            col_r_body, col_r_btn = st.columns([3.8, 1.2], vertical_alignment="center")
            with col_r_body:
                st.markdown(f"<div style='font-size:0.86rem; color:#475569; font-weight:600;'>사건명: {title}</div>", unsafe_allow_html=True)
            with col_r_btn:
                render_copy_button(ruling_clip_text, ruling_cp_id)

            summary_txt = ruling_data.get("summary", "")
            if summary_txt:
                st.markdown(f"""
                <div class="ruling-section-title">⚖️ 1. 판결·예규 요지 및 판단 기준</div>
                <div class="ruling-text">{summary_txt}</div>
                """, unsafe_allow_html=True)

            points_txt = ruling_data.get("points", "")
            if points_txt and points_txt != summary_txt:
                st.markdown(f"""
                <div class="ruling-section-title">📌 2. 판시사항 및 핵심 쟁점</div>
                <div class="ruling-text">{points_txt}</div>
                """, unsafe_allow_html=True)

            order_txt = ruling_data.get("order", "")
            if order_txt:
                st.markdown(f"""
                <div class="ruling-section-title">⚖️ 3. 주문 (Order)</div>
                <div class="ruling-text" style="font-weight:600; color:#003876;">{order_txt}</div>
                """, unsafe_allow_html=True)

            ref_txt = ruling_data.get("ref_articles", "")
            if ref_txt:
                article_pills = "".join([f'<span class="ruling-article-tag">{art.strip()}</span>' for art in ref_txt.replace('/', ',').split(',') if art.strip()])
                st.markdown(f"""
                <div class="ruling-section-title" style="margin-top:10px;">📖 4. 관련 세법 조항 및 참조 조문</div>
                <div style="margin-top:4px;">{article_pills}</div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        if is_open:
            summary_res = st.session_state[analysis_key]

            clip_text = build_clipboard_text(item, summary_res)
            btn_id = f"cp_{prefix}_{idx}_{abs(hash(case_no))}"
            
            col_rep_title, col_rep_btn = st.columns([3, 2], vertical_alignment="center")
            with col_rep_title:
                saved_flag_html = " <span class='vault-saved-badge'>★ 보관함 보관 중</span>" if is_saved else ""
                st.markdown(f"<div style='font-size:0.95rem; font-weight:700; color:#005B45; margin: 8px 0;'>📊 ChatGPT Enterprise 심층 세무 검토 의견{saved_flag_html}</div>", unsafe_allow_html=True)
            with col_rep_btn:
                render_copy_button(clip_text, btn_id)

            st.markdown(_notion_block_html(
                "nb-cjblue", "📋", "관련 세법 조항 및 핵심 쟁점",
                summary_res.get("legal_basis", ""),
            ), unsafe_allow_html=True)

            col_gov, col_taxpayer = st.columns(2)
            with col_gov:
                st.markdown(_notion_block_html(
                    "nb-orange", "🏢", "과세관청(국세청) 과세 논거",
                    summary_res.get("tax_office_view", ""),
                ), unsafe_allow_html=True)
            with col_taxpayer:
                st.markdown(_notion_block_html(
                    "nb-gray", "👤", "납세자 방어 논리",
                    summary_res.get("taxpayer_view", ""),
                ), unsafe_allow_html=True)

            st.markdown(_notion_block_html(
                "nb-gray", "⚖️", "법원 / 심판원 최종 판단 기준",
                summary_res.get("court_decision", ""),
            ), unsafe_allow_html=True)

            st.markdown(_notion_block_html(
                "nb-green", "💼", "회계·세무팀 실무 액션 플랜 & 필수 증빙 체크리스트",
                summary_res.get("actionable_takeaway", ""),
            ), unsafe_allow_html=True)

            with st.expander("📄 사내 보고용 텍스트 전문 미리보기 & 직접 복사", expanded=False):
                st.markdown("<div style='font-size:0.84rem; color:#64748B; margin-bottom:6px;'>※ 우측 상단의 복사 아이콘(📋)을 클릭하거나 전체 선택(Ctrl+A)하여 사내 메신저나 이메일에 바로 붙여넣기 하실 수 있습니다.</div>", unsafe_allow_html=True)
                st.code(clip_text, language="markdown")

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
