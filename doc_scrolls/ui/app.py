from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.events import Key
from textual.widgets import Footer, Input, Label, ListItem, ListView, Markdown

from ..models import SearchResult
from ..service import search_with_note


# -- Custom widgets that delegate nav keys to the app -----------------------


class ResultsList(ListView):
    """ListView that yields vim keys to the app instead of handling them."""

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
    """Markdown viewer with vim-style scroll keys."""

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
        Binding("q", "quit", show=False),
        Binding("slash", "focus_search", show=False),
    ]

    def action_focus_results(self) -> None:
        self.app.query_one("#results", ResultsList).focus()

    def action_focus_search(self) -> None:
        self.app.query_one("#search", Input).focus()


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

    #doc {
      border: solid $surface;
      padding: 0 1;
      overflow-y: auto;
      height: 1fr;
    }

    #doc:focus-within, #doc:focus {
      border: solid $accent;
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

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            yield ResultsList(id="results")
            yield DocViewer("# doc_scrolls\nInstall docs and start searching.", id="doc")
        yield Input(placeholder="Search docs… (Esc to navigate, / to search, q to quit)", id="search")
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

    def _select_index(self, index: int) -> None:
        if not self.results:
            return
        self.current_index = max(0, min(index, len(self.results) - 1))
        self.query_one("#results", ResultsList).index = self.current_index
        self._render_current()

    # -- event handlers ------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self._refresh_results(event.value)

    def on_key(self, event: Key) -> None:
        """Handle keys that need app-level awareness (search bar escape)."""
        focused = self.focused
        is_search = isinstance(focused, Input) and focused.id == "search"

        if is_search and event.key in ("enter", "escape"):
            event.prevent_default()
            self._focus_results()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "results" and event.list_view.index is not None:
            self.current_index = event.list_view.index
            self._render_current()

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        """Suppress default link-opening behavior."""
        event.prevent_default()

    # -- actions (global) ----------------------------------------------------

    def action_page_up(self) -> None:
        self.query_one("#doc", DocViewer).scroll_page_up(animate=False)

    def action_page_down(self) -> None:
        self.query_one("#doc", DocViewer).scroll_page_down(animate=False)
