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

## Notes
- First install requires internet.
- Search and browsing are offline after install.
- Adapter architecture is set up for adding more sources in V2.
