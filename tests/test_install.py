from pathlib import Path

import doc_scrolls.service as service
from doc_scrolls.adapters.python_adapter import InstallPayload


def test_install_python_docs_indexes_pages(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True)

    monkeypatch.setattr(service, "docset_root", lambda source, version: tmp_path / "docsets" / source / version)
    monkeypatch.setattr(service, "docset_db_path", lambda source, version: tmp_path / "docsets" / source / version / "index.db")
    monkeypatch.setattr(service, "ensure_dirs", lambda: None)

    installed_rows = []
    monkeypatch.setattr(service, "upsert_installed", lambda item: installed_rows.append(item))

    def fake_install(self, destination: Path, version: str | None = None, progress=None):
        destination.mkdir(parents=True, exist_ok=True)
        page = destination / "index.html"
        page.write_text(
            "<html><head><title>Python</title></head><body><h1>Python Docs</h1><p>asyncio gather</p></body></html>",
            encoding="utf-8",
        )
        return InstallPayload(version=version or "3", extracted_root=destination, source_url="https://example.invalid")

    monkeypatch.setattr("doc_scrolls.adapters.python_adapter.PythonDocsAdapter.install", fake_install)

    result = service.install_python_docs(version="3")

    assert result.page_count == 1
    assert result.db_path.exists()
    assert installed_rows
