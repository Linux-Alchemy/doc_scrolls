from __future__ import annotations

import shutil
from collections.abc import Callable

from .adapters.python_adapter import PythonDocsAdapter
from .indexer import collect_html_pages, index_pages, init_db, parse_html_page, reset_index
from .models import InstalledDocset, SearchResult
from .search import query_db_with_note
from .storage import docset_db_path, docset_root, ensure_dirs, load_installed, upsert_installed


def _version_sort_key(version: str) -> tuple[int, tuple[int, ...], str]:
    parts = version.split(".")
    if parts and all(part.isdigit() for part in parts):
        return (1, tuple(int(part) for part in parts), "")
    return (0, tuple(), version)


def _report(progress: Callable[[str], None] | None, message: str) -> None:
    if progress:
        progress(message)


def install_python_docs(
    version: str | None = None, progress: Callable[[str], None] | None = None
) -> InstalledDocset:
    ensure_dirs()
    adapter = PythonDocsAdapter()
    resolved_version = (version or "3").strip()
    _report(progress, f"Preparing install for python@{resolved_version}...")

    final_root = docset_root("python", resolved_version)
    staging_root = final_root.parent / f"{final_root.name}.tmp"

    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)

    try:
        raw_root = staging_root / "raw"
        payload = adapter.install(raw_root, version=resolved_version, progress=progress)

        db_path = staging_root / "index.db"
        _report(progress, "Initializing local search index...")
        init_db(db_path)
        reset_index(db_path)

        parsed_pages = []
        html_pages = collect_html_pages(payload.extracted_root)
        total_pages = len(html_pages)
        _report(progress, f"Indexing {total_pages} HTML pages...")
        base_url = f"https://docs.python.org/{payload.version}"
        for idx, html_path in enumerate(html_pages, start=1):
            rel_path = html_path.relative_to(payload.extracted_root)
            parsed = parse_html_page(html_path, base_url=base_url, rel_path=rel_path)
            if parsed:
                parsed_pages.append(parsed)
            if idx % 150 == 0:
                _report(progress, f"Indexed {idx}/{total_pages} pages...")

        page_count = index_pages(db_path, parsed_pages)
        _report(progress, f"Indexed {page_count} pages into SQLite.")

        if final_root.exists():
            shutil.rmtree(final_root)
        shutil.move(str(staging_root), str(final_root))
        _report(progress, "Finalizing installation metadata...")

        installed = InstalledDocset(
            source="python",
            version=payload.version,
            root_path=final_root,
            db_path=docset_db_path("python", payload.version),
            page_count=page_count,
        )
        upsert_installed(installed)
        _report(progress, "Install complete.")
        return installed
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise


def list_installed() -> list[InstalledDocset]:
    return load_installed()


def get_installed(source: str, version: str | None = None) -> InstalledDocset:
    items = [x for x in load_installed() if x.source == source]
    if not items:
        raise RuntimeError(f"No installed docsets found for source '{source}'. Run install first.")

    if version:
        for item in items:
            if item.version == version:
                return item
        raise RuntimeError(f"Source '{source}' version '{version}' is not installed")

    return sorted(items, key=lambda x: _version_sort_key(x.version))[-1]


def search(source: str, query: str, version: str | None = None, limit: int = 50) -> list[SearchResult]:
    rows, _ = search_with_note(source=source, query=query, version=version, limit=limit)
    return rows


def search_with_note(
    source: str, query: str, version: str | None = None, limit: int = 50
) -> tuple[list[SearchResult], str | None]:
    installed = get_installed(source=source, version=version)
    return query_db_with_note(installed.db_path, query=query, limit=limit)
