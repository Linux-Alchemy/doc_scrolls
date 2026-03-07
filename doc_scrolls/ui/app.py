from __future__ import annotations

import re
import sqlite3

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.widgets import Footer, Input, Label, ListItem, ListView, Markdown
from textual.widgets._markdown import MarkdownHeader

from ..models import SearchResult
from ..service import search_with_note


def _slugify(text: str) -> str:
    """Turn heading text into an anchor slug matching Python docs conventions."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    return slug


# -- Custom widgets ----------------------------------------------------------


class ResultsList(ListView):
    """ListView with vim-style keys."""

    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("l", "focus_doc", show=False),
        Binding("g", "first", show=False),
        Binding("G", "last", show=False),
        Binding("q", "quit", show=False),
        Binding("slash", "focus_search", show=False),
    ]

    def action_focus_doc(self) -> None:
        self.app.query_one("#doc", Markdown).focus()

    def action_focus_search(self) -> None:
        self.app.query_one("#search", Input).focus()

    def action_first(self) -> None:
        if self.children:
            self.index = 0

    def action_last(self) -> None:
        if self.children:
            self.index = len(self.children) - 1


class DocViewer(Markdown):
    """Markdown viewer with vim scroll and section jumping."""

    can_focus = True
    DEFAULT_CSS = """
    DocViewer {
        height: 1fr;
        overflow-y: auto;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding("j", "scroll_down", show=False),
        Binding("k", "scroll_up", show=False),
        Binding("h", "focus_results", show=False),
        Binding("g", "scroll_home", show=False),
        Binding("G", "scroll_end", show=False),
        Binding("t", "show_toc", show=False),
        Binding("q", "quit", show=False),
        Binding("slash", "focus_search", show=False),
    ]

    def action_focus_results(self) -> None:
        self.app.query_one("#results", ResultsList).focus()

    def action_focus_search(self) -> None:
        self.app.query_one("#search", Input).focus()

    def action_show_toc(self) -> None:
        self.app.action_show_toc()

    def scroll_to_anchor(self, anchor: str) -> bool:
        """Find a heading matching the anchor slug and scroll to it."""
        headers = list(self.query(MarkdownHeader))
        for header in headers:
            heading_text = str(header._content).strip()
            if _slugify(heading_text) == anchor.lstrip("#"):
                header.scroll_visible(top=True, animate=False)
                return True
        # Fuzzy fallback: check if anchor is contained in slug
        for header in headers:
            heading_text = str(header._content).strip()
            if anchor.lstrip("#") in _slugify(heading_text):
                header.scroll_visible(top=True, animate=False)
                return True
        return False


class TocList(ListView):
    """Table of contents popup list with vim keys."""

    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("escape", "dismiss_toc", show=False),
        Binding("t", "dismiss_toc", show=False),
        Binding("q", "quit", show=False),
    ]

    def action_dismiss_toc(self) -> None:
        self.app.action_dismiss_toc()


# -- Main app ---------------------------------------------------------------


class DocScrollsApp(App[None]):
    CSS = """
    Screen {
      layout: vertical;
    }

    #main {
      height: 1fr;
    }

    #results {
      width: 36;
      border: solid $primary;
    }

    #results:focus-within {
      border: solid $accent;
    }

    #doc-container {
      width: 1fr;
    }

    #doc {
      border: solid $surface;
      padding: 0 1;
      overflow-y: auto;
      height: 1fr;
    }

    #doc:focus-within, #doc:focus {
      border: solid $accent;
    }

    #toc-panel {
      display: none;
      height: 1fr;
      border: solid $warning;
      width: 100%;
    }

    #toc-panel.visible {
      display: block;
    }

    #search {
      dock: bottom;
      height: 3;
      border-top: solid $primary;
    }
    """

    BINDINGS = [
        Binding("pageup", "page_up", "PgUp", show=True),
        Binding("pagedown", "page_down", "PgDn", show=True),
    ]

    def __init__(self, source: str = "python", version: str | None = None) -> None:
        super().__init__()
        self.source = source
        self.version = version
        self.results: list[SearchResult] = []
        self.current_index = 0
        self._toc_headings: list[tuple[str, str]] = []  # (text, anchor)

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            yield ResultsList(id="results")
            with Vertical(id="doc-container"):
                yield DocViewer("# doc_scrolls\nInstall docs and start searching.", id="doc")
                yield TocList(id="toc-panel")
        yield Input(placeholder="Search docs… (Esc to navigate, / to search, t for ToC, q to quit)", id="search")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_results(query="")
        self._focus_search()

    # -- focus helpers -------------------------------------------------------

    def _focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def _focus_results(self) -> None:
        self.query_one("#results", ResultsList).focus()

    # -- data ----------------------------------------------------------------

    def _refresh_results(self, query: str) -> None:
        self.results, note = search_with_note(self.source, query=query, version=self.version, limit=75)
        list_view = self.query_one("#results", ResultsList)
        list_view.clear()

        for item in self.results:
            title = item.title.strip() or "(untitled)"
            list_view.append(ListItem(Label(title)))

        self.current_index = 0
        if self.results:
            list_view.index = 0
            self._render_current()
        else:
            if note:
                self.query_one("#doc", DocViewer).update(f"# Search Syntax Error\n{note}")
            else:
                self.query_one("#doc", DocViewer).update("# No results\nTry a different query.")

    def _render_current(self) -> None:
        if not self.results:
            return
        current = self.results[self.current_index]
        self.query_one("#doc", DocViewer).update(current.markdown)
        self._build_toc(current.markdown)

    def _build_toc(self, markdown: str) -> None:
        """Extract headings from markdown text for the ToC panel."""
        self._toc_headings = []
        for line in markdown.split("\n"):
            match = re.match(r"^(#{1,4})\s+(.+)", line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                # Strip markdown link syntax: [text](url) -> text
                text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
                anchor = _slugify(text)
                indent = "  " * (level - 1)
                self._toc_headings.append((f"{indent}{text}", anchor))

    def _select_index(self, index: int) -> None:
        if not self.results:
            return
        self.current_index = max(0, min(index, len(self.results) - 1))
        self.query_one("#results", ResultsList).index = self.current_index
        self._render_current()

    # -- ToC overlay ---------------------------------------------------------

    def action_show_toc(self) -> None:
        toc_panel = self.query_one("#toc-panel", TocList)
        toc_panel.clear()
        if not self._toc_headings:
            return
        for text, _anchor in self._toc_headings:
            toc_panel.append(ListItem(Label(text)))
        toc_panel.add_class("visible")
        toc_panel.index = 0
        toc_panel.focus()

    def action_dismiss_toc(self) -> None:
        toc_panel = self.query_one("#toc-panel", TocList)
        toc_panel.remove_class("visible")
        self.query_one("#doc", DocViewer).focus()

    # -- event handlers ------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self._refresh_results(event.value)

    def on_key(self, event: Key) -> None:
        """Handle keys that need app-level awareness."""
        focused = self.focused
        is_search = isinstance(focused, Input) and focused.id == "search"

        if is_search and event.key in ("enter", "escape"):
            event.prevent_default()
            self._focus_results()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "results" and event.list_view.index is not None:
            self.current_index = event.list_view.index
            self._render_current()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle Enter on a ToC item — jump to that heading."""
        if event.list_view.id == "toc-panel" and event.list_view.index is not None:
            idx = event.list_view.index
            if 0 <= idx < len(self._toc_headings):
                _text, anchor = self._toc_headings[idx]
                doc = self.query_one("#doc", DocViewer)
                doc.scroll_to_anchor(anchor)
                self.action_dismiss_toc()

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Handle link clicks: anchor jumps or cross-page navigation."""
        event.prevent_default()
        href = event.href

        # Anchor link — scroll to heading
        if href.startswith("#"):
            anchor = href.lstrip("#")
            if anchor:
                self.query_one("#doc", DocViewer).scroll_to_anchor(anchor)
            return

        # Internal page link — try to load from index
        self._try_load_page(href)

    def _try_load_page(self, href: str) -> None:
        """Attempt to load an internal docs page by matching its URL."""
        if not self.results:
            return
        current = self.results[self.current_index]
        # Resolve relative href against current page URL
        base = current.url.rsplit("/", 1)[0] + "/"
        if href.startswith("http"):
            target = href
        else:
            from urllib.parse import urljoin
            target = urljoin(base, href)

        # Strip fragment
        target_base = target.split("#")[0]
        fragment = target.split("#")[1] if "#" in target else None

        # Look up in search results first, then fall back to DB
        for result in self.results:
            if result.url.split("#")[0] == target_base:
                self.query_one("#doc", DocViewer).update(result.markdown)
                self._build_toc(result.markdown)
                if fragment:
                    self.query_one("#doc", DocViewer).scroll_to_anchor(fragment)
                return

        # Try DB lookup
        from ..service import get_installed
        try:
            installed = get_installed(source=self.source, version=self.version)
        except RuntimeError:
            return
        try:
            with sqlite3.connect(installed.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT id, title, url, markdown, plain_text FROM pages WHERE url = ? LIMIT 1",
                    (target_base,),
                ).fetchone()
                if row:
                    md = row["markdown"]
                    self.query_one("#doc", DocViewer).update(md)
                    self._build_toc(md)
                    if fragment:
                        self.query_one("#doc", DocViewer).scroll_to_anchor(fragment)
        except sqlite3.Error:
            pass

    # -- actions (global) ----------------------------------------------------

    def action_page_up(self) -> None:
        self.query_one("#doc", DocViewer).scroll_page_up(animate=False)

    def action_page_down(self) -> None:
        self.query_one("#doc", DocViewer).scroll_page_down(animate=False)
