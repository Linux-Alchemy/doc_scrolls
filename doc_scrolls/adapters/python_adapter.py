from __future__ import annotations

import shutil
import tarfile
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
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

    def install(
        self,
        destination: Path,
        version: str | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> InstallPayload:
        resolved_version = (version or DEFAULT_VERSION).strip()
        self._report(progress, f"Resolving Python docs archive for version '{resolved_version}'...")
        archive_url = self._discover_archive_url(resolved_version)
        self._report(progress, f"Archive URL resolved: {archive_url}")

        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="doc_scrolls_python_") as tmp:
            tmp_path = Path(tmp)
            archive_path = tmp_path / "python-docs.tar.bz2"
            self._report(progress, "Downloading docs archive...")
            self._download_file(archive_url, archive_path, progress=progress)
            self._report(progress, "Extracting archive...")
            with tarfile.open(archive_path, "r:bz2") as tar:
                self._safe_extract(tar, tmp_path)

            extracted_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
            if not extracted_dirs:
                raise RuntimeError("No extracted directory found in Python docs archive")
            source_root = extracted_dirs[0]

            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source_root, destination)
            self._report(progress, "Archive extracted.")

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

    def _download_file(self, url: str, target: Path, progress: Callable[[str], None] | None = None) -> None:
        report_step = 8 * 1024 * 1024
        with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
            response.raise_for_status()
            downloaded = 0
            next_report = report_step
            total_bytes = int(response.headers.get("Content-Length", "0") or 0)
            with target.open("wb") as handle:
                for chunk in response.iter_bytes(chunk_size=1024 * 128):
                    if chunk:
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if downloaded >= next_report:
                            if total_bytes:
                                self._report(
                                    progress,
                                    f"Downloaded {downloaded // (1024 * 1024)} / {total_bytes // (1024 * 1024)} MiB...",
                                )
                            else:
                                self._report(progress, f"Downloaded {downloaded // (1024 * 1024)} MiB...")
                            next_report += report_step

    def _safe_extract(self, tar: tarfile.TarFile, destination: Path) -> None:
        dest_abs = destination.resolve()
        safe_members: list[tarfile.TarInfo] = []
        for member in tar.getmembers():
            normalized_name = member.name.replace("\\", "/")
            member_path = PurePosixPath(normalized_name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError("Archive contains unsafe path traversal entries")

            candidate = (dest_abs / Path(*member_path.parts)).resolve()
            try:
                candidate.relative_to(dest_abs)
            except ValueError as exc:
                raise RuntimeError("Archive contains unsafe path traversal entries") from exc

            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise RuntimeError("Archive contains unsafe member types")

            if member.isfile() or member.isdir():
                safe_members.append(member)

        tar.extractall(destination, members=safe_members)

    def _report(self, progress: Callable[[str], None] | None, message: str) -> None:
        if progress:
            progress(message)
