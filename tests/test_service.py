from pathlib import Path

import pytest

import doc_scrolls.service as service
from doc_scrolls.models import InstalledDocset


def _docset(version: str) -> InstalledDocset:
    return InstalledDocset(
        source="python",
        version=version,
        root_path=Path(f"/tmp/docsets/python/{version}"),
        db_path=Path(f"/tmp/docsets/python/{version}/index.db"),
        page_count=100,
    )


def test_get_installed_prefers_semantic_latest(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "load_installed",
        lambda: [_docset("3.9"), _docset("3.11"), _docset("3.10")],
    )

    installed = service.get_installed(source="python")

    assert installed.version == "3.11"


def test_get_installed_with_explicit_version(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "load_installed",
        lambda: [_docset("3.9"), _docset("3.11")],
    )

    installed = service.get_installed(source="python", version="3.9")

    assert installed.version == "3.9"


def test_get_installed_raises_for_missing_source(monkeypatch) -> None:
    monkeypatch.setattr(service, "load_installed", lambda: [])

    with pytest.raises(RuntimeError, match="No installed docsets found"):
        service.get_installed(source="python")
