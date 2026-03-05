from __future__ import annotations

import sqlite3
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown

from .models import ParsedPage


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                markdown TEXT NOT NULL,
                plain_text TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts
            USING fts5(title, plain_text, content='pages', content_rowid='id')
            """
        )
        conn.commit()


def reset_index(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM pages")
        conn.execute("DELETE FROM pages_fts")
        conn.commit()


def parse_html_page(path: Path, base_url: str, rel_path: Path) -> ParsedPage | None:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    body = soup.body
    if body is None:
        return None

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else path.stem

    markdown = to_markdown(str(body), heading_style="ATX")
    plain_text = body.get_text(" ", strip=True)
    rel = rel_path.as_posix()
    url = f"{base_url.rstrip('/')}/{rel}"

    return ParsedPage(title=title, url=url, markdown=markdown.strip(), plain_text=plain_text)


def index_pages(db_path: Path, pages: list[ParsedPage]) -> int:
    with sqlite3.connect(db_path) as conn:
        for page in pages:
            cur = conn.execute(
                "INSERT INTO pages(title, url, markdown, plain_text) VALUES(?, ?, ?, ?)",
                (page.title, page.url, page.markdown, page.plain_text),
            )
            rowid = cur.lastrowid
            conn.execute(
                "INSERT INTO pages_fts(rowid, title, plain_text) VALUES(?, ?, ?)",
                (rowid, page.title, page.plain_text),
            )
        conn.commit()
    return len(pages)


def collect_html_pages(root: Path) -> list[Path]:
    return sorted([p for p in root.rglob("*.html") if p.is_file()])
