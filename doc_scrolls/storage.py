from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import InstalledDocset

APP_DIR = Path.home() / ".local" / "share" / "doc_scrolls"
DOCSETS_DIR = APP_DIR / "docsets"
METADATA_PATH = APP_DIR / "installed.json"


def ensure_dirs() -> None:
    DOCSETS_DIR.mkdir(parents=True, exist_ok=True)


def docset_root(source: str, version: str) -> Path:
    return DOCSETS_DIR / source / version


def docset_db_path(source: str, version: str) -> Path:
    return docset_root(source, version) / "index.db"


def load_installed() -> list[InstalledDocset]:
    ensure_dirs()
    if not METADATA_PATH.exists():
        return []
    data = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return [
        InstalledDocset(
            source=item["source"],
            version=item["version"],
            root_path=Path(item["root_path"]),
            db_path=Path(item["db_path"]),
            page_count=item["page_count"],
        )
        for item in data
    ]


def save_installed(items: list[InstalledDocset]) -> None:
    ensure_dirs()
    data = [
        {
            **asdict(item),
            "root_path": str(item.root_path),
            "db_path": str(item.db_path),
        }
        for item in items
    ]
    METADATA_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def upsert_installed(docset: InstalledDocset) -> None:
    items = load_installed()
    filtered = [x for x in items if not (x.source == docset.source and x.version == docset.version)]
    filtered.append(docset)
    save_installed(sorted(filtered, key=lambda d: (d.source, d.version)))
