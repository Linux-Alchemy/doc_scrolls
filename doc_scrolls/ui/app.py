from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Footer, Input, Label, ListItem, ListView, Markdown

from ..models import SearchResult
from ..service import search_with_note


class DocSelected(Message):
    def __init__(self, result: SearchResult) -> None:
        self.result = result
        super().__init__()


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

    #doc {
      border: solid $accent;
      padding: 0 1;
    }

    #search {
      dock: bottom;
      height: 3;
      border-top: solid $primary;
    }
    """

    BINDINGS = [
        Binding("/", "focus_search", "Search", show=True),
        Binding("j", "scroll_down", "Down", show=True),
        Binding("k", "scroll_up", "Up", show=True),
        Binding("h", "scroll_left", "Left", show=True),
        Binding("l", "scroll_right", "Right", show=True),
        Binding("g,g", "doc_top", "Top", show=True),
        Binding("G", "doc_bottom", "Bottom", show=True),
        Binding("n", "next_result", "Next hit", show=True),
        Binding("N", "prev_result", "Prev hit", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, source: str = "python", version: str | None = None) -> None:
        super().__init__()
        self.source = source
        self.version = version
        self.results: list[SearchResult] = []
        self.current_index = 0

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            yield ListView(id="results")
            yield Markdown("# doc_scrolls\nInstall docs and start searching.", id="doc")
        yield Input(placeholder="Search docs...", id="search")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_results(query="")
        self._focus_search()

    def _focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def _refresh_results(self, query: str) -> None:
        self.results, note = search_with_note(self.source, query=query, version=self.version, limit=75)
        list_view = self.query_one("#results", ListView)
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
                self.query_one("#doc", Markdown).update(f"# Search Syntax Error\n{note}")
            else:
                self.query_one("#doc", Markdown).update("# No results\nTry a different query.")

    def _render_current(self) -> None:
        if not self.results:
            return
        current = self.results[self.current_index]
        self.query_one("#doc", Markdown).update(current.markdown)

    def _select_index(self, index: int) -> None:
        if not self.results:
            return
        self.current_index = max(0, min(index, len(self.results) - 1))
        self.query_one("#results", ListView).index = self.current_index
        self._render_current()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search":
            self._refresh_results(event.value)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id == "results" and event.list_view.index is not None:
            self._select_index(event.list_view.index)

    def action_focus_search(self) -> None:
        self._focus_search()

    def action_scroll_down(self) -> None:
        self.query_one("#doc", Markdown).scroll_down(animate=False)

    def action_scroll_up(self) -> None:
        self.query_one("#doc", Markdown).scroll_up(animate=False)

    def action_scroll_left(self) -> None:
        self.query_one("#doc", Markdown).scroll_left(animate=False)

    def action_scroll_right(self) -> None:
        self.query_one("#doc", Markdown).scroll_right(animate=False)

    def action_doc_top(self) -> None:
        self.query_one("#doc", Markdown).scroll_home(animate=False)

    def action_doc_bottom(self) -> None:
        self.query_one("#doc", Markdown).scroll_end(animate=False)

    def action_next_result(self) -> None:
        self._select_index(self.current_index + 1)

    def action_prev_result(self) -> None:
        self._select_index(self.current_index - 1)
