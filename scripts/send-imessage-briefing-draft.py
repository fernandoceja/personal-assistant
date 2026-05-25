#!/usr/bin/env python3
"""Preview or explicitly send a reviewed iMessage briefing draft.

Default behavior is dry-run/no-send. The only send path is gated behind
--send-approved-draft and requires --recipient. This script reads only local
*-imessage-draft.txt files and never generates a briefing or reads safe packets.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_DRAFT_CHARS = 900
MAX_LIVE_DRAFT_AGE_SECONDS = 4 * 60 * 60
APPROVED_SELF_RECIPIENT = "nando0589@gmail.com"
CONFIRM_PHRASE = "SEND DAILY BRIEF TO FERNANDO"
RAW_DETAIL_PATTERNS = (
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"\b(message|thread)\s*id\b\s*[:#]?\s*\S*", re.IGNORECASE),
    re.compile(r"\battachment\b\s*[:#]?\s*\S*", re.IGNORECASE),
    re.compile(r"\braw\s+(gmail|api)\b", re.IGNORECASE),
    re.compile(r"\b(gmail|calendar)\s+api\b", re.IGNORECASE),
)
DRAFT_NAME_PATTERN = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-\d{2}-imessage-draft\.txt$")


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


def validate_live_recipient(recipient: str | None) -> str:
    if not recipient:
        raise ValueError("--recipient is required when --send-approved-draft is used")
    clean = recipient.strip()
    if any(separator in clean for separator in (",", ";", "\n", "\r")):
        raise ValueError("Live send rejected: group or multi-recipient sends are not allowed")
    if clean != APPROVED_SELF_RECIPIENT:
        raise ValueError("Live send rejected: recipient is not the approved Fernando/self value")
    return clean


def validate_live_confirmation(confirm: str | None) -> None:
    if confirm != CONFIRM_PHRASE:
        raise ValueError(f'Live send rejected: --confirm must exactly equal "{CONFIRM_PHRASE}"')


def validate_live_draft_freshness(draft_path: Path) -> None:
    match = DRAFT_NAME_PATTERN.match(draft_path.name)
    if not match:
        raise ValueError("Live send rejected: draft filename must be dated like YYYY-MM-DD-HH-imessage-draft.txt")

    today = datetime.now().astimezone().date().isoformat()
    if match.group("date") != today:
        raise ValueError("Live send rejected: draft is stale because its filename date is not today")

    mtime = datetime.fromtimestamp(draft_path.stat().st_mtime, tz=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - mtime).total_seconds()
    if age_seconds < -300:
        raise ValueError("Live send rejected: draft modification time is unexpectedly in the future")
    if age_seconds > MAX_LIVE_DRAFT_AGE_SECONDS:
        raise ValueError("Live send rejected: draft is older than the live-send freshness window")


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


def write_send_attempt_audit(repo_root: Path, draft_path: Path, status: str, error: str | None = None) -> Path:
    audit_dir = repo_root / "logs" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    audit_path = audit_dir / f"imessage-send-attempt-{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    payload = {
        "kind": "imessage-send-attempt",
        "timestamp_utc": now.isoformat().replace("+00:00", "Z"),
        "status": status,
        "draft_path": str(draft_path),
        "recipient": "approved-self",
        "message_body_recorded": False,
        "paths_only": True,
    }
    if error:
        payload["error"] = error
    audit_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return audit_path


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
        help="Required with --send-approved-draft. Must exactly match the approved Fernando/self value.",
    )
    parser.add_argument(
        "--confirm",
        help=f'Required with --send-approved-draft. Must exactly equal "{CONFIRM_PHRASE}".',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        repo_root = repo_root_from_script()
        draft_input = Path(args.draft_file) if args.draft_file else find_latest_draft(repo_root)
        draft_path, draft_text = load_draft(draft_input)

        if not args.send_approved_draft:
            print(f"Draft path: {draft_path}")
            print("Preview:")
            print(draft_text)
            print("Mode: DRY RUN — no iMessage sent.")
            print("Safety: osascript/Messages was not called.")
            return 0

        recipient = validate_live_recipient(args.recipient)
        validate_live_confirmation(args.confirm)
        validate_live_draft_freshness(draft_path)
        print(f"Draft path: {draft_path}")

        # The only send-capable path is below this explicit approval gate.
        try:
            send_imessage(recipient, draft_text)
            audit_path = write_send_attempt_audit(repo_root, draft_path, "sent")
        except (OSError, subprocess.CalledProcessError) as exc:
            audit_path = write_send_attempt_audit(repo_root, draft_path, "failed", exc.__class__.__name__)
            print(f"Audit manifest: {audit_path}")
            raise

        print("Mode: SENT — approved draft sent to Fernando/self.")
        print(f"Audit manifest: {audit_path}")
        return 0
    except (FileNotFoundError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
