# doc_scrolls

Terminal-first docs browser with offline search and markdown rendering.

## V1 Scope
- Source support: Python docs only
- Install docs locally and index with SQLite FTS5
- Open Textual UI with:
  - results pane (left)
  - markdown doc pane (right)
  - search bar (bottom)
- Vim motions: `h/j/k/l`, `gg`, `G`, `n`, `N`, `/`, `q`

## Install

```bash
cd ~/github/Linux-Alchemy/doc_scrolls
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# install Python docs (default docs.python.org/3)
doc-scrolls install python

# list installed docsets
doc-scrolls list

# search from CLI
doc-scrolls search "asyncio gather"

# open terminal UI
doc-scrolls open python
```

## CLI Commands

| Command | Description |
|---|---|
| `doc-scrolls install python` | Download and index Python docs locally |
| `doc-scrolls install python --version 3.12` | Install a specific version |
| `doc-scrolls list` | Show all installed docsets |
| `doc-scrolls search "query"` | Search from the command line |
| `doc-scrolls search "query" --limit 5` | Limit number of results |
| `doc-scrolls open python` | Launch the TUI browser |

## TUI Keybindings

### Zones

The TUI has three focus zones: **search bar**, **results list**, and **doc pane**. Keys behave differently depending on which zone is active. The active zone is highlighted with an accent border.

### Navigation

| Key | Context | Action |
|---|---|---|
| `/` | Any zone | Jump to search bar |
| `Escape` | Search bar | Move to results list |
| `Enter` | Search bar | Move to results list |
| `j` / `k` | Results list | Move selection down/up |
| `g` / `G` | Results list | Jump to first/last result |
| `l` | Results list | Move to doc pane |
| `h` | Doc pane | Move to results list |
| `j` / `k` | Doc pane | Scroll down/up |
| `g` / `G` | Doc pane | Scroll to top/bottom |
| `PgUp` / `PgDn` | Any zone | Page up/down in doc pane |

### Table of Contents

| Key | Context | Action |
|---|---|---|
| `t` | Doc pane | Open ToC section picker |
| `j` / `k` | ToC panel | Navigate sections |
| `Enter` | ToC panel | Jump to selected section |
| `Escape` / `t` | ToC panel | Close ToC, return to doc pane |

### Find in Page

| Key | Context | Action |
|---|---|---|
| `Ctrl+F` | Doc pane | Open find bar |
| `Enter` | Find bar | Jump to next match |
| `Escape` | Find bar | Close find bar (matches preserved) |
| `n` / `N` | Doc pane | Next/previous match |

Matched blocks are highlighted in yellow. The current match is brighter.

### Quitting

| Key | Action |
|---|---|
| `q` | Quit (from results list or doc pane) |
| `Ctrl+Q` | Quit (from anywhere) |

## Example Workflow

```
1.  Launch:           doc-scrolls open python
2.  Search:           Type "turtle" in the search bar
3.  Browse results:   Escape → j/k to pick a result
4.  Read docs:        l to enter the doc pane
5.  Jump to section:  t → pick from ToC → Enter
6.  Find keyword:     Ctrl+F → type "forward" → Enter
7.  Hop matches:      Escape → n for next, N for previous
8.  New search:       / to return to search bar
9.  Quit:             q from results or doc pane
```

## Notes
- First install requires internet.
- Search and browsing are offline after install.
- Clicking links in the doc pane navigates internally (anchors scroll to headings, page links load from the index).
- Adapter architecture is set up for adding more sources in V2.
