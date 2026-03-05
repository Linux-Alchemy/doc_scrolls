from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import SearchResult


def query_db(db_path: Path, query: str, limit: int = 50) -> list[SearchResult]:
    if not query.strip():
        return recent_pages(db_path, limit=limit)

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
            (query, limit),
        ).fetchall()

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
    return results


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
