import io
import tarfile
from pathlib import Path

import pytest

from doc_scrolls.adapters.python_adapter import PythonDocsAdapter


def _build_tarball(path: Path, members: list[dict[str, object]]) -> None:
    with tarfile.open(path, "w:bz2") as tar:
        for member in members:
            info = tarfile.TarInfo(str(member["name"]))
            info.type = member.get("type", tarfile.REGTYPE)
            info.mtime = 0

            if info.type in (tarfile.REGTYPE, tarfile.AREGTYPE):
                payload = member.get("data", b"")
                if isinstance(payload, str):
                    payload = payload.encode("utf-8")
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
                continue

            info.size = 0
            info.linkname = str(member.get("linkname", ""))
            tar.addfile(info)


def test_safe_extract_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "bad.tar.bz2"
    _build_tarball(
        archive,
        [
            {"name": "../evil.txt", "data": "nope"},
        ],
    )

    adapter = PythonDocsAdapter()
    with tarfile.open(archive, "r:bz2") as tar, pytest.raises(RuntimeError, match="unsafe path traversal"):
        adapter._safe_extract(tar, tmp_path / "out")


def test_safe_extract_rejects_absolute_path(tmp_path: Path) -> None:
    archive = tmp_path / "bad.tar.bz2"
    _build_tarball(
        archive,
        [
            {"name": "/etc/passwd", "data": "nope"},
        ],
    )

    adapter = PythonDocsAdapter()
    with tarfile.open(archive, "r:bz2") as tar, pytest.raises(RuntimeError, match="unsafe path traversal"):
        adapter._safe_extract(tar, tmp_path / "out")


@pytest.mark.parametrize(
    ("member_type", "name", "linkname"),
    [
        (tarfile.SYMTYPE, "docs/link", "/etc/passwd"),
        (tarfile.LNKTYPE, "docs/hardlink", "docs/index.html"),
    ],
)
def test_safe_extract_rejects_links(
    tmp_path: Path, member_type: bytes, name: str, linkname: str
) -> None:
    archive = tmp_path / "bad-links.tar.bz2"
    _build_tarball(
        archive,
        [
            {"name": "docs/index.html", "data": "<h1>ok</h1>"},
            {"name": name, "type": member_type, "linkname": linkname},
        ],
    )

    adapter = PythonDocsAdapter()
    with tarfile.open(archive, "r:bz2") as tar, pytest.raises(RuntimeError, match="unsafe member types"):
        adapter._safe_extract(tar, tmp_path / "out")


def test_safe_extract_allows_regular_files_and_dirs(tmp_path: Path) -> None:
    archive = tmp_path / "good.tar.bz2"
    _build_tarball(
        archive,
        [
            {"name": "python-docs", "type": tarfile.DIRTYPE},
            {"name": "python-docs/index.html", "data": "<h1>Python Docs</h1>"},
        ],
    )

    destination = tmp_path / "out"
    destination.mkdir(parents=True, exist_ok=True)

    adapter = PythonDocsAdapter()
    with tarfile.open(archive, "r:bz2") as tar:
        adapter._safe_extract(tar, destination)

    page = destination / "python-docs" / "index.html"
    assert page.exists()
    assert "Python Docs" in page.read_text(encoding="utf-8")
