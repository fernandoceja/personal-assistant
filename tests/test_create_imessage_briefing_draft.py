"""Tests for the review-only iMessage briefing draft generator."""

from __future__ import annotations

import importlib.util
import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "create-imessage-briefing-draft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("create_imessage_briefing_draft", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_finds_latest_final_briefing(tmp_path):
    mod = _load_module()
    briefings = tmp_path / "briefings"
    briefings.mkdir()
    older = briefings / "2026-05-18-07-final.md"
    newer = briefings / "2026-05-18-09-final.md"
    safe_packet = briefings / "2026-05-18-10-safe.md"
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")
    safe_packet.write_text("safe packet", encoding="utf-8")

    assert mod.find_latest_final_briefing(tmp_path) == newer


def test_generates_short_safe_draft_without_raw_details():
    mod = _load_module()
    final_text = """
# Morning Briefing — 2026-05-18

## Executive Summary
- Combined Gmail + Calendar readonly briefing generated successfully.

## Priority Now
- Source: Gmail safe-list. Sender/Event: Apple. Subject: Schedule update. Timing: Today. Importance: work schedule changed. Next Action: review shift timing.

## Review With Me
- Source: Gmail safe-list. Sender/Event: USCIS. Subject: Case update. Timing: Review with me. Importance: immigration/legal topic. Next Action: verify details together. Message ID: abc123 https://example.invalid

## Calendar Watch
- 12:00 PM — Work shift — Apple Store.

## Low Priority
- Routine newsletters grouped.

## Ignore/Suspicious
- 2 suspicious/marketing items. Thread ID: thread-123 Attachment: invoice.pdf
"""

    draft = mod.build_draft(final_text)

    assert len(draft) <= 900
    assert "Status:" in draft
    assert "Priority Now:" in draft
    assert "Review With Me:" in draft
    assert "Calendar Watch:" in draft
    assert "Ignore/Suspicious:" in draft
    assert "Message ID" not in draft
    assert "Thread ID" not in draft
    assert "https://" not in draft
    assert "Attachment" not in draft


def test_output_path_uses_final_briefing_timestamp(tmp_path):
    mod = _load_module()
    final_path = tmp_path / "briefings" / "2026-05-18-09-final.md"
    final_path.parent.mkdir()
    final_path.write_text("## Priority Now\n- Nothing urgent.", encoding="utf-8")

    assert mod.output_path_for(final_path) == tmp_path / "briefings" / "2026-05-18-09-imessage-draft.txt"
