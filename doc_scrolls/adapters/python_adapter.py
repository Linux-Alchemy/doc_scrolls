from __future__ import annotations

import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


DEFAULT_VERSION = "3"


@dataclass(slots=True)
class InstallPayload:
    version: str
    extracted_root: Path
    source_url: str


class PythonDocsAdapter:
    name = "python"

    def install(self, destination: Path, version: str | None = None) -> InstallPayload:
        resolved_version = (version or DEFAULT_VERSION).strip()
        archive_url = self._discover_archive_url(resolved_version)

        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="doc_scrolls_python_") as tmp:
            tmp_path = Path(tmp)
            archive_path = tmp_path / "python-docs.tar.bz2"
            self._download_file(archive_url, archive_path)
            with tarfile.open(archive_path, "r:bz2") as tar:
                self._safe_extract(tar, tmp_path)

            extracted_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
            if not extracted_dirs:
                raise RuntimeError("No extracted directory found in Python docs archive")
            source_root = extracted_dirs[0]

            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source_root, destination)

        return InstallPayload(version=resolved_version, extracted_root=destination, source_url=archive_url)

    def _discover_archive_url(self, version: str) -> str:
        page_url = f"https://docs.python.org/{version}/download.html"
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(page_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            if "docs-html.tar.bz2" in href:
                return urljoin(page_url, href)

        raise RuntimeError(f"Could not locate docs HTML archive at {page_url}")

    def _download_file(self, url: str, target: Path) -> None:
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_bytes(chunk_size=1024 * 128):
                    if chunk:
                        handle.write(chunk)

    def _safe_extract(self, tar: tarfile.TarFile, destination: Path) -> None:
        dest_abs = destination.resolve()
        for member in tar.getmembers():
            member_abs = (destination / member.name).resolve()
            if not str(member_abs).startswith(str(dest_abs)):
                raise RuntimeError("Archive contains unsafe path traversal entries")
        tar.extractall(destination)
