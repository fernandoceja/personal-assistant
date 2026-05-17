#!/usr/bin/env python3
"""Mock-only Gmail safe-list fixture reader.

This script intentionally never authenticates, reads token files, calls Gmail APIs,
or opens live email clients. It only loads the checked-in mock fixture and emits
already-normalized safe-list records.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT_DIR / "fixtures" / "gmail-safe-list-mock.json"
ALLOWED_FIELDS = [
    "source",
    "category",
    "sender_display",
    "sender_domain",
    "subject",
    "received_at",
    "snippet",
    "labels",
    "has_attachment",
    "matched_filter",
    "triage_hint",
    "safety_notes",
]
ALLOWED_LABELS = {
    "INBOX",
    "UNREAD",
    "STARRED",
    "IMPORTANT",
    "SENT",
    "DRAFT",
    "SPAM",
    "TRASH",
    "CATEGORY_PERSONAL",
    "CATEGORY_SOCIAL",
    "CATEGORY_PROMOTIONS",
    "CATEGORY_UPDATES",
    "CATEGORY_FORUMS",
    "MOCK_SAFE",
}
ALLOWED_TRIAGE = {
    "Priority Now",
    "Review With Me",
    "Calendar Watch",
    "Low Priority",
    "Ignore/Suspicious",
}


def _safe_bool_or_unknown(value):
    if isinstance(value, bool):
        return value
    return "unknown"


def normalize_record(record: dict) -> dict:
    normalized = {field: record.get(field, "") for field in ALLOWED_FIELDS}
    normalized["source"] = "gmail_mock"
    normalized["snippet"] = str(normalized.get("snippet", ""))[:200]
    labels = normalized.get("labels", [])
    if not isinstance(labels, list):
        labels = []
    normalized["labels"] = [label for label in labels if label in ALLOWED_LABELS]
    normalized["has_attachment"] = _safe_bool_or_unknown(normalized.get("has_attachment"))
    if normalized.get("triage_hint") not in ALLOWED_TRIAGE:
        normalized["triage_hint"] = "Review With Me"
    return normalized


def validate_no_extra_fields(records: list[dict]) -> None:
    allowed = set(ALLOWED_FIELDS)
    for index, record in enumerate(records, start=1):
        extra = sorted(set(record) - allowed)
        if extra:
            raise ValueError(f"fixture record {index} contains excluded field(s): {', '.join(extra)}")


def safe_list(args: argparse.Namespace) -> int:
    if not args.mock:
        print("ERROR: live Gmail safe-list is not implemented; rerun with --mock.", file=sys.stderr)
        return 2
    if args.window != "48h":
        print("ERROR: mock safe-list currently supports --window 48h only.", file=sys.stderr)
        return 2

    fixture = Path(args.fixture).resolve()
    records = json.loads(fixture.read_text())
    if not isinstance(records, list):
        raise ValueError("fixture must be a JSON list")
    validate_no_extra_fields(records)
    normalized = [normalize_record(record) for record in records]
    limit = max(0, args.max_per_filter)
    if limit:
        normalized = normalized[: limit * 10]

    print(json.dumps(normalized, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Mock-only Gmail safe-list fixture reader")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("safe-list", help="Emit normalized mock Gmail safe-list records")
    p.add_argument("--mock", action="store_true", help="Required; live Gmail is not implemented")
    p.add_argument("--window", default="48h", help="Mock window; currently supports 48h")
    p.add_argument("--max-per-filter", type=int, default=10)
    p.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    p.set_defaults(func=safe_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
