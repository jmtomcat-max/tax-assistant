"""Read-only search access to the Obsidian TAX knowledge database."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Any

import config


_GENERIC_QUERY_WORDS = {"경우", "여부", "관련", "대한", "검토", "문제", "처리", "질문", "알려줘", "어떻게"}


def _search_tokens(query: str) -> list[str]:
    tokens: list[str] = []
    for token in re.findall(r"[가-힣A-Za-z0-9_]{2,}", query or ""):
        token = token.casefold()
        if token in config.STOP_KEYWORDS or token in _GENERIC_QUERY_WORDS:
            continue
        normalized = token
        for suffix in ("에서", "에게", "으로", "까지", "부터", "이나", "거나", "은", "는", "이", "가", "을", "를", "에", "의", "와", "과", "도", "만", "로"):
            if token.endswith(suffix) and len(token) - len(suffix) >= 2:
                normalized = token[: -len(suffix)]
                break
        if normalized not in tokens:
            tokens.append(normalized)
    return tokens[:12]


def _is_relevant(tokens: list[str], title: str, excerpt: str) -> bool:
    corpus = f"{title} {excerpt}".casefold()
    corpus_nospace = re.sub(r"\s+", "", corpus)
    matched = {token for token in tokens if token in corpus or re.sub(r"\s+", "", token) in corpus_nospace}
    return _has_sufficient_relevance(tokens, matched)


def _is_index_document(content: str) -> bool:
    """실제 검토내용 없이 다른 노트 링크만 모아둔 Obsidian 허브를 제외."""
    links = re.findall(r"\[\[[^\]]+\]\]", content or "")
    if len(links) < 3:
        return False
    substantive = re.sub(r"\[\[[^\]]+\]\]", "", content or "")
    substantive = re.sub(r"[#>*_\-|\s]", "", substantive)
    return len(substantive) < 500


def _has_sufficient_relevance(tokens: list[str], matched: set[str]) -> bool:
    if not tokens:
        return False
    required = len(tokens) if len(tokens) <= 3 else max(3, math.ceil(len(tokens) * 0.6))
    ascii_anchors = [token for token in tokens if re.search(r"[a-z0-9]", token)]
    anchors = ascii_anchors or sorted(tokens, key=len, reverse=True)[:2]
    return len(matched) >= required and any(anchor in matched for anchor in anchors)


class TaxKnowledgeRepository:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or config.get_tax_knowledge_db_path())

    def get_database_version(self) -> str:
        if not self.db_path.is_file():
            return "missing"
        stat = self.db_path.stat()
        return f"{stat.st_mtime_ns}:{stat.st_size}"

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        tokens = _search_tokens(query)
        if not tokens or not self.db_path.is_file():
            return []
        fts_query = " OR ".join(f'"{token}"' for token in tokens)
        with sqlite3.connect(f"file:{self.db_path.resolve().as_posix()}?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT d.id AS document_id, d.title, d.source_path,
                       d.matched_fields_json, d.source_mtime, d.content_sha256,
                       ch.content AS excerpt,
                       bm25(tax_chunks_fts, 5.0, 1.0, 0.1) AS rank
                FROM tax_chunks_fts
                JOIN tax_chunks ch ON ch.id = tax_chunks_fts.rowid
                JOIN tax_documents d ON d.id = ch.document_id
                WHERE tax_chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, max(limit * 4, limit)),
            ).fetchall()

        results: list[dict[str, Any]] = []
        seen: set[int] = set()
        for row in rows:
            if _is_index_document(row["excerpt"] or ""):
                continue
            if not _is_relevant(tokens, row["title"] or "", row["excerpt"] or ""):
                continue
            document_id = int(row["document_id"])
            if document_id in seen:
                continue
            seen.add(document_id)
            results.append(
                {
                    "document_id": document_id,
                    "title": row["title"],
                    "source_path": row["source_path"],
                    "matched_fields": json.loads(row["matched_fields_json"] or "[]"),
                    "source_mtime": row["source_mtime"],
                    "content_sha256": row["content_sha256"],
                    "excerpt": (row["excerpt"] or "")[:700],
                    "score": round(-float(row["rank"] or 0), 6),
                }
            )
            if len(results) >= limit:
                break
        return results


def get_tax_knowledge_repository() -> TaxKnowledgeRepository:
    return TaxKnowledgeRepository()
