"""Unified retrieval across approved review history and Obsidian TAX knowledge."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import config
from repositories.review_repo import get_review_repository
from repositories.tax_knowledge_repo import get_tax_knowledge_repository


class KnowledgeSearchService:
    def __init__(self, tax_repo=None, review_repo=None):
        self.tax_repo = tax_repo or get_tax_knowledge_repository()
        self.review_repo = review_repo or get_review_repository()

    def get_version(self) -> str:
        try:
            approved = self.review_repo.get_approved_records()
            max_rev_at = max([r.get("knowledge_reviewed_at", "") for r in approved], default="")
            review_version = f"{len(approved)}:{max_rev_at}"
        except Exception:
            review_version = "v1"
        return f"{self.tax_repo.get_database_version()}|{review_version}"

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        approved = self.review_repo.get_approved_records(query)[:3]
        approved_hits = [self._approved_hit(record) for record in approved]
        remaining = max(0, limit - len(approved_hits))
        obsidian_hits = self.tax_repo.search(query, limit=remaining) if remaining else []
        for hit in obsidian_hits:
            hit["knowledge_type"] = "obsidian"
        return (approved_hits + obsidian_hits)[:limit]

    @staticmethod
    def _approved_hit(record: dict[str, Any]) -> dict[str, Any]:
        record_id = str(record.get("id", ""))
        body = "\n\n".join(part for part in [
            f"핵심 쟁점: {record.get('core_issue', '')}",
            f"승인 결론: {record.get('briefing_conclusion', '')}",
            f"판례 비교: {record.get('case_comparison', '')}",
            "필수 증빙: " + ", ".join(record.get("checklist", []) or []),
        ] if part.split(":", 1)[-1].strip())
        fingerprint_source = json.dumps({
            "id": record_id,
            "conclusion": record.get("briefing_conclusion", ""),
            "reviewed_at": record.get("knowledge_reviewed_at", ""),
        }, ensure_ascii=False, sort_keys=True)
        return {
            "document_id": record_id,
            "title": str(record.get("query", ""))[:120] or record.get("core_issue", "승인 검토"),
            "source_path": f"review_history.db#{record_id}",
            "matched_fields": ["approved_review"],
            "source_mtime": record.get("knowledge_reviewed_at", ""),
            "content_sha256": hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest(),
            "excerpt": body[:1200],
            "score": record.get("_search_score", 0),
            "knowledge_type": "approved_review",
            "reviewed_by": record.get("knowledge_reviewed_by", ""),
            "reviewed_at": record.get("knowledge_reviewed_at", ""),
        }


def get_knowledge_search_service() -> KnowledgeSearchService:
    return KnowledgeSearchService()
