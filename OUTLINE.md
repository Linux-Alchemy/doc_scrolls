# OUTLINE.md — `doc_scrolls` V1

## 1. Project Overview

### What we are building
`doc_scrolls` is a terminal-first documentation browser for Python docs with:
- local install of official Python docs
- local full-text search
- markdown-rendered reading pane
- Vim navigation
- bottom search bar in TUI

### Primary use case
Developers working inside terminal/tmux/Ghostty who want fast offline docs without browser context switching.

### V1 scope (strict)
- Support one source: Python official documentation
- Support install for one version at a time initially (default latest stable configured in adapter)
- Search and browse locally
- TUI with:
  - left results list
  - right markdown document pane
  - bottom search input

### Success criteria
- [ ] `doc-scrolls install python` downloads and indexes docs
- [ ] `doc-scrolls open python` starts TUI and shows searchable docs
- [ ] Search results update from bottom search bar
- [ ] `h/j/k/l`, `gg`, `G`, `/`, `n`, `N`, `q` work in TUI
- [ ] App works offline after install

---

## 2. Learning/Validation Objectives

| Objective | Proof Artifact | Self-check |
|---|---|---|
| Build robust install pipeline | install command + manifest + rollback behavior | If install fails midway, does existing data survive? |
| Ship practical local search | SQLite FTS query results from real docs | Are top matches relevant without hand-tuning every query? |
| Deliver keyboard-first UX | Keybinding map + manual smoke checks | Can I use the app start-to-finish without mouse/arrows? |

---

## 3. Architecture Decisions

### Core design
- Python package with explicit layers:
  - `adapters`: source-specific fetch/parsing behavior
  - `storage`: local paths/manifests
  - `index`: SQLite FTS indexing/query
  - `ui`: Textual app
  - `cli`: command entry points

### Technology choices

| Component | Choice | Why |
|---|---|---|
| CLI | Typer | concise command handling |
| TUI | Textual + Rich | split panes, markdown render, key handling |
| Index | SQLite FTS5 | local full-text search, zero external services |
| Fetch | httpx | reliable downloads |
| Parse | BeautifulSoup4 | straightforward HTML extraction |

### Rent justification
- `python_adapter.py`: isolates source-fetch rules
- `indexer.py`: parse/store/FTS build boundary
- `search.py`: query and ranking behavior
- `app.py`: user interactions and keymaps

---

## 4. Dependency Graph

```text
cli.py
  └── service.py

service.py
  ├── adapters/python_adapter.py
  ├── storage.py
  ├── indexer.py
  └── search.py

ui/app.py
  └── search.py + storage.py
```

Critical path:
1. install docs
2. build index
3. open UI
4. search + navigate

---

## 5. API / Contract Sketch

```python
# service.py

def install_python_docs(version: str | None = None) -> InstalledDocset: ...
def list_installed() -> list[InstalledDocset]: ...
def search(query: str, limit: int = 50) -> list[SearchResult]: ...
```

```python
# adapters/base.py
class SourceAdapter(Protocol):
    name: str
    def install(self, version: str | None = None) -> InstallResult: ...
```

```python
# search.py
class SearchEngine:
    def query(self, text: str, limit: int = 50) -> list[SearchResult]: ...
```

Error behavior:
- Unknown source -> user-friendly CLI error
- Network/download/parsing failures -> install aborted, temp files cleaned
- Empty query in UI -> show recent/default section list

---

## 6. File Structure

```text
doc_scrolls/
├── OUTLINE.md
├── README.md
├── pyproject.toml
├── doc_scrolls/
│   ├── __init__.py
│   ├── cli.py
│   ├── service.py
│   ├── storage.py
│   ├── models.py
│   ├── indexer.py
│   ├── search.py
│   ├── ui/
│   │   └── app.py
│   └── adapters/
│       ├── __init__.py
│       └── python_adapter.py
└── tests/
    ├── test_install.py
    └── test_search.py
```

---

## 7. Logic Flow

1. `doc-scrolls install python`
2. adapter downloads Python docs archive into temp dir
3. parser extracts page title/text + markdown-like content
4. indexer writes rows + FTS entries
5. `doc-scrolls open python` launches Textual UI
6. user types query in bottom bar, results update
7. Enter loads selected result in markdown pane
8. Vim motions navigate

---

## 8. Implementation Phases

### Phase 1: Walking skeleton
- scaffold package + CLI commands + config paths
- success: `--help` and command stubs work

### Phase 2: Python install pipeline
- download/expand docs, persist manifest
- success: `install` + `list` work

### Phase 3: Index + search
- parse docs into SQLite FTS, implement `search`
- success: relevant results returned

### Phase 4: TUI + Vim UX
- split panes, bottom search bar, keybindings
- success: docs readable/navigable fully from keyboard

### Phase 5: hardening
- better errors, docs, smoke tests

---

## 9. Security/Robustness

- Validate all filesystem paths under app data directory
- No shell execution for external content
- Keep parsing defensive (skip malformed pages)
- Transactional install (temp + atomic move)

---

## 10. V2+ (Out of Scope)

- more sources via adapter registry (`docs.rs`, MDN subsets, etc.)
- multi-version side-by-side management
- better relevance ranking and bookmarks

