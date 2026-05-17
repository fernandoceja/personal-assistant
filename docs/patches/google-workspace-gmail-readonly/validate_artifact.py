#!/usr/bin/env python3
"""Static validator for the Gmail read-only safe-list patch artifact.

Runs only local file checks. It does not authenticate, read tokens, or call Gmail.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PY_FILES = [ROOT / "setup.py", ROOT / "google_api.py"]
ALL_FILES = [p for p in ROOT.iterdir() if p.is_file()]

REQUIRED = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "safe-list",
]
FORBIDDEN_IN_PY = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.insert",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://mail.google.com/",
]
FORBIDDEN_API_PATTERNS = [
    r"format\s*=\s*['\"]full['\"]",
    r"format\s*=\s*['\"]raw['\"]",
    r"messages\(\)\.send",
    r"messages\(\)\.modify",
    r"messages\(\)\.trash",
    r"messages\(\)\.delete",
    r"attachments\(\)\.get",
]
SECRET_PATTERNS = [
    r'"(refresh_token|access_token|private_key)"\s*:',
    "BEGIN " + "PRIVATE KEY",
]


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    combined = "\n".join(read(path) for path in ALL_FILES)
    py_combined = "\n".join(read(path) for path in PY_FILES)

    for needle in REQUIRED:
        if needle not in combined:
            fail(f"required text missing: {needle}")

    for needle in FORBIDDEN_IN_PY:
        if needle in py_combined:
            fail(f"forbidden Gmail scope appears in Python reference: {needle}")

    for pattern in FORBIDDEN_API_PATTERNS:
        if re.search(pattern, py_combined):
            fail(f"forbidden Gmail API pattern appears: {pattern}")

    for pattern in SECRET_PATTERNS:
        if re.search(pattern, combined):
            fail(f"secret/token marker appears in artifact: {pattern}")

    print("PASS: Gmail read-only safe-list patch artifact static checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
