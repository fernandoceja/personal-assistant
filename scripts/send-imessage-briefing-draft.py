#!/usr/bin/env python3
"""Preview or explicitly send a reviewed iMessage briefing draft.

Default behavior is dry-run/no-send. The only send path is gated behind
--send-approved-draft and requires --recipient. This script reads only local
*-imessage-draft.txt files and never generates a briefing or reads safe packets.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MAX_DRAFT_CHARS = 900
RAW_DETAIL_PATTERNS = (
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"\b(message|thread)\s*id\b\s*[:#]?\s*\S*", re.IGNORECASE),
    re.compile(r"\battachment\b\s*[:#]?\s*\S*", re.IGNORECASE),
    re.compile(r"\braw\s+(gmail|api)\b", re.IGNORECASE),
    re.compile(r"\b(gmail|calendar)\s+api\b", re.IGNORECASE),
)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def find_latest_draft(repo_root: Path) -> Path:
    briefings_dir = repo_root / "briefings"
    candidates = sorted(briefings_dir.glob("*-imessage-draft.txt"))
    if not candidates:
        raise FileNotFoundError("No iMessage draft found at briefings/*-imessage-draft.txt")
    return candidates[-1]


def validate_draft_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.name.endswith("-imessage-draft.txt"):
        raise ValueError("Input must be a reviewed iMessage draft ending in -imessage-draft.txt; safe packets are not allowed")
    if not resolved.is_file():
        raise FileNotFoundError(f"Draft file not found: {resolved}")
    return resolved


def validate_draft_text(text: str) -> str:
    draft = text.strip()
    if not draft:
        raise ValueError("Draft failed safety validation: draft is empty")
    if len(draft) > MAX_DRAFT_CHARS:
        raise ValueError(f"Draft failed safety validation: draft exceeds {MAX_DRAFT_CHARS} characters")
    for pattern in RAW_DETAIL_PATTERNS:
        if pattern.search(draft):
            raise ValueError("Draft failed safety validation: raw details, links, IDs, attachments, or API output are not allowed")
    return draft


def load_draft(path: Path) -> tuple[Path, str]:
    draft_path = validate_draft_path(path)
    return draft_path, validate_draft_text(draft_path.read_text(encoding="utf-8"))


def send_imessage(recipient: str, message: str) -> None:
    """Explicit send-only function. Never call without prior approval gates."""
    apple_script = """
on run argv
  set targetBuddy to item 1 of argv
  set messageText to item 2 of argv
  tell application "Messages"
    send messageText to buddy targetBuddy of service "iMessage"
  end tell
end run
""".strip()
    subprocess.run(["osascript", "-e", apple_script, recipient, message], check=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run preview by default; explicitly send a reviewed local iMessage draft only with approval flag."
    )
    parser.add_argument(
        "draft_file",
        nargs="?",
        help="Optional path to briefings/YYYY-MM-DD-HH-imessage-draft.txt. Defaults to latest draft.",
    )
    parser.add_argument(
        "--send-approved-draft",
        action="store_true",
        help="Explicit approval gate required before sending the reviewed draft.",
    )
    parser.add_argument(
        "--recipient",
        help="Required with --send-approved-draft. Example: '+1XXXXXXXXXX' or 'Fernando'.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.send_approved_draft and not args.recipient:
            raise ValueError("--recipient is required when --send-approved-draft is used")

        repo_root = repo_root_from_script()
        draft_input = Path(args.draft_file) if args.draft_file else find_latest_draft(repo_root)
        draft_path, draft_text = load_draft(draft_input)

        print(f"Draft path: {draft_path}")
        print("Preview:")
        print(draft_text)

        if not args.send_approved_draft:
            print("Mode: DRY RUN — no iMessage sent.")
            print("Safety: osascript/Messages was not called.")
            return 0

        # The only send-capable path is below this explicit approval gate.
        send_imessage(args.recipient, draft_text)
        print(f"Mode: SENT — approved draft sent to {args.recipient}.")
        return 0
    except (FileNotFoundError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
