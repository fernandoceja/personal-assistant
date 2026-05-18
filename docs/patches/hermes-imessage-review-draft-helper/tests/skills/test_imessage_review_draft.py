"""Tests for the iMessage review-only draft helper."""

from __future__ import annotations

import importlib.util
import pathlib

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "skills" / "apple" / "imessage" / "scripts" / "review_draft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("imessage_review_draft", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_messages_url_encodes_recipient_and_body():
    mod = _load_module()

    url = mod.build_messages_url("+14155551212", "Hello Fernando & family")

    assert url == "sms://open?addresses=+14155551212&body=Hello%20Fernando%20%26%20family"


def test_build_messages_url_allows_apple_id_recipient():
    mod = _load_module()

    url = mod.build_messages_url("person@example.com", "Line 1\nLine 2")

    assert url == "sms://open?addresses=person@example.com&body=Line%201%0ALine%202"


def test_build_messages_url_rejects_missing_message():
    mod = _load_module()

    with pytest.raises(mod.DraftError, match="message text is required"):
        mod.build_messages_url("+14155551212", "   ")


def test_build_messages_url_rejects_multiline_recipient():
    mod = _load_module()

    with pytest.raises(mod.DraftError, match="single line"):
        mod.build_messages_url("+14155551212\n+14155559999", "Hello")


def test_print_url_mode_does_not_open_messages(monkeypatch, capsys):
    mod = _load_module()

    def fail_if_called(*args, **kwargs):  # pragma: no cover - failure path
        raise AssertionError("open should not be called in --print-url mode")

    monkeypatch.setattr(mod.subprocess, "run", fail_if_called)

    status = mod.main(["--to", "+14155551212", "--text", "Review me", "--print-url"])

    assert status == 0
    assert capsys.readouterr().out.strip() == "sms://open?addresses=+14155551212&body=Review%20me"
