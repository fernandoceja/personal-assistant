#!/usr/bin/env python3
"""Reference-only Gmail safe-list connector patch.

This file is preserved as a docs patch artifact. It is not installed and should
not be called against live Gmail until separate approval is granted.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from typing import Any

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SAFE_HEADERS = ["From", "Subject", "Date"]
GMAIL_SAFE_LIST_FIELDS = "messages(id),nextPageToken"
GMAIL_SAFE_GET_FIELDS = "id,threadId,payload(headers(name,value)),snippet,labelIds,internalDate"
SNIPPET_LIMIT = 200
SUBJECT_LIMIT = 180
MAX_WINDOW_HOURS = 48
MAX_PER_FILTER_LIMIT = 10

ALLOWED_OUTPUT_FIELDS = [
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
}
SAFE_FILTERS = [
    {
        "name": "immigration_legal",
        "category": "Immigration / USCIS / legal",
        "query": '(from:uscis.gov OR subject:(USCIS OR immigration OR legal))',
        "triage_hint": "Review With Me",
    },
    {
        "name": "work_apple",
        "category": "Work / Apple",
        "query": '(from:apple.com OR subject:(schedule OR coverage OR shift))',
        "triage_hint": "Priority Now",
    },
    {
        "name": "school_umgc",
        "category": "School / UMGC",
        "query": '(from:umgc.edu OR subject:(assignment OR deadline OR advising))',
        "triage_hint": "Priority Now",
    },
    {
        "name": "bills_finance_security",
        "category": "Bills / finances / security",
        "query": 'subject:(payment OR due OR security OR alert OR statement OR tax OR fraud)',
        "triage_hint": "Review With Me",
    },
    {
        "name": "suspicious_phishing",
        "category": "Suspicious/phishing",
        "query": 'subject:(urgent OR verify OR suspended OR legal OR banking)',
        "triage_hint": "Ignore/Suspicious",
    },
]


def parse_window_hours(window: str) -> int:
    match = re.fullmatch(r"(\d+)h", window.strip())
    if not match:
        raise ValueError("window must use an hour suffix, for example 48h")
    hours = int(match.group(1))
    if hours < 1 or hours > MAX_WINDOW_HOURS:
        raise ValueError(f"window must be between 1h and {MAX_WINDOW_HOURS}h")
    return hours


def gmail_after_query(window: str, now: datetime | None = None) -> str:
    hours = parse_window_hours(window)
    current = now or datetime.now(timezone.utc)
    after = current - timedelta(hours=hours)
    return f"after:{after.strftime('%Y/%m/%d')} newer_than:{hours}h"


def headers_dict(message: dict[str, Any]) -> dict[str, str]:
    headers = message.get("payload", {}).get("headers", [])
    safe = {}
    for header in headers:
        name = str(header.get("name", ""))
        if name in GMAIL_SAFE_HEADERS:
            safe[name] = str(header.get("value", ""))
    return safe


def sender_parts(from_header: str) -> tuple[str, str]:
    display, address = parseaddr(from_header)
    domain = ""
    if "@" in address:
        domain = address.rsplit("@", 1)[1].lower()
    return display or address or "unknown", domain


def cap_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def safe_labels(label_ids: Any) -> list[str]:
    if not isinstance(label_ids, list):
        return []
    return [label for label in label_ids if label in ALLOWED_LABELS]


def normalize_message(message: dict[str, Any], filter_def: dict[str, str]) -> dict[str, Any]:
    headers = headers_dict(message)
    sender_display, sender_domain = sender_parts(headers.get("From", ""))
    record = {
        "source": "gmail_readonly",
        "category": filter_def["category"],
        "sender_display": cap_text(sender_display, 120),
        "sender_domain": cap_text(sender_domain, 120),
        "subject": cap_text(headers.get("Subject", ""), SUBJECT_LIMIT),
        "received_at": cap_text(headers.get("Date", ""), 80),
        "snippet": cap_text(message.get("snippet", ""), SNIPPET_LIMIT),
        "labels": safe_labels(message.get("labelIds", [])),
        "has_attachment": "unknown",
        "matched_filter": filter_def["name"],
        "triage_hint": filter_def["triage_hint"],
        "safety_notes": "Read-only metadata record; IDs, bodies, raw payloads, and attachment details omitted.",
    }
    return {field: record[field] for field in ALLOWED_OUTPUT_FIELDS}


def gmail_safe_list(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Safe-list implementation sketch.

    Expected service calls:
    - users.messages.list(userId="me", q=<recency-limited query>, maxResults=N,
      fields="messages(id),nextPageToken") for candidate IDs only.
    - users.messages.get(userId="me", id=<candidate>, format="metadata",
      metadataHeaders=["From", "Subject", "Date"], fields=<safe mask>) for safe metadata.

    This reference intentionally requires an injected service object so importing
    or syntax-checking it cannot authenticate or touch live Gmail.
    """
    service = getattr(args, "service", None)
    if service is None:
        raise RuntimeError("Reference artifact only: inject an approved Gmail service before live use")

    max_per_filter = max(1, min(int(args.max_per_filter), MAX_PER_FILTER_LIMIT))
    recency = gmail_after_query(args.window)
    output: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for filter_def in SAFE_FILTERS:
        query = f"{recency} {filter_def['query']}"
        candidates = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_per_filter,
            fields=GMAIL_SAFE_LIST_FIELDS,
        ).execute()
        for candidate in candidates.get("messages", []):
            message_id = candidate.get("id")
            if not message_id or message_id in seen_ids:
                continue
            seen_ids.add(message_id)
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=GMAIL_SAFE_HEADERS,
                fields=GMAIL_SAFE_GET_FIELDS,
            ).execute()
            output.append(normalize_message(message, filter_def))

    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Reference Gmail read-only safe-list command")
    sub = parser.add_subparsers(dest="service", required=True)

    gmail = sub.add_parser("gmail")
    gmail_sub = gmail.add_subparsers(dest="action", required=True)

    safe = gmail_sub.add_parser("safe-list", help="Gmail read-only metadata safe-list")
    safe.add_argument("--window", default="48h", help="Recency window; maximum 48h")
    safe.add_argument("--max-per-filter", type=int, default=10)
    safe.set_defaults(func=gmail_safe_list)

    args = parser.parse_args()
    records = args.func(args)
    print(json.dumps(records, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
