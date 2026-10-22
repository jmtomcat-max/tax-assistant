# -*- coding: utf-8 -*-
"""
세무검토 사례관리 보관함 전용 안전 저장 모듈 (storage.py)
- 세무검토 사례 카드 스키마 지원 (제목, 세목, 쟁점태그, 위험등급, 검토상태, 사용자질문, 사실관계, 근거자료, AI의견, 메모 등)
- 기존 판례/진단 데이터 하위 호환 자동 마이그레이션 (migrate_legacy_item)
- 사건번호 및 유사 질문 중복 감지 (check_duplicate_case)
- 민감정보(주민등록번호, 계좌번호, API Key 등) 자동 마스킹 (sanitize_sensitive_text)
- 원자적 파일 쓰기(Atomic Write)로 프로세스 비정상 종료 시 데이터 무결성 보장
- DoS 방지 최대 보관 건수(200건) 제한
"""
import os
import re
import json
import tempfile
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import config

MAX_SAVED_CASES = 200
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_FILE = config.get_data_file_path("saved_cases.json")

VALID_REVIEW_STATUSES = ["검토중", "1차 완료", "회계사 확인 필요", "최종 완료"]
VALID_RISK_LEVELS = ["저위험", "중립/유의", "고위험"]


def sanitize_url(url: str) -> str:
    """URL에 포함된 OC 파라미터나 키를 마스킹/정제"""
    if not url:
        return ""
    return re.sub(r'([?&]OC=)[^&]+', r'\1[PROTECTED]', url, flags=re.IGNORECASE)


def sanitize_sensitive_text(text: str) -> str:
    """주민등록번호, 외국인등록번호, 계좌번호, API Key 등 민감정보 마스킹"""
    if not text or not isinstance(text, str):
        return text or ""
    
    # 1. 주민등록번호 패턴 (6자리-7자리)
    text = re.sub(r'\b(\d{6})[- ]?([1-4]\d{6})\b', r'\1-*******', text)
    
    # 2. 계좌번호 패턴 (3~6자리-2~6자리-3~8자리)
    text = re.sub(r'\b(\d{3,6})[- ]?(\d{2,6})[- ]?(\d{3,8})\b', r'\1-***-*****', text)
    
    # 3. API Key / Token 패턴 (AIza..., sk-...)
    text = re.sub(r'\b(AIza[0-9A-Za-z-_]{35})\b', r'[API_KEY_PROTECTED]', text)
    text = re.sub(r'\b(sk-[0-9A-Za-z-_]{20,})\b', r'[TOKEN_PROTECTED]', text)
    
    return text


def migrate_legacy_item(item_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    기존의 단순 판례 또는 초기 진단 데이터를 '세무검토 사례 카드'의 신규 표준 스키마로 안전하게 변환
    """
    if not isinstance(item, dict):
        return {}

    # 이미 신규 스키마인 경우 기본 검증 후 반환
    if "review_status" in item and "legal_references" in item and "facts_summary" in item:
        clean_item = dict(item)
        if clean_item.get("review_status") not in VALID_REVIEW_STATUSES:
            clean_item["review_status"] = "검토중"
        return clean_item

    # 기존 legacy 필드 추출
    title = item.get("title", "제목 미지정 세무 검토 사례")
    tax_cat = item.get("tax_category", "조세일반")
    case_no = item.get("case_number", item_id)
    saved_at = item.get("saved_at", datetime.now().strftime('%Y-%m-%d %H:%M'))
    court = item.get("court", "법원/국세청")
    date_str = item.get("date", "")
    link = sanitize_url(item.get("link", ""))
    source = item.get("source", "국가법령정보센터")
    prec_id = item.get("prec_id", "")
    ai_sum = item.get("ai_summary", {}) if isinstance(item.get("ai_summary"), dict) else {}

    # 쟁점 태그 도출
    issue_tags = item.get("issue_tags", [])
    if not issue_tags:
        tags = [tax_cat]
        for w in title.replace("[상황 진단]", "").replace("[", " ").replace("]", " ").split():
            clean_w = re.sub(r'[^가-힣a-zA-Z0-9]', '', w)
            if len(clean_w) >= 2 and clean_w not in tags and len(tags) < 4:
                tags.append(clean_w)
        issue_tags = tags

    # 위험 등급 매핑
    risk_lvl = item.get("risk_level", "중립/유의")
    if risk_lvl not in VALID_RISK_LEVELS:
        if "고위험" in str(risk_lvl) or "주의" in str(risk_lvl):
            risk_lvl = "고위험"
        elif "저위험" in str(risk_lvl) or "안전" in str(risk_lvl):
            risk_lvl = "저위험"
        else:
            risk_lvl = "중립/유의"

    # 사실관계 요약 구성
    facts_summary = item.get("facts_summary", {})
    if not facts_summary or not isinstance(facts_summary, dict):
        facts_summary = {
            "tax_category": tax_cat,
            "trans_type": title[:40],
            "counterparty": "미기재",
            "amount": "미기재",
            "tax_period": "해당 과세연도",
            "evidence_held": "확인 필요",
            "purpose": title
        }

    # 근거 자료(법령/판례) 리스트 구성
    legal_references = item.get("legal_references", [])
    if not legal_references and isinstance(legal_references, list):
        if case_no and case_no != item_id:
            legal_references.append({
                "type": "판례/예규",
                "title": title,
                "case_number": case_no,
                "court": court,
                "date": date_str,
                "link": link,
                "source": source,
                "prec_id": prec_id
            })

    # AI 검토의견 구성
    ai_opinion = item.get("ai_opinion", {})
    if not ai_opinion or not isinstance(ai_opinion, dict):
        ai_opinion = {
            "basis_strength": item.get("basis_strength", "유의 필요"),
            "basis_rationale": item.get("basis_rationale", "판례 및 법령 종합 검토"),
            "conclusion": ai_sum.get("legal_basis", "") or ai_sum.get("court_decision", "") or item.get("summary", ""),
            "case_comparison": ai_sum.get("court_decision", ""),
            "checklist": ai_sum.get("actionable_takeaway", "") or "과세관청 입증 증빙 구비 필수",
            "tax_office_view": ai_sum.get("tax_office_view", ""),
            "taxpayer_view": ai_sum.get("taxpayer_view", "")
        }

    migrated_card = {
        "case_id": item_id,
        "title": title,
        "tax_category": tax_cat,
        "issue_tags": issue_tags,
        "risk_level": risk_lvl,
        "review_status": item.get("review_status", "검토중"),
        "user_query": sanitize_sensitive_text(item.get("user_query", title)),
        "facts_summary": facts_summary,
        "legal_references": legal_references,
        "ai_opinion": ai_opinion,
        "user_memo": item.get("user_memo", ""),
        "created_at": saved_at,
        "updated_at": item.get("updated_at", saved_at),
        # 하위 호환 유지용 메타데이터
        "case_number": case_no,
        "court": court,
        "date": date_str,
        "link": link,
        "source": source,
        "prec_id": prec_id,
        "saved_at": saved_at,
        "ai_summary": ai_sum
    }

    return migrated_card


def sanitize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """저장 대상 사례 카드 살균, 민감정보 마스킹 및 길이 검증"""
    clean_item = dict(item)
    if "link" in clean_item and isinstance(clean_item["link"], str):
        clean_item["link"] = sanitize_url(clean_item["link"])
    if "user_query" in clean_item and isinstance(clean_item["user_query"], str):
        clean_item["user_query"] = sanitize_sensitive_text(clean_item["user_query"])
    if "user_memo" in clean_item and isinstance(clean_item["user_memo"], str):
        clean_item["user_memo"] = sanitize_sensitive_text(clean_item["user_memo"])
    
    # 텍스트 길이 과도 팽창 방지
    for k, v in list(clean_item.items()):
        if isinstance(v, str) and len(v) > 30000:
            clean_item[k] = v[:30000] + "... [생략됨]"
            
    return clean_item


def check_duplicate_case(saved_cases: Dict[str, Any], case_number: Optional[str] = None, user_query: Optional[str] = None, current_id: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
    """
    저장 시 기존 사례와의 중복 여부(사건번호 일치 또는 질문 유사도) 검사
    반환값: (is_duplicate, reason_message, existing_case_id)
    """
    if not saved_cases:
        return False, "", None

    # 1. 동일 사건번호 검사
    if case_number and case_number.strip():
        norm_case_no = re.sub(r'[^가-힣a-zA-Z0-9]', '', case_number)
        for cid, item in saved_cases.items():
            if current_id and cid == current_id:
                continue
            exist_no = item.get("case_number", "")
            if exist_no:
                norm_exist = re.sub(r'[^가-힣a-zA-Z0-9]', '', exist_no)
                if norm_case_no and norm_case_no == norm_exist:
                    return True, f"동일한 사건번호({exist_no})의 세무검토 사례가 이미 보관함에 존재합니다.", cid

    # 2. 질문 유사도(단어 자카드 유사도) 검사
    if user_query and len(user_query.strip()) >= 10:
        words_new = set([w for w in re.findall(r'[가-힣a-zA-Z0-9]{2,}', user_query) if w not in ["어떤가요", "가능한가요", "궁금합니다", "어떻게", "있는지"]])
        if len(words_new) >= 3:
            for cid, item in saved_cases.items():
                if current_id and cid == current_id:
                    continue
                exist_q = item.get("user_query", "") or item.get("title", "")
                words_exist = set([w for w in re.findall(r'[가-힣a-zA-Z0-9]{2,}', exist_q) if w not in ["어떤가요", "가능한가요", "궁금합니다", "어떻게", "있는지"]])
                if not words_exist:
                    continue
                intersection = words_new.intersection(words_exist)
                union = words_new.union(words_exist)
                jaccard = len(intersection) / len(union) if union else 0.0
                if jaccard >= 0.70:
                    return True, f"유사한 내용의 세무검토 질문('{item.get('title', '')[:30]}...')이 이미 보관함에 있습니다.", cid

    return False, "", None


def load_saved_cases() -> Dict[str, Any]:
    """보관함 데이터 안전 조회 및 신규 스키마 자동 마이그레이션"""
    if not os.path.exists(STORAGE_FILE):
        return {}

    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # 모든 항목을 세무검토 사례 카드 스키마로 마이그레이션 및 살균
            migrated_dict = {}
            for k, v in data.items():
                if isinstance(v, dict):
                    card = migrate_legacy_item(k, v)
                    migrated_dict[k] = sanitize_item(card)
            return migrated_dict
        return {}
    except Exception:
        return {}


def save_saved_cases(data: Dict[str, Any]) -> bool:
    """원자적 파일 쓰기(Atomic Write)로 안전하게 저장"""
    if not isinstance(data, dict):
        return False

    # 최대 저장 건수 제한 (최신순 200건 유지)
    if len(data) > MAX_SAVED_CASES:
        keys_to_keep = list(data.keys())[-MAX_SAVED_CASES:]
        data = {k: data[k] for k in keys_to_keep}

    # 스키마 마이그레이션 및 살균 처리
    clean_data = {}
    for k, v in data.items():
        if isinstance(v, dict):
            card = migrate_legacy_item(k, v)
            clean_data[k] = sanitize_item(card)

    # 원자적 쓰기: 동일 디렉터리에 임시 파일 생성 -> json 기록 -> os.replace
    temp_fd = None
    temp_path = None
    try:
        dir_name = os.path.dirname(STORAGE_FILE)
        temp_fd, temp_path = tempfile.mkstemp(prefix="saved_cases_", suffix=".tmp", dir=dir_name)
        with open(temp_fd, "w", encoding="utf-8") as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)
        temp_fd = None
        
        os.replace(temp_path, STORAGE_FILE)
        return True
    except Exception:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False


def update_case_memo_and_status(case_id: str, memo: str, status: str) -> bool:
    """보관 사례의 사용자 메모 및 검토상태를 업데이트"""
    cases = load_saved_cases()
    if case_id not in cases:
        return False
    
    cases[case_id]["user_memo"] = sanitize_sensitive_text(memo)
    if status in VALID_REVIEW_STATUSES:
        cases[case_id]["review_status"] = status
    cases[case_id]["updated_at"] = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    return save_saved_cases(cases)
