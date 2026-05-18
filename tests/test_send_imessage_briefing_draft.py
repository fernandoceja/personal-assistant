"""Tests for the explicit-gated iMessage briefing draft sender."""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "send-imessage-briefing-draft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("send_imessage_briefing_draft", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dry_run_does_not_call_osascript(tmp_path, capsys, monkeypatch):
    mod = _load_module()
    draft = tmp_path / "briefings" / "2026-05-18-09-imessage-draft.txt"
    draft.parent.mkdir()
    draft.write_text("Status: Review-only briefing draft. Nothing sent.\nPriority Now: No urgent source-backed items.\n", encoding="utf-8")
    called = False

    def fake_send(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(mod, "send_imessage", fake_send)

    assert mod.main([str(draft)]) == 0
    output = capsys.readouterr().out
    assert "Mode: DRY RUN — no iMessage sent." in output
    assert "Safety: osascript/Messages was not called." in output
    assert "Priority Now: No urgent source-backed items." in output
    assert called is False


def test_missing_recipient_with_send_flag_fails_safely(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    draft = tmp_path / "briefings" / "2026-05-18-09-imessage-draft.txt"
    draft.parent.mkdir()
    draft.write_text("Status: Review-only briefing draft. Nothing sent.\n", encoding="utf-8")
    monkeypatch.setattr(mod, "send_imessage", lambda *_args, **_kwargs: pytest.fail("send should not be called"))

    assert mod.main([str(draft), "--send-approved-draft"]) == 1
    err = capsys.readouterr().err
    assert "--recipient is required when --send-approved-draft is used" in err


def test_missing_draft_file_fails_safely(capsys):
    mod = _load_module()

    assert mod.main(["/tmp/definitely-missing-imessage-draft.txt"]) == 1
    err = capsys.readouterr().err
    assert "Draft file not found" in err


def test_latest_draft_selection_uses_newest_imessage_draft(tmp_path):
    mod = _load_module()
    briefings = tmp_path / "briefings"
    briefings.mkdir()
    older = briefings / "2026-05-18-07-imessage-draft.txt"
    newer = briefings / "2026-05-18-09-imessage-draft.txt"
    safe_packet = briefings / "2026-05-18-10-safe.md"
    final_briefing = briefings / "2026-05-18-10-final.md"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")
    safe_packet.write_text("safe packet", encoding="utf-8")
    final_briefing.write_text("final briefing", encoding="utf-8")

    assert mod.find_latest_draft(tmp_path) == newer


def test_send_function_is_not_invoked_without_explicit_flag(tmp_path, monkeypatch):
    mod = _load_module()
    draft = tmp_path / "briefings" / "2026-05-18-09-imessage-draft.txt"
    draft.parent.mkdir()
    draft.write_text("Status: Review-only briefing draft. Nothing sent.\n", encoding="utf-8")
    send_calls = []
    monkeypatch.setattr(mod, "send_imessage", lambda *_args, **_kwargs: send_calls.append("called"))

    assert mod.main([str(draft), "--recipient", "Fernando"]) == 0
    assert send_calls == []


def test_send_mode_requires_valid_safe_draft_content(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    draft = tmp_path / "briefings" / "2026-05-18-09-imessage-draft.txt"
    draft.parent.mkdir()
    draft.write_text("Status: Review-only briefing draft. Nothing sent.\nMessage ID: abc123\nhttps://example.invalid\n", encoding="utf-8")
    monkeypatch.setattr(mod, "send_imessage", lambda *_args, **_kwargs: pytest.fail("send should not be called"))

    assert mod.main([str(draft), "--send-approved-draft", "--recipient", "Fernando"]) == 1
    err = capsys.readouterr().err
    assert "Draft failed safety validation" in err


def test_send_mode_invokes_send_only_with_explicit_flag_and_recipient(tmp_path, monkeypatch):
    mod = _load_module()
    draft = tmp_path / "briefings" / "2026-05-18-09-imessage-draft.txt"
    draft.parent.mkdir()
    draft.write_text("Status: Review-only briefing draft. Nothing sent.\nPriority Now: No urgent source-backed items.\n", encoding="utf-8")
    send_calls = []
    monkeypatch.setattr(mod, "send_imessage", lambda recipient, message: send_calls.append((recipient, message)))

    assert mod.main([str(draft), "--send-approved-draft", "--recipient", "Fernando"]) == 0
    assert send_calls == [("Fernando", draft.read_text(encoding="utf-8").strip())]
