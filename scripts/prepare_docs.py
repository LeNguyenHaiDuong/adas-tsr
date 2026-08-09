#!/usr/bin/env python3
"""Build the MkDocs source tree without repository symlinks."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS_BUILD = ROOT / ".mkdocs_docs"


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".ipynb_checkpoints"))


def main() -> None:
    if DOCS_BUILD.exists():
        shutil.rmtree(DOCS_BUILD)
    DOCS_BUILD.mkdir(parents=True)

    copy_file(ROOT / "README.md", DOCS_BUILD / "index.md")
    copy_file(ROOT / "TROUBLESHOOTING.md", DOCS_BUILD / "TROUBLESHOOTING.md")
    copy_tree(ROOT / "research", DOCS_BUILD / "research")
    copy_file(ROOT / "videos" / "README.md", DOCS_BUILD / "videos" / "README.md")
    copy_tree(ROOT / "docs" / "javascripts", DOCS_BUILD / "javascripts")

    print(f"Prepared MkDocs sources in {DOCS_BUILD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
