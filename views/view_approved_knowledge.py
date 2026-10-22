# -*- coding: utf-8 -*-
"""회계팀이 승인한 검토 결과만 보여주는 확정 지식 보관함."""
import csv
import html
import io

import streamlit as st

from repositories.review_repo import get_review_repository


def _card(record):
    value = lambda key, default="-": html.escape(str(record.get(key) or default))
    checklist = "".join(f"<li>{html.escape(str(item))}</li>" for item in record.get("checklist", []) or [])
    sources = "".join(
        f"<li>{html.escape(str(source.get('title') or source.get('source_path') or '내부 자료'))}</li>"
        for source in record.get("knowledge_sources", []) or []
    )
    return f"""
    <article class="approved-card">
      <div class="approved-status">✓ 승인 완료</div>
      <h3>{value('query', '제목 없음')}</h3>
      <p class="approved-issue"><b>핵심 쟁점</b> · {value('core_issue', '미등록')}</p>
      <div class="approved-label">✓ 승인 결론</div>
      <div class="approved-conclusion">{value('briefing_conclusion', '승인 결론 없음')}</div>
      <p class="approved-meta">{value('tax_category', '조세일반')} · 승인자 {value('knowledge_reviewed_by')} · 승인일 {value('knowledge_reviewed_at')} · 기준일 {value('applied_tax_base_date')}</p>
      <details><summary>›　근거와 실무 체크리스트</summary><div class="approved-detail">
        <b>승인 결론 전체보기</b><p>{value('briefing_conclusion', '승인 결론 없음')}</p>
        {f'<b>리스크</b><p>{value("risk_reason")}</p>' if record.get('risk_reason') else ''}
        {f'<b>실무 체크리스트</b><ul>{checklist}</ul>' if checklist else ''}
        {f'<b>사용한 내부 지식</b><ul>{sources}</ul>' if sources else ''}
      </div></details>
    </article>"""


def render_approved_knowledge_view():
    repo = get_review_repository()
    records = repo.get_approved_records()

    st.html("""
        <style>
            .approved-heading { margin: 0 0 .9rem; }
            .approved-eyebrow { color: #008F69; font-size: .7rem; font-weight: 850; letter-spacing: .1em; }
            .approved-heading h1 { margin: .15rem 0 .2rem; color: #10231E; font-size: 1.75rem; letter-spacing: -.04em; }
            .approved-heading p { margin: 0; color: #64756F; font-size: .82rem; }
            div[class*="st-key-approved-card-"] { height: 420px !important; min-height: 420px !important;
                padding: 12px 14px !important; overflow: hidden !important;
                box-sizing: border-box !important;
                -webkit-font-smoothing: auto !important; text-rendering: optimizeLegibility;
                background: #FFFFFF; border: 1px solid #D8E6E1; border-radius: 10px;
                box-shadow: 0 5px 14px rgba(12, 61, 47, .04);
                transition: all .2s cubic-bezier(.16, 1, .3, 1); }
            div[class*="st-key-approved-card-"] [data-testid="stVerticalBlockBorderWrapper"] {
                height: 100% !important; overflow: hidden !important; box-sizing: border-box !important; }
            div[class*="st-key-approved-card-"]:has(details[open]) [data-testid="stVerticalBlockBorderWrapper"] {
                height: 100% !important; overflow-y: auto !important; }
            div[class*="st-key-approved-card-"]:hover {
                background: linear-gradient(135deg, #F0FDF4 0%, #FAFDFB 60%, #FFFFFF 100%) !important;
                border-color: #A7D7C9 !important; border-left: 4px solid #005B45 !important;
                box-shadow: 0 6px 18px rgba(0, 91, 69, .10), 0 2px 6px rgba(15, 23, 42, .04) !important;
                transform: translateY(-2px); }
            div[class*="st-key-approved-card-"] [data-testid="stVerticalBlock"] { gap: .35rem !important; }
            div[class*="st-key-approved-card-"] h3,
            div[class*="st-key-approved-card-"] strong { color: #005B45 !important; }
            div[class*="st-key-approved-card-"] h3 { margin: 0 !important; color: #0B1222 !important;
                font-size: 1rem !important; font-weight: 800 !important; line-height: 1.4 !important; display: -webkit-box;
                -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }
            div[class*="st-key-approved-card-"] p,
            div[class*="st-key-approved-card-"] li,
            div[class*="st-key-approved-card-"] span { color: #1E293B !important; font-size: .8rem !important; }
            div[class*="st-key-approved-card-"] [data-testid="stMarkdownContainer"] p {
                color: #111827 !important; font-size: .85rem !important; font-weight: 650 !important; line-height: 1.5 !important; }
            div[class*="st-key-approved-card-"] [data-testid="stCaptionContainer"] p { color: #334155 !important;
                font-size: .75rem !important; font-weight: 650 !important; line-height: 1.45 !important;
                display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }
            div[class*="st-key-approved-card-"] [data-testid="stAlert"] { padding: 8px 10px !important;
                background: #F0FDF4 !important; border: 0 !important; border-left: 3px solid #008F69 !important;
                border-radius: 7px !important; }
            div[class*="st-key-approved-card-"] [data-testid="stAlert"] > div { background: transparent !important; }
            div[class*="st-key-approved-card-"] [data-testid="stAlert"] p { color: #111827 !important;
                font-size: .86rem !important; font-weight: 650 !important; line-height: 1.55 !important;
                display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 4; overflow: hidden; }
            div[class*="st-key-approved-card-"] [data-testid="stMarkdownContainer"] strong {
                color: #005B45 !important; font-size: .76rem !important; }
            div[class*="st-key-approved-card-"] details { border-color: #D8E6E1 !important; }
            div[class*="st-key-approved-card-"] summary { min-height: 30px !important; padding: 4px 0 !important;
                color: #005B45 !important; font-size: .75rem !important; }
            .approved-card { position:relative; height:420px; box-sizing:border-box; display:flex; flex-direction:column; gap:9px;
                padding: 14px 16px; overflow: hidden; background: #fff; border: 1px solid #D8E6E1; border-radius: 10px;
                box-shadow: 0 5px 14px rgba(12,61,47,.04); color: #111827; transition: all .2s cubic-bezier(.16,1,.3,1);
                -webkit-font-smoothing: auto; text-rendering: optimizeLegibility; }
            .approved-card:hover { background: linear-gradient(135deg,#F0FDF4 0%,#FAFDFB 60%,#fff 100%);
                border-color:#A7D7C9; border-left:4px solid #005B45; box-shadow:0 6px 18px rgba(0,91,69,.10);
                transform:translateY(-2px); }
            .approved-status,.approved-label { align-self:flex-start; padding:4px 9px; border-radius:999px;
                font-size:11px; font-weight:800; line-height:1.2; }
            .approved-status { color:#007A5A; background:#E9F7F2; border:1px solid #C8EBDD; }
            .approved-label { color:#B33B27; background:#FFF0EC; border:1px solid #FFD2C8; }
            .approved-card h3 { margin:0; color:#0B1222; font-size:15px; font-weight:800; line-height:1.4;
                display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:2; overflow:hidden; }
            .approved-issue { margin:0; color:#1E293B; font-size:13px; font-weight:650; line-height:1.45;
                display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:2; overflow:hidden; }
            .approved-issue b { color:#005B45; }
            .approved-conclusion { min-height:112px; padding:10px 12px; overflow:hidden; color:#111827; background:#F0FDF4;
                border-left:3px solid #008F69; border-radius:7px; font-size:13px; font-weight:650; line-height:1.55;
                display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:5; }
            .approved-meta { margin:0; color:#334155; font-size:11.5px; font-weight:650; line-height:1.4;
                display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:2; overflow:hidden; }
            .approved-card details { margin-top:auto; color:#111827; font-size:12px; }
            .approved-card details[open] { position:absolute; z-index:5; width:calc(100% - 32px); max-height:360px; overflow:auto;
                padding:10px; background:#fff; border:1px solid #A7D7C9; border-radius:8px; box-shadow:0 8px 24px rgba(0,91,69,.14); }
            .approved-card summary { padding:9px 10px; cursor:pointer; color:#111827; border:1px solid #D8E6E1;
                border-radius:7px; font-size:12px; font-weight:750; list-style:none; }
            .approved-detail { padding:10px 2px 0; line-height:1.55; }
        </style>
        <div class="approved-heading">
            <div class="approved-eyebrow">APPROVED KNOWLEDGE</div>
            <h1>승인된 자료</h1>
            <p>회계팀이 공식 근거를 확인하고 승인한 검토 결과를 모았습니다.</p>
        </div>
    """)

    query = st.text_input("승인 지식 검색", placeholder="질문, 쟁점, 세목으로 검색")
    if query.strip():
        records = repo.get_approved_records(query.strip())

    left, right = st.columns([4, 1])
    left.markdown(f"**승인 지식 · {len(records)}건**")
    if records:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["질문", "세목", "핵심 쟁점", "승인 결론", "승인자", "승인일", "기준 세법일"])
        for record in records:
            writer.writerow([
                record.get("query", ""), record.get("tax_category", ""), record.get("core_issue", ""),
                record.get("briefing_conclusion", ""), record.get("knowledge_reviewed_by", ""),
                record.get("knowledge_reviewed_at", ""), record.get("applied_tax_base_date", ""),
            ])
        right.download_button(
            "CSV 다운로드", "\ufeff" + output.getvalue(), "approved_tax_knowledge.csv", "text/csv",
            use_container_width=True,
        )

    if not records:
        st.info("아직 승인된 지식이 없습니다. 지식 승인센터에서 후보 답변의 결론과 공식 근거를 확인한 뒤 승인해 주세요.")
        if st.button("지식 승인센터로 이동", type="primary"):
            st.session_state["active_view"] = "review_history"
            st.query_params["view"] = "review_history"
            st.rerun()
        return

    columns = st.columns(3)
    for index, record in enumerate(records):
        columns[index % 3].html(_card(record))
