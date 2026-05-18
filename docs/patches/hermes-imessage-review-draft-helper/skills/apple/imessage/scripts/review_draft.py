#!/usr/bin/env python3
"""Open a review-only Messages.app draft without sending it.

This helper intentionally has no send path. It builds a macOS Messages URL and
opens it with Launch Services so the user can review/edit/send manually.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from urllib.parse import quote


class DraftError(ValueError):
    """Raised when a draft cannot be prepared safely."""


def _clean_recipient(recipient: str) -> str:
    recipient = (recipient or "").strip()
    if not recipient:
        raise DraftError("recipient is required")
    if any(ch in recipient for ch in "\r\n"):
        raise DraftError("recipient must be a single line")
    return recipient


def _clean_message(message: str) -> str:
    message = message or ""
    if not message.strip():
        raise DraftError("message text is required")
    return message


def build_messages_url(recipient: str, message: str) -> str:
    """Return a macOS Messages.app URL for a recipient + draft body.

    The sms: URL scheme is handled by Messages.app on macOS. Opening this URL
    creates a compose window with the body filled in; it does not press Return
    or invoke the Messages AppleScript `send` command.
    """

    recipient = _clean_recipient(recipient)
    message = _clean_message(message)
    recipient_q = quote(recipient, safe='+@.-_')
    body_q = quote(message, safe='')
    return f"sms://open?addresses={recipient_q}&body={body_q}"


def open_review_draft(recipient: str, message: str) -> str:
    """Open Messages.app to a review-only draft and return the URL used."""

    if platform.system() != "Darwin":
        raise DraftError("review drafts require macOS / Messages.app")

    url = build_messages_url(recipient, message)
    subprocess.run(["open", url], check=True)
    return url


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Open a Messages.app/iMessage draft for human review only. "
            "This script never sends the message."
        )
    )
    parser.add_argument("--to", required=True, help="Phone number or Apple ID recipient")
    parser.add_argument(
        "--text",
        required=True,
        help="Draft message body. Quote multiline text in your shell as needed.",
    )
    parser.add_argument(
        "--print-url",
        action="store_true",
        help="Print the Messages URL without opening Messages.app.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.print_url:
            print(build_messages_url(args.to, args.text))
        else:
            open_review_draft(args.to, args.text)
            print("Opened Messages.app draft for review only; nothing was sent.")
        return 0
    except (DraftError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
