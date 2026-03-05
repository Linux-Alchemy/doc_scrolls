from __future__ import annotations

import typer

from .service import get_installed, install_python_docs, list_installed, search_with_note
from .ui.app import DocScrollsApp

app = typer.Typer(help="doc_scrolls: terminal-first docs browser")


@app.command()
def install(source: str = typer.Argument("python"), version: str | None = typer.Option(None, "--version")) -> None:
    """Install docs for a supported source."""
    if source != "python":
        raise typer.BadParameter("V1 supports only source='python'")

    docset = install_python_docs(version=version)
    typer.echo(f"Installed {docset.source}@{docset.version} with {docset.page_count} indexed pages")


@app.command("list")
def list_cmd() -> None:
    """List installed docs."""
    items = list_installed()
    if not items:
        typer.echo("No installed docs found")
        return

    for item in items:
        typer.echo(f"{item.source}@{item.version} pages={item.page_count} db={item.db_path}")


@app.command("search")
def search(
    query: str = typer.Argument(..., help="FTS query string"),
    source: str = typer.Option("python", "--source"),
    version: str | None = typer.Option(None, "--version"),
    limit: int = typer.Option(15, "--limit"),
) -> None:
    """Search installed docs and print top matches."""
    rows, note = search_with_note(source=source, version=version, query=query, limit=limit)
    if note:
        typer.secho(note, fg=typer.colors.YELLOW)

    if not rows:
        typer.echo("No matches")
        return

    for idx, row in enumerate(rows, start=1):
        typer.echo(f"{idx:>2}. {row.title}\\n    {row.url}\\n")


@app.command()
def open(
    source: str = typer.Argument("python"),
    version: str | None = typer.Option(None, "--version"),
) -> None:
    """Open TUI browser."""
    _ = get_installed(source=source, version=version)
    app_ui = DocScrollsApp(source=source, version=version)
    app_ui.run()


if __name__ == "__main__":
    app()
