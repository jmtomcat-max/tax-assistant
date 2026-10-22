# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무·조세 판례 실시간 검색 및 AI 분석 비서 - 판례 판단/분류 로직
- components/ui_elements.py 에서 분리됨 (2026-09-14 리팩토링)
- Streamlit에 의존하지 않는 순수 판단 로직만 담당 (입력 dict -> 결과 dict/str)
- badge_html 필드는 렌더링측 호환을 위해 유지하되, 실제 st.markdown 호출은 하지 않음
"""


def determine_case_outcome(case_item: dict) -> dict:
    """
    판례/예규의 판결요지, 사건명, 결론 텍스트를 분석하여 4가지 표준 결론 배지 결정:
    - 납세자 유리 / 과세관청 유리 / 일부 인용 / 판단 불명확
    """
    text_corpus = (
        str(case_item.get("summary", "")) + " " +
        str(case_item.get("title", "")) + " " +
        str(case_item.get("core_point", "")) + " " +
        str(case_item.get("court_decision", ""))
    ).lower()

    if any(k in text_corpus for k in ["일부인용", "일부 인용", "일부취소", "일부 취소", "재조사", "경정하라", "일부승소"]):
        return {
            "label": "일부 인용",
            "badge_html": '<span class="badge-outcome-partial">🟡 일부 인용</span>',
            "detail": "일부 처분 취소 또는 재조사 경정 결정"
        }

    taxpayer_keys = ["인용", "취소한다", "원고승", "원고 승", "납세자승", "처분을 취소", "손금산입", "공제대상", "위법하다", "부당하다", "과세처분은 위법"]
    office_keys = ["기각", "각하", "원고패", "원고 패", "적법하다", "손금불산입", "매입세액불공제", "과세처분은 적법", "과세관청승"]

    has_taxpayer = any(k in text_corpus for k in taxpayer_keys)
    has_office = any(k in text_corpus for k in office_keys)

    if has_taxpayer and not has_office:
        return {
            "label": "납세자 유리",
            "badge_html": '<span class="badge-outcome-taxpayer">🟢 납세자 유리</span>',
            "detail": "과세처분 취소 또는 납세자 주장 인용"
        }
    elif has_office and not has_taxpayer:
        return {
            "label": "과세관청 유리",
            "badge_html": '<span class="badge-outcome-office">🔴 과세관청 유리</span>',
            "detail": "청구 기각 또는 과세관청 처분 적법 유지"
        }
    elif has_taxpayer and has_office:
        if "기각한다" in text_corpus or "기각됨" in text_corpus:
            return {
                "label": "과세관청 유리",
                "badge_html": '<span class="badge-outcome-office">🔴 과세관청 유리</span>',
                "detail": "납세자 청구 기각"
            }
        else:
            return {
                "label": "일부 인용",
                "badge_html": '<span class="badge-outcome-partial">🟡 일부 인용</span>',
                "detail": "쟁점별 인용 및 기각 혼재"
            }

    return {
        "label": "판단 불명확",
        "badge_html": '<span class="badge-outcome-unclear">🟠 판단 불명확</span>',
        "detail": "유권해석 원칙론 또는 사실관계 입증 여하에 따름"
    }


def derive_case_application(case_item: dict, user_query: str = "", facts: dict = None) -> str:
    """
    판례의 법리와 사용자의 세무 질의/사실관계를 대조하여 실무 적용 착안점 도출
    """
    title = case_item.get("title", "")
    summary = case_item.get("summary", "") or case_item.get("core_point", "")
    tax_cat = case_item.get("tax_category", "조세일반")
    
    app_notes = []
    if any(k in title or k in summary for k in ["대손", "회수불능", "폐업", "부도"]):
        app_notes.append("회수불능 객관적 증빙(폐업사실증명, 재산조사서 등) 구비 시 손금산입 기준 직접 원용 가능.")
    elif any(k in title or k in summary for k in ["사실과 다른", "세금계산서", "위장", "가공"]):
        app_notes.append("실제 거래 진실성 및 선의·무과실 입증(계약서, 금융이체증) 시 매입세액공제 소명 근거로 활용.")
    elif any(k in title or k in summary for k in ["특수관계", "부당행위", "시가", "가지급금"]):
        app_notes.append("특수관계인 간 적정 시가 평가서 및 이사회 결의서 구비하여 부당행위계산 부인 리스크 차단.")
    elif any(k in title or k in summary for k in ["접대비", "판매장려금", "광고선전비"]):
        app_notes.append("사전 약정서 및 지출의 상대방 범위에 따라 판매부대비용 인정 여부 판별의 핵심 기준 제시.")
    else:
        app_notes.append(f"{tax_cat} 관련 객관적 거래 증빙 및 법령상 요건 충족 여부에 따라 동일한 판단 취지 적용 가능.")

    return " ".join(app_notes)


# ----------------- 다중 판례 비교표 컴포넌트 -----------------
def get_basis_quality_meta(case_item: dict) -> dict:
    """검색 결과의 근거 품질 메타데이터를 UI 표시용으로 정규화."""
    basis_type = case_item.get("basis_type") or "참고자료"
    score = case_item.get("relevance_score")
    try:
        score_int = int(float(score)) if score not in (None, "") and str(score).strip() != "" else None
    except (ValueError, TypeError):
        score_int = None

    if basis_type == "직접근거 후보":
        color = "#175CD3"
        bg = "#EFF8FF"
        border = "#B2DDFF"
        label = "직접근거"
    elif basis_type == "보조근거 후보":
        color = "#344054"
        bg = "#F8F9FA"
        border = "#D0D5DD"
        label = "보조근거"
    elif basis_type == "사실관계 유사 후보":
        color = "#027A48"
        bg = "#ECFDF3"
        border = "#A6F4C5"
        label = "사실관계 유사"
    else:
        color = "#5925DC"
        bg = "#F4F3FF"
        border = "#D9D6FE"
        label = "참고자료"

    score_label = f"{score_int}점" if score_int is not None else "점수 없음"
    badge_html = (
        f"<span style='background:{bg}; color:{color}; border:1px solid {border}; "
        f"font-size:0.74rem; font-weight:700; padding:2px 7px; border-radius:12px; "
        f"display:inline-flex; align-items:center; white-space:nowrap;'>{label} · {score_label}</span>"
    )
    return {
        "basis_type": basis_type,
        "score": score_int,
        "label": label,
        "badge_html": badge_html,
        "match_reason": case_item.get("match_reason", ""),
        "matched_keywords": case_item.get("matched_keywords", []) or []
    }


def verify_direct_basis_eligibility(
    user_query: str,
    case_item: dict,
    intent_data: dict = None
) -> tuple:
    """
    직접근거(direct_basis) 부여 적격성을 4대 기준으로 엄격 검증합니다:
    1. 핵심 수식어(Specific Modifiers) 일치: 질의에 '무증자', '완전자회사', '포합주식', '100%', '적격' 등 특화 조건이 있을 때,
       판례 본문/전문/요지에 해당 조건 또는 동의어가 실제로 존재하는가 (부재 시 단순 일반 선례로 판정하여 direct_basis 배제)
    2. 핵심 거래대상(Transaction Type) 일치: 질의의 거래행위가 판례 내용에 실질적으로 존재하는가
    3. 세목(Tax Category) 일치: 질의 대상 세목과 판례 세목의 법리적 호환 여부
    4. 세무 쟁점(Tax Issue) 일치: 질의의 세무 쟁점이 판례에서 실제로 다루어졌는가

    Returns:
        (is_eligible: bool, reason_or_detail: str)
    """
    q_str = (user_query or "").strip()
    if not q_str:
        return True, "질의 부재 (기본 통과)"

    # 판례 검색 코퍼스 전체 (제목, 요지, 판시사항, 이유, 주문, 전문, 매칭키워드)
    corpus_parts = [
        str(case_item.get("title", "")),
        str(case_item.get("summary", "")),
        str(case_item.get("points", "")),
        str(case_item.get("reason", "")),
        str(case_item.get("order", "")),
        str(case_item.get("full_text", "")),
        " ".join(case_item.get("matched_keywords", []) or [])
    ]
    corpus = " ".join(corpus_parts)

    # 1. 특화 세부 수식어(Specific Modifiers) 맵 & 동의어 군
    SPECIFIC_MODIFIERS = {
        "무증자": ["무증자", "합병신주", "신주미교부", "신주 미교부", "주식미교부", "포합주식", "100%", "완전자회사", "모자회사", "단독주주"],
        "완전자회사": ["완전자회사", "100%", "모자회사", "단독주주", "전액출자", "완전모자", "완전자법인"],
        "포합주식": ["포합주식", "포합", "자기주식", "합병신주", "구주", "모자회사"],
        "적격": ["적격", "적격합병", "적격분할", "과세특례", "과세이연"],
        "간이": ["간이", "간이합병"],
        "소규모": ["소규모", "소규모합병"],
        "삼각": ["삼각", "삼각합병", "삼각주식교환"],
        "역합병": ["역합병", "역발행"],
        "물적분할": ["물적분할", "물적"],
        "인적분할": ["인적분할", "인적"],
        "불균등": ["불균등", "불균등감자", "불균등증자", "시가미달"],
        "명의신탁": ["명의신탁", "차명", "실소유자", "실질주주"]
    }

    # 질의에 포함된 특화 수식어 탐색
    active_modifiers = []
    for mod_key, syn_list in SPECIFIC_MODIFIERS.items():
        if mod_key in q_str:
            active_modifiers.append((mod_key, syn_list))

    if active_modifiers:
        for mod_key, syn_list in active_modifiers:
            matched = any(syn in corpus for syn in syn_list)
            if not matched:
                return False, f"특화 수식어('{mod_key}') 미포함 일반 선례"

    # 2. 핵심 거래대상(Primary Transaction Target) 검증
    KNOWN_TRANSACTIONS = [
        "합병", "분할", "영업양수도", "양도", "증여", "상속", "현물출자", "출자", 
        "감자", "증자", "배당", "대여", "가지급금", "접대비", "대손", "퇴직금", 
        "용역", "임대", "사용료", "로열티"
    ]
    query_trans = [t for t in KNOWN_TRANSACTIONS if t in q_str]
    if query_trans:
        has_trans_match = any(t in corpus for t in query_trans)
        if not has_trans_match:
            return False, f"핵심 거래대상({', '.join(query_trans[:2])}) 불일치"

    # 3. 세목(Tax Category) 일치 검증
    it_tax = case_item.get("tax_category", "조세일반")
    target_tax = (intent_data or {}).get("tax_category")
    if not target_tax or target_tax in ("조세일반", "전체"):
        for tc in ["법인세", "부가가치세", "소득세", "상속세", "증여세", "지방세", "취득세"]:
            if tc in q_str:
                target_tax = tc
                break

    if target_tax and target_tax not in ("조세일반", "전체"):
        if it_tax != "조세일반" and target_tax not in it_tax and it_tax not in target_tax:
            if (target_tax == "법인세" and it_tax in ("상속·증여세", "소득세·원천세")) or \
               (target_tax == "부가가치세" and it_tax in ("상속·증여세", "지방세")):
                return False, f"세목 불일치 (질의: {target_tax} vs 판례: {it_tax})"

    # 4. 세무 쟁점(Tax Issue) 일치 검증
    KNOWN_ISSUES = [
        "부당행위", "부당행위계산", "의제배당", "시가", "손금", "손금불산입", 
        "익금", "익금산입", "과세이연", "이월결손금", "승계", "감가상각", 
        "원천징수", "매입세액", "세금계산서", "가산세", "입증책임", "신의칙", "실질과세"
    ]
    query_issues = [iss for iss in KNOWN_ISSUES if iss in q_str]
    if query_issues:
        has_issue_match = any(iss in corpus for iss in query_issues)
        if not has_issue_match:
            return False, f"세무 쟁점({', '.join(query_issues[:2])}) 미포함"

    return True, "4대 요건(수식어·거래대상·세목·쟁점) 충족"


