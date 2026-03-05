from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class InstalledDocset:
    source: str
    version: str
    root_path: Path
    db_path: Path
    page_count: int


@dataclass(slots=True)
class SearchResult:
    page_id: int
    title: str
    url: str
    snippet: str
    markdown: str
    score: float


@dataclass(slots=True)
class ParsedPage:
    title: str
    url: str
    markdown: str
    plain_text: str
