#!/usr/bin/env python3
"""P0-06 gate: no Waze/Google material in the repo.

Names, counts, sizes and measured numbers are facts and may be recorded; artwork, audio, fonts,
string tables, code and package identifiers may not. Documentation may discuss the name in prose,
so only *shipped* files are scanned, and comments are ignored (a comment is not a product surface).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHIPPED = ["app", "design", "assets3d", "core", "backend", "proto", "server"]
CODE_SUFFIXES = {".kt", ".kts", ".java", ".xml", ".json", ".py", ".toml", ".rs", ".proto", ".sh", ".yaml", ".yml"}
BANNED_FILES = {".apk", ".aab", ".pck", ".dex", ".so", ".mp3", ".ogg", ".wav", ".jks", ".keystore"}
# The Gradle wrapper is Gradle's own jar, not an app asset.
ALLOWED = {ROOT / "gradle" / "wrapper" / "gradle-wrapper.jar"}

TRADEMARK = re.compile(r"\bwaze\b", re.I)
FOREIGN_ID = re.compile(r"com\.waze|com\.google\.android\.apps\.maps", re.I)


def strip_comment(line: str, suffix: str) -> str:
    """Remove trailing comments so a prose mention is not a finding."""
    if suffix in {".kt", ".kts", ".java", ".rs"}:
        line = re.sub(r"//.*$", "", line)
        line = re.sub(r"/\*.*?\*/", "", line)
    elif suffix in {".py", ".sh", ".yaml", ".yml", ".toml"}:
        line = re.sub(r"(?<!:)//.*$", "", line)
        line = re.sub(r"#.*$", "", line)
    elif suffix == ".xml":
        line = re.sub(r"<!--.*?-->", "", line)
    elif suffix == ".json":
        pass  # JSON has no comments; a match here is real
    return line


def main() -> int:
    problems: list[str] = []
    for top in SHIPPED:
        base = ROOT / top
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path in ALLOWED or "/build/" in str(path):
                continue
            suffix = path.suffix.lower()
            if suffix in BANNED_FILES:
                problems.append(f"binary asset in the tree: {path.relative_to(ROOT)}")
                continue
            if suffix not in CODE_SUFFIXES:
                continue
            in_doc = False
            for n, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
                if suffix == ".py" and raw.count('"""') % 2 == 1:
                    in_doc = not in_doc  # prose, not a product surface
                    continue
                if in_doc:
                    continue
                line = strip_comment(raw, suffix)
                if not line.strip():
                    continue
                if TRADEMARK.search(line) or FOREIGN_ID.search(line):
                    problems.append(f"{path.relative_to(ROOT)}:{n}: {raw.strip()[:110]}")

    for p in problems:
        print(f"  {p}", file=sys.stderr)
    if problems:
        print(f"\ncheck_no_waze_assets: {len(problems)} finding(s) — see NOTICE.md", file=sys.stderr)
        return 1
    print("check_no_waze_assets: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
