"""Import tax-related Obsidian notes into a local SQLite knowledge database."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


TAX_VALUES = {"tax", "tax_review"}
PROTECTED_PARTS = {".obsidian", ".trash", "archive", "90_archive", "templates"}


def clean_scalar(value: str):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    low = value.casefold()
    if low in {"true", "false"}:
        return low == "true"
    if low in {"null", "~"} or not value:
        return None
    return value


def parse_frontmatter(text: str) -> tuple[dict, str]:
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text

    props: dict[str, object] = {}
    current_key: str | None = None
    for raw in lines[1:end]:
        key_match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", raw)
        if key_match:
            current_key, value = key_match.groups()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                props[current_key] = [
                    clean_scalar(item) for item in value[1:-1].split(",") if item.strip()
                ]
            else:
                props[current_key] = clean_scalar(value)
            continue
        list_match = re.match(r"^\s+-\s+(.*)$", raw)
        if list_match and current_key:
            existing = props.get(current_key)
            if not isinstance(existing, list):
                existing = [] if existing is None else [existing]
            existing.append(clean_scalar(list_match.group(1)))
            props[current_key] = existing
    return props, "\n".join(lines[end + 1 :]).strip()


def flattened_values(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().casefold() for item in value if item is not None]
    return [] if value is None else [str(value).strip().casefold()]


def matched_tax_fields(props: dict) -> list[str]:
    return sorted(
        key for key, value in props.items() if TAX_VALUES.intersection(flattened_values(value))
    )


def is_protected(path: Path, vault: Path, props: dict) -> bool:
    relative = path.relative_to(vault)
    parts = {part.casefold() for part in relative.parts[:-1]}
    if parts.intersection(PROTECTED_PARTS) or path.name.casefold() == "pw.md":
        return True
    for key in ("manual_review", "cleanup_candidate"):
        if props.get(key) is True or str(props.get(key, "")).casefold() == "true":
            return True
    status = {value for value in flattened_values(props.get("status"))}
    return "unresolved" in status


def chunks(text: str, max_chars: int = 1800) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    result: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            result.append(current)
            current = ""
        if len(paragraph) <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                result.append(current)
                current = ""
            result.extend(paragraph[i : i + max_chars] for i in range(0, len(paragraph), max_chars))
    if current:
        result.append(current)
    return result


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS tax_chunks_fts;
        DROP TABLE IF EXISTS tax_chunks;
        DROP TABLE IF EXISTS tax_properties;
        DROP TABLE IF EXISTS tax_documents;
        CREATE TABLE tax_documents (
            id INTEGER PRIMARY KEY,
            source_path TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            properties_json TEXT NOT NULL,
            matched_fields_json TEXT NOT NULL,
            source_mtime TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            imported_at TEXT NOT NULL
        );
        CREATE TABLE tax_properties (
            document_id INTEGER NOT NULL REFERENCES tax_documents(id) ON DELETE CASCADE,
            property_name TEXT NOT NULL,
            property_value_json TEXT,
            PRIMARY KEY (document_id, property_name)
        );
        CREATE TABLE tax_chunks (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES tax_documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            UNIQUE (document_id, chunk_index)
        );
        CREATE VIRTUAL TABLE tax_chunks_fts USING fts5(
            title, content, source_path, content=''
        );
        CREATE INDEX idx_tax_properties_name ON tax_properties(property_name);
        CREATE INDEX idx_tax_chunks_document ON tax_chunks(document_id);
        """
    )


def import_vault(vault: Path, database: Path) -> dict:
    stats = {"markdown": 0, "tax_documents": 0, "chunks": 0, "protected": 0, "read_errors": 0}
    imported_at = datetime.now(timezone.utc).isoformat()
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        create_schema(conn)
        for path in vault.rglob("*.md"):
            stats["markdown"] += 1
            try:
                text = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError):
                stats["read_errors"] += 1
                continue
            props, body = parse_frontmatter(text)
            fields = matched_tax_fields(props)
            if not fields:
                continue
            if is_protected(path, vault, props):
                stats["protected"] += 1
                continue
            relative = path.relative_to(vault).as_posix()
            cursor = conn.execute(
                """INSERT INTO tax_documents
                (source_path, title, content, properties_json, matched_fields_json,
                 source_mtime, content_sha256, imported_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    relative,
                    path.stem,
                    body,
                    json.dumps(props, ensure_ascii=False, sort_keys=True),
                    json.dumps(fields, ensure_ascii=False),
                    datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                    hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    imported_at,
                ),
            )
            document_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO tax_properties VALUES (?, ?, ?)",
                [
                    (document_id, key, json.dumps(value, ensure_ascii=False))
                    for key, value in props.items()
                ],
            )
            for index, chunk in enumerate(chunks(body)):
                chunk_id = conn.execute(
                    "INSERT INTO tax_chunks (document_id, chunk_index, content) VALUES (?, ?, ?)",
                    (document_id, index, chunk),
                ).lastrowid
                conn.execute(
                    "INSERT INTO tax_chunks_fts(rowid, title, content, source_path) VALUES (?, ?, ?, ?)",
                    (chunk_id, path.stem, chunk, relative),
                )
                stats["chunks"] += 1
            stats["tax_documents"] += 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vault", type=Path)
    parser.add_argument("--database", type=Path, default=Path("obsidian_tax_knowledge.db"))
    args = parser.parse_args()
    if not args.vault.is_dir():
        parser.error(f"Vault not found: {args.vault}")
    stats = import_vault(args.vault.resolve(), args.database.resolve())
    print(json.dumps({"database": str(args.database.resolve()), **stats}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
