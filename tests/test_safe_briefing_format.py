"""Tests for safe briefing final formatting."""

from __future__ import annotations

import json
import pathlib
import subprocess


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMATTER = REPO_ROOT / "scripts" / "format-safe-briefing.sh"
REQUIRED_HEADINGS = [
    "Executive Summary",
    "Priority Now",
    "Review With Me",
    "Calendar Watch",
    "Low Priority",
    "Ignore/Suspicious",
]


def run_formatter(tmp_path: pathlib.Path, source_text: str) -> str:
    source = tmp_path / "packet-safe.md"
    output = tmp_path / "packet-final.md"
    source.write_text(source_text, encoding="utf-8")
    subprocess.run(
        ["bash", str(FORMATTER), "--input", str(source), "--output", str(output)],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return output.read_text(encoding="utf-8")


def headings(final_text: str) -> list[str]:
    return [line.removeprefix("## ").strip() for line in final_text.splitlines() if line.startswith("## ")]


def gmail_packet(records: list[dict]) -> str:
    return "\n".join(
        [
            "# Safe Morning Assistant Input Packet",
            "## Gmail Mock Safe-List",
            "GMAIL_MOCK_SAFE_LIST_JSON_BEGIN",
            json.dumps(records),
            "GMAIL_MOCK_SAFE_LIST_JSON_END",
        ]
    )


def test_final_briefing_contains_exact_required_headings(tmp_path):
    final = run_formatter(tmp_path, "# Safe Packet\n\n## Gmail Non-Live Placeholder\nGmail live data not accessed.\n")

    assert headings(final) == REQUIRED_HEADINGS


def test_gmail_safe_list_does_not_expose_raw_bodies_or_tokens(tmp_path):
    records = [
        {
            "source": "gmail_readonly",
            "category": "School / UMGC",
            "sender_display": "UMGC",
            "sender_domain": "umgc.edu",
            "subject": "Student account statement",
            "received_at": "Today",
            "snippet": "raw private body access_token=ya29.secret-value threadId abc123",
            "triage_hint": "Review With Me",
            "body": "this raw body must never appear",
            "threadId": "thread-123",
        }
    ]
    final = run_formatter(tmp_path, gmail_packet(records))

    assert "this raw body" not in final
    assert "raw private body" not in final
    assert "thread-123" not in final
    assert "ya29." not in final
    assert "access_token" not in final


def test_no_calendar_claim_when_sources_return_no_events(tmp_path):
    packet = "\n".join(
        [
            "# Safe Packet",
            "## Local Apple Calendar Diagnostics",
            "Permission/status: granted — Calendar.app read completed.",
            "Result: preferred calendars found, but no events were found for today/tomorrow.",
            "## Google Calendar Readonly Diagnostics",
            "Result: success — Google Calendar readonly safe-list completed.",
            "[]",
        ]
    )
    final = run_formatter(tmp_path, packet)

    assert "no today/tomorrow events were found" in final.lower()
    assert "returned today/tomorrow items" not in final


def test_uncertain_school_money_legal_security_route_to_review(tmp_path):
    records = [
        {"category": "School / UMGC", "sender_display": "UMGC", "sender_domain": "umgc.edu", "subject": "Financial aid statement", "received_at": "Today", "snippet": "", "triage_hint": "Low Priority"},
        {"category": "Finances / BofA", "sender_display": "Bank", "sender_domain": "bank.example", "subject": "Balance alert", "received_at": "Today", "snippet": "", "triage_hint": "Low Priority"},
        {"category": "Immigration / USCIS / legal", "sender_display": "USCIS", "sender_domain": "uscis.gov", "subject": "Case update", "received_at": "Today", "snippet": "", "triage_hint": "Low Priority"},
    ]
    final = run_formatter(tmp_path, gmail_packet(records))
    review = final.split("## Review With Me", 1)[1].split("## Calendar Watch", 1)[0]

    assert "Category: school" in review
    assert "Category: money" in review
    assert "Category: legal/immigration" in review
    assert "Why this matters:" in review
    assert "What to verify:" in review
    assert "Conservative next action:" in review


def test_unknown_billing_security_sender_routes_to_ignore_suspicious(tmp_path):
    records = [
        {
            "category": "Suspicious/phishing",
            "sender_display": "Unknown sender",
            "sender_domain": "",
            "subject": "Urgent billing security verification",
            "received_at": "Today",
            "snippet": "verify your account",
            "triage_hint": "Review With Me",
        }
    ]
    final = run_formatter(tmp_path, gmail_packet(records))
    suspicious = final.split("## Ignore/Suspicious", 1)[1]

    assert "Urgent billing security verification" in suspicious
    assert "## Review With Me\nNo source-backed items" in final
