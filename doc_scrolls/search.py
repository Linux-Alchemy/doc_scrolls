from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .models import SearchResult


FTS_RESERVED_TERMS = {"and", "or", "not", "near"}


def _normalize_query(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]+", query)
    safe_terms = [token for token in tokens if token.lower() not in FTS_RESERVED_TERMS]
    return " ".join(f'"{term}"' for term in safe_terms)


def query_db_with_note(db_path: Path, query: str, limit: int = 50) -> tuple[list[SearchResult], str | None]:
    if not query.strip():
        return recent_pages(db_path, limit=limit), None

    normalized = _normalize_query(query)
    if not normalized:
        return [], "Search syntax error: no searchable terms found in query."

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT p.id, p.title, p.url, p.markdown, p.plain_text,
                       bm25(pages_fts, 2.0, 1.0) AS score
                FROM pages_fts
                JOIN pages p ON p.id = pages_fts.rowid
                WHERE pages_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (normalized, limit),
            ).fetchall()
    except sqlite3.OperationalError as exc:
        lowered = str(exc).lower()
        if "syntax error" in lowered or "unterminated string" in lowered or "malformed match" in lowered:
            return [], f"Search syntax error: {exc}"
        raise

    results: list[SearchResult] = []
    for row in rows:
        snippet = row["plain_text"][:220]
        results.append(
            SearchResult(
                page_id=row["id"],
                title=row["title"],
                url=row["url"],
                snippet=snippet,
                markdown=row["markdown"],
                score=float(row["score"]),
            )
        )
    return results, None


def query_db(db_path: Path, query: str, limit: int = 50) -> list[SearchResult]:
    rows, _ = query_db_with_note(db_path, query=query, limit=limit)
    return rows


def recent_pages(db_path: Path, limit: int = 50) -> list[SearchResult]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, title, url, markdown, plain_text
            FROM pages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        SearchResult(
            page_id=row["id"],
            title=row["title"],
            url=row["url"],
            snippet=row["plain_text"][:220],
            markdown=row["markdown"],
            score=0.0,
        )
        for row in rows
    ]
