# -*- coding: utf-8 -*-
"""
CJ프레시웨이 세무 리서치 & AI 검토 - 검토 기록(Review History) 전용 Repository 모듈
- 4대 엔터프라이즈 아키텍처 원칙 준수:
  1. 분석 완료 후 안전한 동기 저장 (Safe Synchronous Save)
  2. 질의 지문(Fingerprint) 기반 중복 방지 및 갱신 (Upsert)
  3. 완전 삭제 대신 보관 처리(Soft Delete) & 불변 감사 로그(Audit Log)
  4. 향후 SQLite / 사내 DB로 교체 가능한 Repository 인터페이스 구조 (DIP)
"""
import os
import re
import json
import sqlite3
import hashlib
import tempfile
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import config
from storage import sanitize_sensitive_text
from repositories.tax_knowledge_repo import _has_sufficient_relevance, _search_tokens

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = config.get_data_file_path("review_history.json")
AUDIT_LOG_FILE = config.get_data_file_path("audit_trail.jsonl")
SQLITE_DB_FILE = config.get_data_file_path("review_history.db")

_file_lock = threading.Lock()

KNOWLEDGE_STATUSES = {"candidate", "reviewing", "approved", "rejected", "superseded"}
FEEDBACK_RATINGS = {"helpful", "needs_correction"}


def _validate_knowledge_status(status: str, note: str = "") -> str:
    normalized = (status or "").strip().lower()
    if normalized not in KNOWLEDGE_STATUSES:
        raise ValueError(f"지원하지 않는 지식 상태입니다: {status}")
    if normalized in {"rejected", "superseded"} and not (note or "").strip():
        raise ValueError("반려 또는 대체 처리에는 검토 메모가 필요합니다.")
    return normalized


def _normalize_knowledge_sources(sources: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Keep only traceable metadata for internal knowledge used by a review."""
    normalized = []
    for source in (sources or [])[:5]:
        if not isinstance(source, dict) or source.get("document_id") is None:
            continue
        normalized.append({
            "document_id": source.get("document_id"),
            "title": str(source.get("title", ""))[:300],
            "source_path": str(source.get("source_path", ""))[:1000],
            "content_sha256": str(source.get("content_sha256", ""))[:64],
            "score": source.get("score", 0),
            "knowledge_type": str(source.get("knowledge_type", "obsidian"))[:30],
            "reviewed_by": str(source.get("reviewed_by", ""))[:200],
            "reviewed_at": str(source.get("reviewed_at", ""))[:30],
        })
    return normalized


def compute_query_fingerprint(query: str, tax_category: str = "전체") -> str:
    """
    질의 텍스트와 세목을 정규화하여 고유한 질의 지문(Fingerprint) 해시를 생성.
    - 특수문자 제거, 연속 공백 단일화, 소문자화
    - 불용어 정리 후 SHA-256 16자리 다이제스트 반환
    """
    q_norm = (query or "").strip().lower()
    q_norm = re.sub(r'[\r\n\t]', ' ', q_norm)
    q_norm = re.sub(r'[^\w\s가-힣]', '', q_norm)
    q_norm = re.sub(r'\s+', ' ', q_norm).strip()
    
    tax_norm = (tax_category or "전체").strip().lower()
    
    composite = f"{tax_norm}::{q_norm}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()[:16]


def _tokenize_review_search_query(query: str) -> List[str]:
    """내부 문서 검색과 같은 기준으로 의미 토큰을 추출."""
    return _search_tokens(query)


def _filter_and_rank_records(records: List[Dict[str, Any]], search_query: str) -> List[Dict[str, Any]]:
    """
    [Requirement 11] 지능형 토큰 분리 AND/OR 검색 및 전방위 필드 확장 가중치 랭킹
    - 공백 압축 일치: +50~60점
    - 필드별 토큰 매칭: query/issue +30, keywords +25, conclusion +20, cases +15, comparison/risk/checklist +10, full +5
    - 모든 토큰 AND 일치: +40점
    - 관련도 점수 내림차순, 최신순 정렬
    """
    if not search_query or not search_query.strip():
        records_copy = list(records)
        records_copy.sort(key=lambda x: str(x.get("last_reviewed_at", "")), reverse=True)
        return records_copy

    sq_raw = search_query.strip().lower()
    sq_nospace = re.sub(r'\s+', '', sq_raw)
    tokens = _tokenize_review_search_query(sq_raw)

    filtered_with_scores = []
    for r in records:
        q_txt = str(r.get("query", "")).lower()
        issue_txt = str(r.get("core_issue", "")).lower()
        conc_txt = str(r.get("briefing_conclusion", "")).lower()
        kws_txt = " ".join([str(k) for k in r.get("active_keywords", [])]).lower()
        comp_txt = str(r.get("case_comparison", "")).lower()
        risk_rsn_txt = str(r.get("risk_reason", "")).lower()
        chk_txt = " ".join([str(c) for c in r.get("checklist", [])]).lower()

        top_cases_list = r.get("top_cases", []) or []
        cases_parts = []
        for tc in top_cases_list:
            if isinstance(tc, dict):
                cases_parts.append(f"{tc.get('title', '')} {tc.get('case_number', '')} {tc.get('summary', '')}")
        cases_txt = " ".join(cases_parts).lower()

        bf = r.get("briefing_full", {})
        bf_txt = json.dumps(bf, ensure_ascii=False).lower() if isinstance(bf, (dict, list)) else str(bf).lower()
        knowledge_txt = json.dumps(r.get("knowledge_sources", []), ensure_ascii=False).lower()

        full_corpus = f"{q_txt} {issue_txt} {conc_txt} {kws_txt} {comp_txt} {risk_rsn_txt} {chk_txt} {cases_txt} {knowledge_txt} {bf_txt}"
        full_corpus_nospace = re.sub(r'\s+', '', full_corpus)

        score = 0
        matched_tokens = set()

        # A. 구문 / 띄어쓰기 압축 일치 검사
        if sq_raw in full_corpus:
            score += 60
        elif len(sq_nospace) >= 2 and sq_nospace in full_corpus_nospace:
            score += 50

        # B. 개별 토큰 필드별 가중치 매칭 검사
        for tok in tokens:
            tok_nospace = re.sub(r'\s+', '', tok)
            tok_matched = False
            if tok in q_txt or tok in issue_txt or (tok_nospace and tok_nospace in re.sub(r'\s+', '', q_txt)):
                score += 30
                tok_matched = True
            if tok in kws_txt:
                score += 25
                tok_matched = True
            if tok in conc_txt:
                score += 20
                tok_matched = True
            if tok in cases_txt:
                score += 15
                tok_matched = True
            if tok in knowledge_txt:
                score += 15
                tok_matched = True
            if tok in comp_txt or tok in risk_rsn_txt or tok in chk_txt:
                score += 10
                tok_matched = True
            if tok in bf_txt:
                score += 5
                tok_matched = True
            if not tok_matched and tok_nospace and tok_nospace in full_corpus_nospace:
                score += 8
                tok_matched = True

            if tok_matched:
                matched_tokens.add(tok)

        # C. AND 매칭 보너스 (질의의 모든 토큰이 어디든 존재할 때)
        if tokens and len(matched_tokens) == len(tokens):
            score += 40

        # D. 매칭 판정
        if _has_sufficient_relevance(tokens, matched_tokens):
            r_copy = dict(r)
            r_copy["_search_score"] = score
            filtered_with_scores.append(r_copy)

    # 관련도 점수 우선, 그 다음 최신순 정렬
    filtered_with_scores.sort(
        key=lambda x: (x.get("_search_score", 0), str(x.get("last_reviewed_at", ""))),
        reverse=True
    )
    return filtered_with_scores


class BaseReviewRepository(ABC):
    """
    검토 기록 데이터 액세스 추상 인터페이스 (Repository Pattern)
    향후 SQLite, PostgreSQL, 사내 DB로 교체 시 이 인터페이스만 구현하면 됨.
    """
    @abstractmethod
    def save_review(
        self,
        query: str,
        tax_category: str,
        core_issue: str,
        active_keywords: List[str],
        risk_level: str,
        briefing_conclusion: str,
        checklist: List[str],
        direct_basis_count: int,
        total_results_count: int,
        top_cases: List[Dict[str, Any]],
        applied_tax_base_date: str = "",
        model_used: str = "",
        user_id: str = "jongmin.park1@cj.net",
        case_comparison: str = "",
        risk_reason: str = "",
        briefing_full: Optional[Dict[str, Any]] = None,
        selected_category: str = "전체",
        current_focus: str = "종합 검토",
        results_fingerprint: str = "",
        files_fingerprint: str = "no_files",
        knowledge_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, bool]:
        """
        검토 기록을 동기 저장하거나 기존 지문이 있으면 갱신(Upsert).
        반환: (record_id, is_new)
        """
        pass

    @abstractmethod
    def get_all(self, include_archived: bool = False, search_query: str = "", tax_category: str = "전체") -> List[Dict[str, Any]]:
        """검토 기록 목록 조회"""
        pass

    @abstractmethod
    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """단건 검토 기록 조회"""
        pass

    @abstractmethod
    def set_knowledge_status(
        self, record_id: str, status: str, reviewer: str, note: str = ""
    ) -> bool:
        """검토 결과를 후보/검토중/승인/반려/대체 상태로 전환."""
        pass

    @abstractmethod
    def get_approved_records(self, search_query: str = "") -> List[Dict[str, Any]]:
        """다음 RAG 단계에서 사용할 승인 지식만 조회."""
        pass

    @abstractmethod
    def set_feedback(self, record_id: str, rating: str, user_id: str, note: str = "") -> bool:
        """사용자 평가를 저장하여 품질 개선 신호로 사용."""
        pass

    @abstractmethod
    def resolve_feedback(self, record_id: str, assignee: str, note: str) -> bool:
        """수정 필요 피드백을 처리 완료하고 감사 이력을 남김."""
        pass

    @abstractmethod
    def archive_record(self, record_id: str, user_id: str = "jongmin.park1@cj.net", reason: str = "") -> bool:
        """소프트 딜리트: 보관 처리 (물리 삭제가 아닌 is_archived = True 전환)"""
        pass

    @abstractmethod
    def restore_record(self, record_id: str, user_id: str = "jongmin.park1@cj.net") -> bool:
        """보관된 기록 복원"""
        pass

    @abstractmethod
    def get_kpi_stats(self) -> Dict[str, Any]:
        """통계 KPI 데이터 산출 (총 건수, 세목별 건수, 최근 검토 일시 등)"""
        pass


class JsonReviewRepository(BaseReviewRepository):
    """
    JSON 파일 기반 안전 동기 저장소 구현체.
    - 원자적 파일 쓰기(Atomic Write)
    - 파일 잠금(Thread Lock)
    - 불변 감사 로그(audit_trail.jsonl) 분리 기록
    """
    def __init__(self, file_path: str = HISTORY_FILE, audit_path: str = AUDIT_LOG_FILE):
        self.file_path = file_path
        self.audit_path = audit_path

    def _append_audit_log(self, action: str, record_id: str, user_id: str, details: Dict[str, Any]):
        """감사 추적 로그(불변 Append-only JSONL) 기록"""
        try:
            event = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": action,
                "record_id": record_id,
                "user_id": user_id,
                "details": details
            }
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass  # 감사 로그 실패가 메인 트랜잭션을 중단시키지 않음

    def _read_data(self) -> Dict[str, Any]:
        """안전한 JSON 읽기"""
        if not os.path.exists(self.file_path):
            return {"version": 1, "records": {}}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"version": 1, "records": {}}
                if "records" not in data:
                    data["records"] = {}
                return data
        except Exception:
            return {"version": 1, "records": {}}

    def _atomic_write_data(self, data: Dict[str, Any]) -> bool:
        """원자적 파일 교체 쓰기 (OS 레벨 충돌 방지)"""
        dir_name = os.path.dirname(self.file_path)
        os.makedirs(dir_name, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                json.dump(data, tf, ensure_ascii=False, indent=2)
                temp_name = tf.name
            os.replace(temp_name, self.file_path)
            return True
        except Exception:
            if 'temp_name' in locals() and os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass
            return False

    def save_review(
        self,
        query: str,
        tax_category: str,
        core_issue: str,
        active_keywords: List[str],
        risk_level: str,
        briefing_conclusion: str,
        checklist: List[str],
        direct_basis_count: int,
        total_results_count: int,
        top_cases: List[Dict[str, Any]],
        applied_tax_base_date: str = "",
        model_used: str = "",
        user_id: str = "jongmin.park1@cj.net",
        case_comparison: str = "",
        risk_reason: str = "",
        briefing_full: Optional[Dict[str, Any]] = None,
        selected_category: str = "전체",
        current_focus: str = "종합 검토",
        results_fingerprint: str = "",
        files_fingerprint: str = "no_files",
        knowledge_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, bool]:
        if not query or not query.strip():
            return "", False

        clean_query = sanitize_sensitive_text(query.strip())
        clean_issue = sanitize_sensitive_text(core_issue or "")
        clean_conclusion = sanitize_sensitive_text(briefing_conclusion or "")
        clean_case_comp = sanitize_sensitive_text(case_comparison or "")
        clean_risk_reason = sanitize_sensitive_text(risk_reason or "")
        clean_knowledge_sources = _normalize_knowledge_sources(knowledge_sources)
        
        fingerprint = compute_query_fingerprint(clean_query, tax_category)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 결과 지문 자동 계산 (미전달 시 top_cases 기반 생성)
        if not results_fingerprint and top_cases:
            c_tokens = [f"{c.get('case_number', '')}_{c.get('title', '')}" for c in top_cases]
            results_fingerprint = hashlib.sha256("_".join(c_tokens).encode("utf-8")).hexdigest()[:16]

        with _file_lock:
            data = self._read_data()
            records = data.get("records", {})

            # 지문(fingerprint) 기반 기존 레코드 검색
            existing_id = None
            for rid, rec in records.items():
                if rec.get("query_fingerprint") == fingerprint:
                    existing_id = rid
                    break

            if existing_id:
                # [Upsert] 기존 레코드 갱신
                rec = records[existing_id]
                rec["review_count"] = rec.get("review_count", 1) + 1
                rec["last_reviewed_at"] = now_str
                rec["core_issue"] = clean_issue or rec.get("core_issue", "")
                rec["briefing_conclusion"] = clean_conclusion or rec.get("briefing_conclusion", "")
                rec["risk_level"] = risk_level or rec.get("risk_level", "중립/유의")
                rec["direct_basis_count"] = direct_basis_count
                rec["total_results_count"] = total_results_count
                rec["applied_tax_base_date"] = applied_tax_base_date or config.get_tax_base_date()
                rec["model_used"] = model_used or config.get_ai_service_name()
                
                # [Requirement 13] 기존 기록 갱신 시 활성 키워드 갱신
                rec["active_keywords"] = active_keywords or rec.get("active_keywords", [])
                
                # [Requirement 12] 검색 조건 및 결과 추적 필드 갱신
                rec["selected_category"] = selected_category or rec.get("selected_category", "전체")
                rec["current_focus"] = current_focus or rec.get("current_focus", "종합 검토")
                rec["results_fingerprint"] = results_fingerprint or rec.get("results_fingerprint", "")
                rec["files_fingerprint"] = files_fingerprint or rec.get("files_fingerprint", "no_files")

                if top_cases:
                    rec["top_cases"] = top_cases[:5]
                if checklist:
                    rec["checklist"] = checklist[:5]
                if clean_case_comp:
                    rec["case_comparison"] = clean_case_comp
                if clean_risk_reason:
                    rec["risk_reason"] = clean_risk_reason
                if briefing_full:
                    rec["briefing_full"] = briefing_full
                rec["knowledge_sources"] = clean_knowledge_sources or rec.get("knowledge_sources", [])
                # 재검토로 결론이 바뀔 수 있으므로 기존 승인을 자동 승계하지 않습니다.
                rec["knowledge_status"] = "candidate"
                rec["knowledge_reviewed_by"] = ""
                rec["knowledge_reviewed_at"] = ""
                rec["knowledge_review_note"] = ""
                rec["feedback_rating"] = ""
                rec["feedback_note"] = ""
                rec["feedback_by"] = ""
                rec["feedback_at"] = ""
                rec["feedback_resolved_at"] = ""
                rec["feedback_resolved_by"] = ""
                rec["feedback_resolution_note"] = ""
                rec["is_archived"] = False  # 재검토 시 활성화 복원

                # [Requirement 12] 동일 질의 조건 및 결과 변화 추적 이력 누적
                if "revisions" not in rec or not isinstance(rec["revisions"], list):
                    rec["revisions"] = []
                rec["revisions"].append({
                    "review_index": rec["review_count"],
                    "reviewed_at": now_str,
                    "active_keywords": rec["active_keywords"],
                    "selected_category": rec["selected_category"],
                    "current_focus": rec["current_focus"],
                    "results_fingerprint": rec["results_fingerprint"],
                    "files_fingerprint": rec["files_fingerprint"],
                    "total_results_count": total_results_count,
                    "direct_basis_count": direct_basis_count,
                    "risk_level": rec["risk_level"],
                    "briefing_conclusion": clean_conclusion[:150],
                    "knowledge_document_ids": [s["document_id"] for s in clean_knowledge_sources],
                })
                rec["revisions"] = rec["revisions"][-20:]

                saved = self._atomic_write_data(data)
                if not saved:
                    return "", False

                self._append_audit_log("UPDATE_REVIEW", existing_id, user_id, {
                    "fingerprint": fingerprint,
                    "review_count": rec["review_count"],
                    "active_keywords": rec["active_keywords"],
                    "query_snippet": clean_query[:50],
                    "knowledge_source_count": len(clean_knowledge_sources),
                })
                return existing_id, False
            else:
                # [Insert] 신규 레코드 생성
                new_id = f"rev_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{fingerprint[:6]}"
                new_record = {
                    "id": new_id,
                    "query_fingerprint": fingerprint,
                    "first_created_at": now_str,
                    "last_reviewed_at": now_str,
                    "review_count": 1,
                    "is_archived": False,
                    "user_id": user_id,
                    "query": clean_query,
                    "tax_category": tax_category or "조세일반",
                    "core_issue": clean_issue,
                    "active_keywords": active_keywords or [],
                    "selected_category": selected_category or "전체",
                    "current_focus": current_focus or "종합 검토",
                    "results_fingerprint": results_fingerprint or "",
                    "files_fingerprint": files_fingerprint or "no_files",
                    "risk_level": risk_level or "중립/유의",
                    "risk_reason": clean_risk_reason,
                    "briefing_conclusion": clean_conclusion,
                    "case_comparison": clean_case_comp,
                    "checklist": checklist[:5] if checklist else [],
                    "direct_basis_count": direct_basis_count,
                    "total_results_count": total_results_count,
                    "top_cases": top_cases[:5] if top_cases else [],
                    "briefing_full": briefing_full or {},
                    "knowledge_sources": clean_knowledge_sources,
                    "knowledge_status": "candidate",
                    "knowledge_reviewed_by": "",
                    "knowledge_reviewed_at": "",
                    "knowledge_review_note": "",
                    "feedback_rating": "",
                    "feedback_note": "",
                    "feedback_by": "",
                    "feedback_at": "",
                    "feedback_resolved_at": "",
                    "feedback_resolved_by": "",
                    "feedback_resolution_note": "",
                    "applied_tax_base_date": applied_tax_base_date or config.get_tax_base_date(),
                    "model_used": model_used or config.get_ai_service_name(),
                    "revisions": [{
                        "review_index": 1,
                        "reviewed_at": now_str,
                        "active_keywords": active_keywords or [],
                        "selected_category": selected_category or "전체",
                        "current_focus": current_focus or "종합 검토",
                        "results_fingerprint": results_fingerprint or "",
                        "files_fingerprint": files_fingerprint or "no_files",
                        "total_results_count": total_results_count,
                        "direct_basis_count": direct_basis_count,
                        "risk_level": risk_level or "중립/유의",
                        "briefing_conclusion": clean_conclusion[:150],
                        "knowledge_document_ids": [s["document_id"] for s in clean_knowledge_sources],
                    }]
                }
                records[new_id] = new_record
                data["records"] = records

                saved = self._atomic_write_data(data)
                if not saved:
                    return "", False

                self._append_audit_log("CREATE_REVIEW", new_id, user_id, {
                    "fingerprint": fingerprint,
                    "tax_category": tax_category,
                    "query_snippet": clean_query[:50],
                    "knowledge_source_count": len(clean_knowledge_sources),
                })
                return new_id, True

    def get_all(self, include_archived: bool = False, search_query: str = "", tax_category: str = "전체") -> List[Dict[str, Any]]:
        with _file_lock:
            data = self._read_data()
            records = list(data.get("records", {}).values())

        # 1. 보관 처리 필터
        if not include_archived:
            records = [r for r in records if not r.get("is_archived", False)]

        # 2. 세목 필터
        if tax_category and tax_category != "전체":
            records = [r for r in records if r.get("tax_category") == tax_category]

        # 3. 토큰화·다중 필드 말뭉치 및 관련도 랭킹 적용
        return _filter_and_rank_records(records, search_query)

    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        with _file_lock:
            data = self._read_data()
            return data.get("records", {}).get(record_id)

    def set_knowledge_status(self, record_id: str, status: str, reviewer: str, note: str = "") -> bool:
        status = _validate_knowledge_status(status, note)
        reviewer = (reviewer or "").strip()
        if not reviewer:
            raise ValueError("검토자 이름 또는 계정이 필요합니다.")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _file_lock:
            data = self._read_data()
            record = data.get("records", {}).get(record_id)
            if not record:
                return False
            previous = record.get("knowledge_status", "candidate")
            record["knowledge_status"] = status
            record["knowledge_reviewed_by"] = reviewer
            record["knowledge_reviewed_at"] = now_str
            record["knowledge_review_note"] = sanitize_sensitive_text(note or "")
            if not self._atomic_write_data(data):
                return False
        self._append_audit_log("KNOWLEDGE_STATUS_CHANGED", record_id, reviewer, {
            "from": previous, "to": status, "note": sanitize_sensitive_text(note or "")[:300]
        })
        return True

    def get_approved_records(self, search_query: str = "") -> List[Dict[str, Any]]:
        records = self.get_all(include_archived=False, search_query=search_query)
        return [r for r in records if r.get("knowledge_status", "candidate") == "approved"]

    def set_feedback(self, record_id: str, rating: str, user_id: str, note: str = "") -> bool:
        rating = (rating or "").strip().lower()
        if rating not in FEEDBACK_RATINGS:
            raise ValueError("지원하지 않는 피드백 값입니다.")
        if rating == "needs_correction" and not (note or "").strip():
            raise ValueError("수정 필요 평가에는 구체적인 사유가 필요합니다.")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _file_lock:
            data = self._read_data()
            record = data.get("records", {}).get(record_id)
            if not record:
                return False
            record.update({
                "feedback_rating": rating,
                "feedback_note": sanitize_sensitive_text(note or ""),
                "feedback_by": (user_id or "anonymous").strip(),
                "feedback_at": now_str,
                "feedback_resolved_at": "",
                "feedback_resolved_by": "",
                "feedback_resolution_note": "",
            })
            if not self._atomic_write_data(data):
                return False
        self._append_audit_log("REVIEW_FEEDBACK", record_id, user_id, {"rating": rating, "note": note[:300]})
        return True

    def resolve_feedback(self, record_id: str, assignee: str, note: str) -> bool:
        if not (note or "").strip():
            raise ValueError("처리 완료 근거를 입력해 주세요.")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _file_lock:
            data = self._read_data()
            record = data.get("records", {}).get(record_id)
            if not record or record.get("feedback_rating") != "needs_correction":
                return False
            record.update({
                "feedback_resolved_at": now_str,
                "feedback_resolved_by": (assignee or "").strip(),
                "feedback_resolution_note": sanitize_sensitive_text(note),
            })
            if not self._atomic_write_data(data):
                return False
        self._append_audit_log("FEEDBACK_RESOLVED", record_id, assignee, {"note": note[:300]})
        return True

    def archive_record(self, record_id: str, user_id: str = "jongmin.park1@cj.net", reason: str = "") -> bool:
        """완전 삭제 대신 보관 처리 (Soft Delete)"""
        with _file_lock:
            data = self._read_data()
            records = data.get("records", {})
            if record_id in records:
                records[record_id]["is_archived"] = True
                records[record_id]["archived_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                records[record_id]["archived_by"] = user_id
                records[record_id]["archived_reason"] = reason or "사용자 보관 요청"
                saved = self._atomic_write_data(data)
                if not saved:
                    return False
                self._append_audit_log("ARCHIVE_REVIEW", record_id, user_id, {"reason": reason})
                return True
            return False

    def restore_record(self, record_id: str, user_id: str = "jongmin.park1@cj.net") -> bool:
        """보관된 기록 복원"""
        with _file_lock:
            data = self._read_data()
            records = data.get("records", {})
            if record_id in records:
                records[record_id]["is_archived"] = False
                records[record_id].pop("archived_at", None)
                saved = self._atomic_write_data(data)
                if not saved:
                    return False
                self._append_audit_log("RESTORE_REVIEW", record_id, user_id, {})
                return True
            return False

    def get_kpi_stats(self) -> Dict[str, Any]:
        """KPI 통계 요약"""
        with _file_lock:
            data = self._read_data()
            all_records = list(data.get("records", {}).values())

        active = [r for r in all_records if not r.get("is_archived", False)]
        tax_counts = {}
        status_counts = {status: 0 for status in KNOWLEDGE_STATUSES}
        feedback_counts = {rating: 0 for rating in FEEDBACK_RATINGS}
        knowledge_source_uses = 0
        for r in active:
            t = r.get("tax_category", "기타")
            tax_counts[t] = tax_counts.get(t, 0) + 1
            status = r.get("knowledge_status", "candidate")
            status_counts[status] = status_counts.get(status, 0) + 1
            rating = r.get("feedback_rating", "")
            if rating in feedback_counts:
                feedback_counts[rating] += 1
            knowledge_source_uses += len(r.get("knowledge_sources", []) or [])

        # [Requirement 15] 활성 기록을 last_reviewed_at 최신순으로 정렬하여 정확한 최근 검토일자 산출
        active.sort(key=lambda x: str(x.get("last_reviewed_at", "")), reverse=True)
        recent_dt = active[0].get("last_reviewed_at", "-") if active else "-"
        total_runs = sum(r.get("review_count", 1) for r in active)

        return {
            "total_active_cases": len(active),
            "total_reviews_run": total_runs,
            "archived_count": len(all_records) - len(active),
            "recent_reviewed_at": recent_dt,
            "tax_distribution": tax_counts,
            "knowledge_status_counts": status_counts,
            "feedback_counts": feedback_counts,
            "knowledge_source_uses": knowledge_source_uses,
        }


# ==============================================================================
# [Requirement 16] 중기 확장 대비 SQLite 엔터프라이즈 저장소 구현체
# ==============================================================================
class SqliteReviewRepository(BaseReviewRepository):
    """
    SQLite 기반의 고성능·멀티프로세스 동시성 보장 검토 기록 저장소 구현체.
    - WAL(Write-Ahead Logging) 모드로 다중 프로세스/스레드 동시 읽기 및 쓰기 충돌 방지
    - busy_timeout=10000ms 설정으로 파일 락 대기 및 경쟁 완화
    - 완벽한 ACID 트랜잭션(Commit/Rollback)
    - 레거시 JSON(review_history.json, audit_trail.jsonl) 데이터 자동 무손실 마이그레이션 지원
    """
    def __init__(self, db_path: str = SQLITE_DB_FILE, legacy_json_path: str = HISTORY_FILE, legacy_audit_path: str = AUDIT_LOG_FILE):
        self.db_path = db_path
        self.legacy_json_path = legacy_json_path
        self.legacy_audit_path = legacy_audit_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()
        self._migrate_legacy_json_if_needed()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 10000;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    query_fingerprint TEXT UNIQUE,
                    first_created_at TEXT,
                    last_reviewed_at TEXT,
                    review_count INTEGER DEFAULT 1,
                    is_archived INTEGER DEFAULT 0,
                    archived_at TEXT,
                    archived_by TEXT,
                    archived_reason TEXT,
                    user_id TEXT,
                    query TEXT,
                    tax_category TEXT,
                    core_issue TEXT,
                    active_keywords TEXT,
                    selected_category TEXT,
                    current_focus TEXT,
                    results_fingerprint TEXT,
                    files_fingerprint TEXT,
                    risk_level TEXT,
                    risk_reason TEXT,
                    briefing_conclusion TEXT,
                    case_comparison TEXT,
                    checklist TEXT,
                    direct_basis_count INTEGER DEFAULT 0,
                    total_results_count INTEGER DEFAULT 0,
                    top_cases TEXT,
                    briefing_full TEXT,
                    knowledge_sources TEXT DEFAULT '[]',
                    knowledge_status TEXT DEFAULT 'candidate',
                    knowledge_reviewed_by TEXT DEFAULT '',
                    knowledge_reviewed_at TEXT DEFAULT '',
                    knowledge_review_note TEXT DEFAULT '',
                    feedback_rating TEXT DEFAULT '',
                    feedback_note TEXT DEFAULT '',
                    feedback_by TEXT DEFAULT '',
                    feedback_at TEXT DEFAULT '',
                    feedback_resolved_at TEXT DEFAULT '',
                    feedback_resolved_by TEXT DEFAULT '',
                    feedback_resolution_note TEXT DEFAULT '',
                    applied_tax_base_date TEXT,
                    model_used TEXT,
                    revisions TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_reviews_fp ON reviews(query_fingerprint);
                CREATE INDEX IF NOT EXISTS idx_reviews_last ON reviews(last_reviewed_at DESC);
                CREATE INDEX IF NOT EXISTS idx_reviews_arch ON reviews(is_archived);
                CREATE INDEX IF NOT EXISTS idx_reviews_tax ON reviews(tax_category);

                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    action TEXT,
                    record_id TEXT,
                    user_id TEXT,
                    details TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_trail(timestamp DESC);
            """)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(reviews)")}
            if "knowledge_sources" not in columns:
                conn.execute("ALTER TABLE reviews ADD COLUMN knowledge_sources TEXT DEFAULT '[]'")
            for column, definition in {
                "knowledge_status": "TEXT DEFAULT 'candidate'",
                "knowledge_reviewed_by": "TEXT DEFAULT ''",
                "knowledge_reviewed_at": "TEXT DEFAULT ''",
                "knowledge_review_note": "TEXT DEFAULT ''",
                "feedback_rating": "TEXT DEFAULT ''",
                "feedback_note": "TEXT DEFAULT ''",
                "feedback_by": "TEXT DEFAULT ''",
                "feedback_at": "TEXT DEFAULT ''",
                "feedback_resolved_at": "TEXT DEFAULT ''",
                "feedback_resolved_by": "TEXT DEFAULT ''",
                "feedback_resolution_note": "TEXT DEFAULT ''",
            }.items():
                if column not in columns:
                    conn.execute(f"ALTER TABLE reviews ADD COLUMN {column} {definition}")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_knowledge_status ON reviews(knowledge_status)")

    def _migrate_legacy_json_if_needed(self):
        """기존 JSON 파일 및 audit_trail.jsonl 이력이 있으면 최초 1회 자동 무손실 이관"""
        try:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM reviews")
                count = cur.fetchone()[0]
                if count > 0:
                    return

                if self.legacy_json_path and os.path.exists(self.legacy_json_path):
                    with open(self.legacy_json_path, "r", encoding="utf-8") as f:
                        j_data = json.load(f)
                    records = j_data.get("records", {})
                    for rec_id, rec in records.items():
                        conn.execute("""
                            INSERT OR REPLACE INTO reviews (
                                id, query_fingerprint, first_created_at, last_reviewed_at,
                                review_count, is_archived, archived_at, archived_by, archived_reason,
                                user_id, query, tax_category, core_issue, active_keywords,
                                selected_category, current_focus, results_fingerprint, files_fingerprint,
                                risk_level, risk_reason, briefing_conclusion, case_comparison,
                                checklist, direct_basis_count, total_results_count, top_cases,
                                briefing_full, applied_tax_base_date, model_used, revisions
                            ) VALUES (
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                            )
                        """, (
                            rec.get("id", rec_id),
                            rec.get("query_fingerprint", ""),
                            rec.get("first_created_at", ""),
                            rec.get("last_reviewed_at", ""),
                            rec.get("review_count", 1),
                            1 if rec.get("is_archived", False) else 0,
                            rec.get("archived_at"),
                            rec.get("archived_by"),
                            rec.get("archived_reason"),
                            rec.get("user_id", "system"),
                            rec.get("query", ""),
                            rec.get("tax_category", "조세일반"),
                            rec.get("core_issue", ""),
                            json.dumps(rec.get("active_keywords", []), ensure_ascii=False),
                            rec.get("selected_category", "전체"),
                            rec.get("current_focus", "종합"),
                            rec.get("results_fingerprint", ""),
                            rec.get("files_fingerprint", ""),
                            rec.get("risk_level", "중립/유의"),
                            rec.get("risk_reason", ""),
                            rec.get("briefing_conclusion", ""),
                            rec.get("case_comparison", ""),
                            json.dumps(rec.get("checklist", []), ensure_ascii=False),
                            rec.get("direct_basis_count", 0),
                            rec.get("total_results_count", 0),
                            json.dumps(rec.get("top_cases", []), ensure_ascii=False),
                            json.dumps(rec.get("briefing_full", {}), ensure_ascii=False),
                            rec.get("applied_tax_base_date", "2026-01-01"),
                            rec.get("model_used", ""),
                            json.dumps(rec.get("revisions", []), ensure_ascii=False)
                        ))

                # 감사 로그 마이그레이션
                if self.legacy_audit_path and os.path.exists(self.legacy_audit_path):
                    cur_audit = conn.execute("SELECT COUNT(*) FROM audit_trail")
                    if cur_audit.fetchone()[0] == 0:
                        with open(self.legacy_audit_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                try:
                                    ev = json.loads(line)
                                    conn.execute(
                                        "INSERT INTO audit_trail (timestamp, action, record_id, user_id, details) VALUES (?, ?, ?, ?, ?)",
                                        (ev.get("timestamp"), ev.get("action"), ev.get("record_id"), ev.get("user_id"), json.dumps(ev.get("details", {}), ensure_ascii=False))
                                    )
                                except Exception:
                                    pass
                conn.commit()
        except Exception:
            pass

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["is_archived"] = bool(d.get("is_archived", 0))
        for json_col in ["active_keywords", "checklist", "top_cases", "briefing_full", "knowledge_sources", "revisions"]:
            val = d.get(json_col)
            if isinstance(val, str):
                try:
                    d[json_col] = json.loads(val)
                except Exception:
                    d[json_col] = [] if json_col != "briefing_full" else {}
            elif val is None:
                d[json_col] = [] if json_col != "briefing_full" else {}
        return d

    def save_review(
        self,
        query: str,
        tax_category: str,
        core_issue: str,
        active_keywords: List[str],
        risk_level: str,
        briefing_conclusion: str,
        checklist: List[str],
        direct_basis_count: int,
        total_results_count: int,
        top_cases: List[Dict[str, Any]],
        applied_tax_base_date: str = "2026-01-01",
        model_used: str = "ChatGPT Enterprise",
        user_id: str = "jongmin.park1@cj.net",
        case_comparison: str = "",
        risk_reason: str = "",
        briefing_full: Optional[Dict[str, Any]] = None,
        selected_category: str = "전체",
        current_focus: str = "종합",
        files_fingerprint: str = "",
        results_fingerprint: str = "",
        knowledge_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, bool]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_query = sanitize_sensitive_text(query or "").strip()
        clean_issue = sanitize_sensitive_text(core_issue or "").strip()
        clean_conclusion = sanitize_sensitive_text(briefing_conclusion or "").strip()
        clean_case_comp = sanitize_sensitive_text(case_comparison or "").strip()
        clean_risk_reason = sanitize_sensitive_text(risk_reason or "").strip()
        clean_knowledge_sources = _normalize_knowledge_sources(knowledge_sources)

        fingerprint = compute_query_fingerprint(clean_query, tax_category)

        if not results_fingerprint and top_cases:
            case_keys = [f"{c.get('case_number','')}:{c.get('title','')}" for c in top_cases[:5]]
            results_fingerprint = hashlib.sha256("_".join(case_keys).encode("utf-8")).hexdigest()[:16]

        try:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM reviews WHERE query_fingerprint = ?", (fingerprint,))
                row = cur.fetchone()

                if row:
                    rec = self._row_to_dict(row)
                    existing_id = rec["id"]
                    new_count = rec["review_count"] + 1
                    revisions = rec.get("revisions", []) or []
                    revisions.append({
                        "review_index": new_count,
                        "reviewed_at": now_str,
                        "active_keywords": active_keywords or rec.get("active_keywords", []),
                        "selected_category": selected_category or "전체",
                        "current_focus": current_focus or "종합 검토",
                        "results_fingerprint": results_fingerprint,
                        "files_fingerprint": files_fingerprint,
                        "total_results_count": total_results_count,
                        "direct_basis_count": direct_basis_count,
                        "risk_level": risk_level or rec.get("risk_level", "중립/유의"),
                        "briefing_conclusion": clean_conclusion[:150],
                        "knowledge_document_ids": [s["document_id"] for s in clean_knowledge_sources],
                    })
                    revisions = revisions[-20:]

                    conn.execute("""
                        UPDATE reviews SET
                            last_reviewed_at = ?,
                            review_count = ?,
                            is_archived = 0,
                            user_id = ?,
                            tax_category = ?,
                            core_issue = ?,
                            active_keywords = ?,
                            selected_category = ?,
                            current_focus = ?,
                            results_fingerprint = ?,
                            files_fingerprint = ?,
                            risk_level = ?,
                            risk_reason = ?,
                            briefing_conclusion = ?,
                            case_comparison = ?,
                            checklist = ?,
                            direct_basis_count = ?,
                            total_results_count = ?,
                            top_cases = ?,
                            briefing_full = ?,
                            knowledge_sources = ?,
                            knowledge_status = 'candidate',
                            knowledge_reviewed_by = '',
                            knowledge_reviewed_at = '',
                            knowledge_review_note = '',
                            feedback_rating = '',
                            feedback_note = '',
                            feedback_by = '',
                            feedback_at = '',
                            feedback_resolved_at = '',
                            feedback_resolved_by = '',
                            feedback_resolution_note = '',
                            revisions = ?
                        WHERE id = ?
                    """, (
                        now_str,
                        new_count,
                        user_id,
                        tax_category or rec.get("tax_category", "조세일반"),
                        clean_issue or rec.get("core_issue", ""),
                        json.dumps(active_keywords or rec.get("active_keywords", []), ensure_ascii=False),
                        selected_category or "전체",
                        current_focus or "종합 검토",
                        results_fingerprint or rec.get("results_fingerprint", ""),
                        files_fingerprint or rec.get("files_fingerprint", ""),
                        risk_level or rec.get("risk_level", "중립/유의"),
                        clean_risk_reason or rec.get("risk_reason", ""),
                        clean_conclusion or rec.get("briefing_conclusion", ""),
                        clean_case_comp or rec.get("case_comparison", ""),
                        json.dumps(checklist[:5] if checklist else rec.get("checklist", []), ensure_ascii=False),
                        direct_basis_count,
                        total_results_count,
                        json.dumps(top_cases[:5] if top_cases else rec.get("top_cases", []), ensure_ascii=False),
                        json.dumps(briefing_full if briefing_full else rec.get("briefing_full", {}), ensure_ascii=False),
                        json.dumps(clean_knowledge_sources or rec.get("knowledge_sources", []), ensure_ascii=False),
                        json.dumps(revisions, ensure_ascii=False),
                        existing_id
                    ))

                    conn.execute("""
                        INSERT INTO audit_trail (timestamp, action, record_id, user_id, details)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        now_str,
                        "UPDATE_REVIEW",
                        existing_id,
                        user_id,
                        json.dumps({
                            "fingerprint": fingerprint,
                            "review_count": new_count,
                            "active_keywords": active_keywords or rec.get("active_keywords", []),
                            "query_snippet": clean_query[:50],
                            "knowledge_source_count": len(clean_knowledge_sources),
                        }, ensure_ascii=False)
                    ))
                    conn.commit()
                    return existing_id, False
                else:
                    new_id = f"rev_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{fingerprint[:6]}"
                    first_rev = [{
                        "review_index": 1,
                        "reviewed_at": now_str,
                        "active_keywords": active_keywords or [],
                        "selected_category": selected_category or "전체",
                        "current_focus": current_focus or "종합 검토",
                        "results_fingerprint": results_fingerprint or "",
                        "files_fingerprint": files_fingerprint or "no_files",
                        "total_results_count": total_results_count,
                        "direct_basis_count": direct_basis_count,
                        "risk_level": risk_level or "중립/유의",
                        "briefing_conclusion": clean_conclusion[:150],
                        "knowledge_document_ids": [s["document_id"] for s in clean_knowledge_sources],
                    }]
                    conn.execute("""
                        INSERT INTO reviews (
                            id, query_fingerprint, first_created_at, last_reviewed_at, review_count,
                            is_archived, user_id, query, tax_category, core_issue,
                            active_keywords, selected_category, current_focus, results_fingerprint, files_fingerprint,
                            risk_level, risk_reason, briefing_conclusion, case_comparison, checklist,
                            direct_basis_count, total_results_count, top_cases, briefing_full, knowledge_sources,
                            knowledge_status, knowledge_reviewed_by, knowledge_reviewed_at, knowledge_review_note,
                            feedback_rating, feedback_note, feedback_by, feedback_at,
                            applied_tax_base_date, model_used, revisions
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                    """, (
                        new_id,
                        fingerprint,
                        now_str,
                        now_str,
                        1,
                        0,
                        user_id,
                        clean_query,
                        tax_category or "조세일반",
                        clean_issue,
                        json.dumps(active_keywords or [], ensure_ascii=False),
                        selected_category or "전체",
                        current_focus or "종합 검토",
                        results_fingerprint or "",
                        files_fingerprint or "no_files",
                        risk_level or "중립/유의",
                        clean_risk_reason,
                        clean_conclusion,
                        clean_case_comp,
                        json.dumps(checklist[:5] if checklist else [], ensure_ascii=False),
                        direct_basis_count,
                        total_results_count,
                        json.dumps(top_cases[:5] if top_cases else [], ensure_ascii=False),
                        json.dumps(briefing_full or {}, ensure_ascii=False),
                        json.dumps(clean_knowledge_sources, ensure_ascii=False),
                        "candidate",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        applied_tax_base_date or config.get_tax_base_date(),
                        model_used or config.get_ai_service_name(),
                        json.dumps(first_rev, ensure_ascii=False)
                    ))
                    conn.execute("""
                        INSERT INTO audit_trail (timestamp, action, record_id, user_id, details)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        now_str,
                        "CREATE_REVIEW",
                        new_id,
                        user_id,
                        json.dumps({
                            "fingerprint": fingerprint,
                            "tax_category": tax_category,
                            "query_snippet": clean_query[:50],
                            "knowledge_source_count": len(clean_knowledge_sources),
                        }, ensure_ascii=False)
                    ))
                    conn.commit()
                    return new_id, True
        except Exception:
            return "", False

    def get_all(self, include_archived: bool = False, search_query: str = "", tax_category: str = "전체") -> List[Dict[str, Any]]:
        query_sql = "SELECT * FROM reviews WHERE 1=1"
        params = []

        if not include_archived:
            query_sql += " AND is_archived = 0"

        if tax_category and tax_category != "전체":
            query_sql += " AND tax_category = ?"
            params.append(tax_category)

        query_sql += " ORDER BY last_reviewed_at DESC"

        try:
            with self._get_connection() as conn:
                cur = conn.execute(query_sql, params)
                rows = cur.fetchall()
                records = [self._row_to_dict(r) for r in rows]
        except Exception:
            records = []

        return _filter_and_rank_records(records, search_query)

    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT * FROM reviews WHERE id = ?", (record_id,))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
        except Exception:
            return None

    def set_knowledge_status(self, record_id: str, status: str, reviewer: str, note: str = "") -> bool:
        status = _validate_knowledge_status(status, note)
        reviewer = (reviewer or "").strip()
        if not reviewer:
            raise ValueError("검토자 이름 또는 계정이 필요합니다.")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_note = sanitize_sensitive_text(note or "")
        try:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT knowledge_status FROM reviews WHERE id = ?", (record_id,)
                ).fetchone()
                if not row:
                    return False
                previous = row[0] or "candidate"
                conn.execute(
                    """UPDATE reviews SET knowledge_status = ?, knowledge_reviewed_by = ?,
                       knowledge_reviewed_at = ?, knowledge_review_note = ? WHERE id = ?""",
                    (status, reviewer, now_str, clean_note, record_id),
                )
                conn.execute(
                    "INSERT INTO audit_trail (timestamp, action, record_id, user_id, details) VALUES (?, ?, ?, ?, ?)",
                    (now_str, "KNOWLEDGE_STATUS_CHANGED", record_id, reviewer, json.dumps({
                        "from": previous, "to": status, "note": clean_note[:300]
                    }, ensure_ascii=False)),
                )
                return True
        except sqlite3.Error:
            return False

    def get_approved_records(self, search_query: str = "") -> List[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM reviews WHERE is_archived = 0 AND knowledge_status = 'approved' ORDER BY knowledge_reviewed_at DESC"
                ).fetchall()
                records = [self._row_to_dict(row) for row in rows]
        except sqlite3.Error:
            records = []
        return _filter_and_rank_records(records, search_query)

    def set_feedback(self, record_id: str, rating: str, user_id: str, note: str = "") -> bool:
        rating = (rating or "").strip().lower()
        if rating not in FEEDBACK_RATINGS:
            raise ValueError("지원하지 않는 피드백 값입니다.")
        if rating == "needs_correction" and not (note or "").strip():
            raise ValueError("수정 필요 평가에는 구체적인 사유가 필요합니다.")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_note = sanitize_sensitive_text(note or "")
        user_id = (user_id or "anonymous").strip()
        try:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """UPDATE reviews SET feedback_rating = ?, feedback_note = ?,
                       feedback_by = ?, feedback_at = ?, feedback_resolved_at = '',
                       feedback_resolved_by = '', feedback_resolution_note = '' WHERE id = ?""",
                    (rating, clean_note, user_id, now_str, record_id),
                )
                if cur.rowcount == 0:
                    return False
                conn.execute(
                    "INSERT INTO audit_trail (timestamp, action, record_id, user_id, details) VALUES (?, ?, ?, ?, ?)",
                    (now_str, "REVIEW_FEEDBACK", record_id, user_id, json.dumps({
                        "rating": rating, "note": clean_note[:300]
                    }, ensure_ascii=False)),
                )
                return True
        except sqlite3.Error:
            return False

    def resolve_feedback(self, record_id: str, assignee: str, note: str) -> bool:
        assignee = (assignee or "").strip()
        if not assignee:
            raise ValueError("담당자가 필요합니다.")
        if not (note or "").strip():
            raise ValueError("처리 완료 근거를 입력해 주세요.")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clean_note = sanitize_sensitive_text(note)
        try:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """UPDATE reviews SET feedback_resolved_at = ?, feedback_resolved_by = ?,
                       feedback_resolution_note = ?
                       WHERE id = ? AND feedback_rating = 'needs_correction'""",
                    (now_str, assignee, clean_note, record_id),
                )
                if cur.rowcount == 0:
                    return False
                conn.execute(
                    "INSERT INTO audit_trail (timestamp, action, record_id, user_id, details) VALUES (?, ?, ?, ?, ?)",
                    (now_str, "FEEDBACK_RESOLVED", record_id, assignee,
                     json.dumps({"note": clean_note[:300]}, ensure_ascii=False)),
                )
                return True
        except sqlite3.Error:
            return False

    def archive_record(self, record_id: str, user_id: str = "jongmin.park1@cj.net", reason: str = "") -> bool:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "UPDATE reviews SET is_archived = 1, archived_at = ?, archived_by = ?, archived_reason = ? WHERE id = ?",
                    (now_str, user_id, reason or "사용자 보관 요청", record_id)
                )
                if cur.rowcount > 0:
                    conn.execute(
                        "INSERT INTO audit_trail (timestamp, action, record_id, user_id, details) VALUES (?, ?, ?, ?, ?)",
                        (now_str, "ARCHIVE_REVIEW", record_id, user_id, json.dumps({"reason": reason}, ensure_ascii=False))
                    )
                    conn.commit()
                    return True
                return False
        except Exception:
            return False

    def restore_record(self, record_id: str, user_id: str = "jongmin.park1@cj.net") -> bool:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "UPDATE reviews SET is_archived = 0, archived_at = NULL WHERE id = ?",
                    (record_id,)
                )
                if cur.rowcount > 0:
                    conn.execute(
                        "INSERT INTO audit_trail (timestamp, action, record_id, user_id, details) VALUES (?, ?, ?, ?, ?)",
                        (now_str, "RESTORE_REVIEW", record_id, user_id, json.dumps({}, ensure_ascii=False))
                    )
                    conn.commit()
                    return True
                return False
        except Exception:
            return False

    def get_kpi_stats(self) -> Dict[str, Any]:
        try:
            with self._get_connection() as conn:
                cur = conn.execute("""
                    SELECT 
                        COUNT(*), 
                        COALESCE(SUM(review_count), 0), 
                        COALESCE(MAX(last_reviewed_at), '-')
                    FROM reviews 
                    WHERE is_archived = 0
                """)
                active_cnt, total_runs, recent_dt = cur.fetchone()

                cur_arch = conn.execute("SELECT COUNT(*) FROM reviews WHERE is_archived = 1")
                arch_cnt = cur_arch.fetchone()[0]

                cur_status = conn.execute("""
                    SELECT COALESCE(knowledge_status, 'candidate'), COUNT(*)
                    FROM reviews WHERE is_archived = 0 GROUP BY COALESCE(knowledge_status, 'candidate')
                """)
                status_counts = {status: 0 for status in KNOWLEDGE_STATUSES}
                status_counts.update({row[0]: row[1] for row in cur_status.fetchall()})

                cur_feedback = conn.execute("""
                    SELECT feedback_rating, COUNT(*) FROM reviews
                    WHERE is_archived = 0 AND feedback_rating != '' GROUP BY feedback_rating
                """)
                feedback_counts = {rating: 0 for rating in FEEDBACK_RATINGS}
                feedback_counts.update({row[0]: row[1] for row in cur_feedback.fetchall()})

                knowledge_source_uses = 0
                for row in conn.execute("SELECT knowledge_sources FROM reviews WHERE is_archived = 0"):
                    try:
                        knowledge_source_uses += len(json.loads(row[0] or "[]"))
                    except (TypeError, json.JSONDecodeError):
                        pass

                cur_tax = conn.execute("""
                    SELECT tax_category, COUNT(*) 
                    FROM reviews 
                    WHERE is_archived = 0 
                    GROUP BY tax_category
                """)
                tax_dist = {row[0]: row[1] for row in cur_tax.fetchall()}

                return {
                    "total_active_cases": active_cnt,
                    "total_reviews_run": total_runs,
                    "archived_count": arch_cnt,
                    "recent_reviewed_at": recent_dt,
                    "tax_distribution": tax_dist,
                    "knowledge_status_counts": status_counts,
                    "feedback_counts": feedback_counts,
                    "knowledge_source_uses": knowledge_source_uses,
                }
        except Exception:
            return {
                "total_active_cases": 0,
                "total_reviews_run": 0,
                "archived_count": 0,
                "recent_reviewed_at": "-",
                "tax_distribution": {},
                "knowledge_status_counts": {status: 0 for status in KNOWLEDGE_STATUSES},
                "feedback_counts": {rating: 0 for rating in FEEDBACK_RATINGS},
                "knowledge_source_uses": 0,
            }


# ==============================================================================
# 저장소 백엔드 Factory / Singleton (DIP 준수)
# ==============================================================================
_repo_instance: Optional[BaseReviewRepository] = None

def get_review_repository(backend: Optional[str] = None) -> BaseReviewRepository:
    """
    ReviewRepository 팩토리 함수 (DIP 준수).
    환경 변수/설정(REVIEW_STORAGE_BACKEND)에 따라 'sqlite' 또는 'json' 리포지토리 인스턴스 반환.
    - 기본값: 'sqlite' (멀티프로세스 동시성 WAL, ACID 트랜잭션 보장, 무손실 자동 마이그레이션)
    - 레거시: 'json' (기존 단일 프로세스 파일 저장소)
    """
    global _repo_instance
    if backend is not None:
        if backend.lower() == "sqlite":
            return SqliteReviewRepository()
        else:
            return JsonReviewRepository()

    if _repo_instance is None:
        selected = config.get_review_storage_backend()
        if selected == "json":
            _repo_instance = JsonReviewRepository()
        else:
            _repo_instance = SqliteReviewRepository()
    return _repo_instance
