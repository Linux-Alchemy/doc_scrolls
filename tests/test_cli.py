from pathlib import Path

from typer.testing import CliRunner

import doc_scrolls.cli as cli
from doc_scrolls.models import InstalledDocset


runner = CliRunner()


def test_install_shows_progress_and_success(monkeypatch) -> None:
    def fake_install(version=None, progress=None):
        assert progress is not None
        progress("Mock download step")
        return InstalledDocset(
            source="python",
            version=version or "3",
            root_path=Path("/tmp/docset"),
            db_path=Path("/tmp/docset/index.db"),
            page_count=1,
        )

    monkeypatch.setattr(cli, "install_python_docs", fake_install)

    result = runner.invoke(cli.app, ["install", "python", "--version", "3"])

    assert result.exit_code == 0
    assert "[install] Mock download step" in result.output
    assert "Installed python@3 with 1 indexed pages" in result.output


def test_search_handles_runtime_error(monkeypatch) -> None:
    def fake_search_with_note(**kwargs):
        raise RuntimeError("No installed docsets found for source 'python'. Run install first.")

    monkeypatch.setattr(cli, "search_with_note", fake_search_with_note)

    result = runner.invoke(cli.app, ["search", "asyncio"])

    assert result.exit_code == 1
    assert "Run install first." in result.output


def test_open_handles_runtime_error(monkeypatch) -> None:
    def fake_get_installed(*args, **kwargs):
        raise RuntimeError("No installed docsets found for source 'python'. Run install first.")

    monkeypatch.setattr(cli, "get_installed", fake_get_installed)

    result = runner.invoke(cli.app, ["open", "python"])

    assert result.exit_code == 1
    assert "Run install first." in result.output
