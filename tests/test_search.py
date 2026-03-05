from pathlib import Path

from doc_scrolls.indexer import index_pages, init_db, parse_html_page, reset_index
from doc_scrolls.models import ParsedPage
from doc_scrolls.search import query_db, query_db_with_note


def test_query_db_returns_matches(tmp_path: Path) -> None:
    db_path = tmp_path / "index.db"
    init_db(db_path)
    reset_index(db_path)

    pages = [
        ParsedPage(
            title="asyncio tasks",
            url="https://docs.python.org/3/library/asyncio-task.html",
            markdown="# asyncio tasks",
            plain_text="create_task gather TaskGroup await",
        ),
        ParsedPage(
            title="pathlib",
            url="https://docs.python.org/3/library/pathlib.html",
            markdown="# pathlib",
            plain_text="path operations filesystem glob",
        ),
    ]
    index_pages(db_path, pages)

    results = query_db(db_path, "gather", limit=5)

    assert results
    assert results[0].title == "asyncio tasks"


def test_query_db_with_note_handles_invalid_syntax_gracefully(tmp_path: Path) -> None:
    db_path = tmp_path / "index.db"
    init_db(db_path)
    reset_index(db_path)

    pages = [
        ParsedPage(
            title="asyncio tasks",
            url="https://docs.python.org/3/library/asyncio-task.html",
            markdown="# asyncio tasks",
            plain_text="create_task gather TaskGroup await",
        )
    ]
    index_pages(db_path, pages)

    results, note = query_db_with_note(db_path, "(", limit=5)

    assert results == []
    assert note is not None
    assert "syntax error" in note.lower()


def test_query_db_with_note_sanitizes_operator_noise(tmp_path: Path) -> None:
    db_path = tmp_path / "index.db"
    init_db(db_path)
    reset_index(db_path)

    pages = [
        ParsedPage(
            title="asyncio tasks",
            url="https://docs.python.org/3/library/asyncio-task.html",
            markdown="# asyncio tasks",
            plain_text="create_task gather TaskGroup await",
        )
    ]
    index_pages(db_path, pages)

    results, note = query_db_with_note(db_path, "gather OR (", limit=5)

    assert note is None
    assert results


def test_parse_html_page_extracts_content(tmp_path: Path) -> None:
    html = tmp_path / "sample.html"
    html.write_text(
        """
        <html><head><title>Sample Title</title></head>
        <body><h1>Header</h1><p>Hello world</p><pre>print('x')</pre></body></html>
        """,
        encoding="utf-8",
    )

    parsed = parse_html_page(html, base_url="https://docs.python.org/3", rel_path=Path("sample.html"))

    assert parsed is not None
    assert parsed.title == "Sample Title"
    assert "Hello world" in parsed.plain_text
    assert "print('x')" in parsed.markdown
