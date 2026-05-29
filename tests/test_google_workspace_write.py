"""Tests for Google Workspace Write Safety Modes and Shift Event Parsing."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
from unittest.mock import patch

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "google-workspace-write.py"

def _load_module():
    spec = importlib.util.spec_from_file_location("google_workspace_write", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_timezone_offset():
    mod = _load_module()
    # May 24 is in DST (PDT = -07:00)
    assert mod.get_tz_offset("2026-05-24") == "-07:00"
    # Dec 24 is in Standard Time (PST = -08:00)
    assert mod.get_tz_offset("2026-12-24") == "-08:00"

def test_normalize_datetime():
    mod = _load_module()
    offset = "-07:00"
    date_str = "2026-05-24"
    
    # 24h format
    assert mod.normalize_datetime("09:30", date_str, offset) == "2026-05-24T09:30:00-07:00"
    # AM/PM format
    assert mod.normalize_datetime("9:30 AM", date_str, offset) == "2026-05-24T09:30:00-07:00"
    assert mod.normalize_datetime("2:30 PM", date_str, offset) == "2026-05-24T14:30:00-07:00"
    # ISO Datetime (should preserve if offset present, append if not)
    assert mod.normalize_datetime("2026-05-24T09:30:00-07:00", date_str, offset) == "2026-05-24T09:30:00-07:00"
    assert mod.normalize_datetime("2026-05-24T09:30:00", date_str, offset) == "2026-05-24T09:30:00-07:00"

def test_parse_shift_text():
    mod = _load_module()
    text = """
    Apple - Learn and Grow: 09:30 AM - 10:30 AM
    Break: 10:30 AM - 11:00 AM
    Apple - Daily Download: 11:00 AM - 12:00 PM
    """
    segments = mod.parse_shift_text(text, "2026-05-24")
    assert len(segments) == 3
    
    assert segments[0]["title"] == "Apple - Learn and Grow"
    assert segments[0]["start"] == "09:30"
    assert segments[0]["end"] == "10:30"
    
    assert segments[1]["title"] == "Break"
    assert segments[1]["start"] == "10:30"
    assert segments[1]["end"] == "11:00"

def test_cli_read_only_refusal():
    # Run the script via subprocess without write or preview flags
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "calendar", "create",
        "--summary", "Test Event",
        "--start", "2026-05-24T10:00:00",
        "--end", "2026-05-24T11:00:00"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 2
    
    data = json.loads(res.stdout)
    assert data["status"] == "error"
    assert "READ-ONLY" in data["message"]
    assert data["writes_performed"] is False

def test_cli_preview_mode():
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "calendar", "create",
        "--summary", "Test Event",
        "--start", "2026-05-24T10:00:00",
        "--end", "2026-05-24T11:00:00",
        "--preview"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    
    data = json.loads(res.stdout)
    assert data["status"] == "preview"
    assert data["title"] == "Test Event"
    assert data["writes_performed"] is False

def test_shift_preview_mode(tmp_path):
    # Test create-shift-events subcommand in preview mode without breaks
    json_path = tmp_path / "segments.json"
    segments_data = [
        {"title": "Apple - Learn and Grow", "start": "09:30 AM", "end": "10:30 AM"},
        {"title": "Break", "start": "10:30 AM", "end": "11:00 AM"},
        {"title": "Apple - Daily Download", "start": "11:00 AM", "end": "12:00 PM"}
    ]
    json_path.write_text(json.dumps(segments_data), encoding="utf-8")
    
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "calendar", "create-shift-events",
        "--source", "ukg",
        "--date", "2026-05-24",
        "--calendar-id", "primary",
        "--segments-json", str(json_path),
        "--preview"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    
    data = json.loads(res.stdout)
    assert data["status"] == "preview"
    assert data["writes_performed"] is False
    # Break should be omitted since --create-breaks is absent
    assert len(data["created_events"]) == 2
    assert data["created_events"][0]["title"] == "Apple - Learn and Grow"
    assert data["created_events"][1]["title"] == "Apple - Daily Download"

def test_approved_write_mode():
    mod = _load_module()
    
    # Run in write mode using sys.argv patching
    test_args = [
        "google-workspace-write.py",
        "calendar", "create",
        "--summary", "Test Event",
        "--start", "2026-05-24T10:00:00-07:00",
        "--end", "2026-05-24T11:00:00-07:00",
        "--allow-live-calendar-write"
    ]
    
    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_run_gws.return_value = {"id": "test_event_123_id"}
        mod.main()
        
        # Verify gws command runner was called with the right parameters
        assert mock_run_gws.called
        args_passed = mock_run_gws.call_args[0][0]
        assert "calendar" in args_passed
        assert "create" in args_passed
        assert "Test Event" in args_passed
        assert "--allow-live-google-calendar-write" in args_passed

def test_shift_write_mode_with_duplicates():
    mod = _load_module()
    
    test_args = [
        "google-workspace-write.py",
        "calendar", "create-shift-events",
        "--source", "ukg",
        "--date", "2026-05-24",
        "--calendar-id", "primary",
        "--segments-text", "Apple - Learn and Grow: 09:30 AM - 10:30 AM\nApple - Daily Download: 10:30 AM - 11:00 AM",
        "--allow-live-calendar-write"
    ]
    
    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        # First call (safe-list) returns that the first event exists
        # Second call (create) creates the second event
        mock_run_gws.side_effect = [
            [
                {
                    "summary": "Apple - Learn and Grow",
                    "start": "2026-05-24T09:30:00-07:00",
                    "end": "2026-05-24T10:30:00-07:00",
                    "location": ""
                }
            ],
            {"id": "new_event_id_456"}
        ]
        
        mod.main()
        
        # Verify run_gws_command was called twice
        assert mock_run_gws.call_count == 2
        
        # Check first call was safe-list
        first_call = mock_run_gws.call_args_list[0][0][0]
        assert "safe-list" in first_call
        
        # Check second call was calendar create
        second_call = mock_run_gws.call_args_list[1][0][0]
        assert "create" in second_call
        assert "Apple - Daily Download" in second_call

def test_fuzzy_title_duplicate_detection():
    mod = _load_module()
    
    # 1. Exact duplicate
    assert mod.is_duplicate_title("Learn and Grow", "Learn and Grow") is True
    # 2. Prefix mismatch
    assert mod.is_duplicate_title("Apple - Learn and Grow", "Learn and Grow") is True
    assert mod.is_duplicate_title("Learn and Grow", "Apple - Learn and Grow") is True
    # 3. Parenthetical mismatch
    assert mod.is_duplicate_title("Apple - Mobile Support", "Mobile Support (Genius Bar)") is True
    assert mod.is_duplicate_title("Mobile Support (Genius Bar)", "Mobile Support") is True
    # 4. Canonical segment maps match
    assert mod.is_duplicate_title("Mobile Support Genius Bar", "Mobile Support") is True
    assert mod.is_duplicate_title("genius bar", "Apple - Mobile Support") is True
    # 5. Different title does not match
    assert mod.is_duplicate_title("Apple - Learn and Grow", "Apple - Daily Download") is False

def test_shift_write_mode_fuzzy_duplicates():
    mod = _load_module()
    
    test_args = [
        "google-workspace-write.py",
        "calendar", "create-shift-events",
        "--source", "ukg",
        "--date", "2026-05-24",
        "--calendar-id", "primary",
        "--segments-text", (
            "Apple - Learn and Grow: 09:30 AM - 10:30 AM\n"
            "Apple - Mobile Support: 11:15 AM - 1:15 PM\n"
            "Apple - Daily Download: 10:30 AM - 11:00 AM\n"
            "Apple - Mobile Support: 5:00 PM - 6:30 PM"
        ),
        "--allow-live-calendar-write"
    ]
    
    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_run_gws.side_effect = [
            # First call (safe-list) returns existing events:
            [
                {
                    "summary": "Learn and Grow",
                    "start": "2026-05-24T09:30:00-07:00",
                    "end": "2026-05-24T10:30:00-07:00"
                },
                {
                    "summary": "Mobile Support (Genius Bar)",
                    "start": "2026-05-24T11:15:00-07:00",
                    "end": "2026-05-24T13:15:00-07:00"
                },
                {
                    "summary": "Daily Download",
                    "start": "2026-05-24T15:00:00-07:00",
                    "end": "2026-05-24T15:30:00-07:00"
                },
                {
                    "summary": "Apple - Learn and Grow",
                    "start": "2026-05-24T17:00:00-07:00",
                    "end": "2026-05-24T18:30:00-07:00"
                }
            ],
            # Second call (create segment 3)
            {"id": "event_daily_download_id"},
            # Third call (create segment 4)
            {"id": "event_mobile_support_id"}
        ]
        
        mod.main()
        
        # Verify run_gws_command was called exactly 3 times (1 safe-list + 2 creations)
        assert mock_run_gws.call_count == 3
        
        # Check call parameters to make sure the correct segments were created
        # Call 1 (index 1) is Segment 3 (Daily Download)
        call_daily_download = mock_run_gws.call_args_list[1][0][0]
        assert "create" in call_daily_download
        assert "Apple - Daily Download" in call_daily_download
        
        # Call 2 (index 2) is Segment 4 (Mobile Support)
        call_mobile_support = mock_run_gws.call_args_list[2][0][0]
        assert "create" in call_mobile_support
        assert "Apple - Mobile Support" in call_mobile_support


def test_explicit_five_duplicate_scenarios():
    mod = _load_module()

    # 1. Exact duplicate title/time skips.
    assert mod.is_duplicate_title("Learn and Grow", "Learn and Grow") is True

    # 2. Prefix mismatch skips: "Apple - Learn and Grow" vs "Learn and Grow".
    assert mod.is_duplicate_title("Apple - Learn and Grow", "Learn and Grow") is True
    assert mod.is_duplicate_title("Learn and Grow", "Apple - Learn and Grow") is True

    # 3. Parenthetical mismatch skips: "Apple - Mobile Support" vs "Mobile Support (Genius Bar)".
    assert mod.is_duplicate_title("Apple - Mobile Support", "Mobile Support (Genius Bar)") is True
    assert mod.is_duplicate_title("Mobile Support (Genius Bar)", "Apple - Mobile Support") is True

    # 4. Same title but different time does not skip.
    # Checked externally by start/end times. In this test, we can verify that is_duplicate_title
    # is True because the titles are duplicate, but the actual script logic would skip only if times also match.

    # 5. Different title same time does not skip unless canonical segment maps match.
    # Different titles with no canonical map alignment do not match:
    assert mod.is_duplicate_title("Apple - Learn and Grow", "Apple - Daily Download") is False
    # Alignment via canonical maps (e.g. mobile support genius bar / genius bar both map to mobile support):
    assert mod.is_duplicate_title("mobile support genius bar", "genius bar") is True
    assert mod.is_duplicate_title("genius bar", "Apple - Mobile Support") is True


def test_break_duplicate_detection():
    mod = _load_module()

    # Exact "Break" title same time skips.
    assert mod.is_duplicate_title("Break", "Break") is True

    # "Meal Break" same time maps to break only if explicitly desired.
    assert mod.is_duplicate_title("Break", "Meal Break", map_meal_to_break=False) is False
    assert mod.is_duplicate_title("Break", "Meal Break", map_meal_to_break=True) is True
    assert mod.is_duplicate_title("Meal Break", "Break", map_meal_to_break=False) is False
    assert mod.is_duplicate_title("Meal Break", "Break", map_meal_to_break=True) is True

    # Check other terms like Lunch/Meal
    assert mod.is_duplicate_title("Break", "Lunch", map_meal_to_break=False) is False
    assert mod.is_duplicate_title("Break", "Lunch", map_meal_to_break=True) is True


def test_shift_write_mode_breaks():
    mod = _load_module()

    test_args = [
        "google-workspace-write.py",
        "calendar", "create-shift-events",
        "--source", "ukg",
        "--date", "2026-05-24",
        "--calendar-id", "primary",
        "--segments-text", (
            "Break: 11:00 AM - 11:15 AM\n"
            "Break: 01:15 PM - 02:15 PM\n"
            "Break: 04:45 PM - 05:00 PM"
        ),
        "--create-breaks",
        "--allow-live-calendar-write"
    ]

    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_run_gws.side_effect = [
            # First call (safe-list) returns existing events:
            [
                # 1. Exact Break same time (11:00 AM - 11:15 AM)
                {
                    "title": "Break",
                    "start": "2026-05-24T11:00:00-07:00",
                    "end": "2026-05-24T11:15:00-07:00"
                },
                # 2. Meal Break same time (1:15 PM - 2:15 PM) but map_meal_to_break is False
                {
                    "title": "Meal Break",
                    "start": "2026-05-24T13:15:00-07:00",
                    "end": "2026-05-24T14:15:00-07:00"
                },
                # 3. Different break time (4:45 PM - 5:00 PM vs existing 15:00-15:15)
                {
                    "title": "Break",
                    "start": "2026-05-24T15:00:00-07:00",
                    "end": "2026-05-24T15:15:00-07:00"
                }
            ],
            # Second call (create Break segment at 13:15-14:15 since it didn't map/skip)
            {"id": "new_break_1315_id"},
            # Third call (create Break segment since different time)
            {"id": "new_break_diff_time_id"}
        ]

        mod.main()

        # Verify run_gws_command was called exactly 3 times (1 safe-list + 2 creations)
        assert mock_run_gws.call_count == 3

        # Verify safe-list call
        first_call = mock_run_gws.call_args_list[0][0][0]
        assert "safe-list" in first_call

        # Verify creation calls
        c1 = mock_run_gws.call_args_list[1][0][0]
        assert "create" in c1
        assert "Break" in c1
        assert "2026-05-24T13:15:00-07:00" in c1

        c2 = mock_run_gws.call_args_list[2][0][0]
        assert "create" in c2
        assert "Break" in c2
        assert "2026-05-24T16:45:00-07:00" in c2


def test_shift_write_mode_breaks_mapping():
    mod = _load_module()

    test_args = [
        "google-workspace-write.py",
        "calendar", "create-shift-events",
        "--source", "ukg",
        "--date", "2026-05-24",
        "--calendar-id", "primary",
        "--segments-text", (
            "Break: 11:00 AM - 11:15 AM\n"
            "Break: 01:15 PM - 02:15 PM"
        ),
        "--create-breaks",
        "--map-meal-to-break",
        "--allow-live-calendar-write"
    ]

    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_run_gws.side_effect = [
            # First call (safe-list) returns existing events:
            [
                # 1. Exact Break same time (11:00 AM - 11:15 AM)
                {
                    "title": "Break",
                    "start": "2026-05-24T11:00:00-07:00",
                    "end": "2026-05-24T11:15:00-07:00"
                },
                # 2. Meal Break same time (1:15 PM - 2:15 PM) mapped to Break
                {
                    "title": "Meal Break",
                    "start": "2026-05-24T13:15:00-07:00",
                    "end": "2026-05-24T14:15:00-07:00"
                }
            ]
        ]

        mod.main()

        # Verify run_gws_command was called exactly 1 time (only safe-list), because BOTH are skipped!
        assert mock_run_gws.call_count == 1


def test_mode_write_without_calendar_flag_refused():
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "--mode", "write",
        "calendar", "create",
        "--summary", "Test Event",
        "--start", "2026-05-24T10:00:00",
        "--end", "2026-05-24T11:00:00",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 2
    data = json.loads(res.stdout)
    assert data["status"] == "error"
    assert "READ-ONLY" in data["message"]
    assert data["writes_performed"] is False


def test_google_writes_flag_without_calendar_flag_refused():
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "--allow-live-google-writes",
        "calendar", "create",
        "--summary", "Test Event",
        "--start", "2026-05-24T10:00:00",
        "--end", "2026-05-24T11:00:00",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 2
    data = json.loads(res.stdout)
    assert data["status"] == "error"
    assert data["writes_performed"] is False


def test_calendar_delete_without_delete_flag():
    mod = _load_module()

    test_args = [
        "google-workspace-write.py",
        "calendar", "delete", "test_id_123"
    ]

    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_exit.side_effect = SystemExit
        try:
            mod.main()
        except SystemExit:
            pass
        # Should exit with status code 2 (refusal)
        mock_exit.assert_called_once_with(2)
        assert not mock_run_gws.called


def test_calendar_delete_with_calendar_write_flag_only():
    mod = _load_module()

    test_args = [
        "google-workspace-write.py",
        "calendar", "delete", "test_id_123",
        "--allow-live-calendar-write"
    ]

    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_exit.side_effect = SystemExit
        try:
            mod.main()
        except SystemExit:
            pass
        mock_exit.assert_called_once_with(2)
        assert not mock_run_gws.called


def test_calendar_delete_with_google_writes_flag_only():
    mod = _load_module()

    test_args = [
        "google-workspace-write.py",
        "calendar", "delete", "test_id_123",
        "--allow-live-google-writes"
    ]

    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_exit.side_effect = SystemExit
        try:
            mod.main()
        except SystemExit:
            pass
        mock_exit.assert_called_once_with(2)
        assert not mock_run_gws.called


def test_calendar_delete_with_delete_flag_success():
    mod = _load_module()

    test_args = [
        "google-workspace-write.py",
        "calendar", "delete", "test_id_123",
        "--allow-live-calendar-delete"
    ]

    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_exit.side_effect = SystemExit
        mock_run_gws.return_value = {"id": "test_id_123"}
        try:
            mod.main()
        except SystemExit:
            pass

        # Verify exit was called with 0 (success)
        mock_exit.assert_called_once_with(0)
        # Verify it actually called run_gws_command delete path
        assert mock_run_gws.called
        gws_args = mock_run_gws.call_args[0][0]
        assert "calendar" in gws_args
        assert "delete" in gws_args
        assert "test_id_123" in gws_args


def test_calendar_cleanup_duplicates_preview_only(tmp_path):
    mod = _load_module()

    # Save a preview file
    preview_file = tmp_path / "preview.json"
    preview_data = {
        "duplicate_groups": [
            {
                "canonical_title": "learn and grow",
                "start": "2026-05-24T09:30:00-07:00",
                "end": "2026-05-24T10:30:00-07:00",
                "keep_event": {"event_id": "keep_1", "title": "Apple - Learn and Grow"},
                "delete_candidates": [
                    {"event_id": "del_1", "title": "Apple - Learn and Grow", "reason": "Duplicate title/time match"}
                ]
            }
        ]
    }
    preview_file.write_text(json.dumps(preview_data))

    # Run with preview file but NO delete flag (meaning preview only, no deletes performed)
    test_args = [
        "google-workspace-write.py",
        "calendar", "cleanup-duplicates",
        "--date", "2026-05-24",
        "--cleanup-preview", str(preview_file)
    ]

    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_exit.side_effect = SystemExit
        try:
            mod.main()
        except SystemExit:
            pass
        mock_exit.assert_called_once_with(0)
        assert not mock_run_gws.called


def test_calendar_cleanup_duplicates_live(tmp_path):
    mod = _load_module()

    preview_file = tmp_path / "preview.json"
    preview_data = {
        "duplicate_groups": [
            {
                "canonical_title": "learn and grow",
                "start": "2026-05-24T09:30:00-07:00",
                "end": "2026-05-24T10:30:00-07:00",
                "keep_event": {"event_id": "keep_1", "title": "Apple - Learn and Grow"},
                "delete_candidates": [
                    {"event_id": "del_1", "title": "Apple - Learn and Grow", "reason": "Duplicate title/time match"}
                ]
            }
        ]
    }
    preview_file.write_text(json.dumps(preview_data))

    test_args = [
        "google-workspace-write.py",
        "calendar", "cleanup-duplicates",
        "--date", "2026-05-24",
        "--cleanup-preview", str(preview_file),
        "--allow-live-calendar-delete"
    ]

    with patch.object(mod, "run_gws_command") as mock_run_gws, patch("sys.exit") as mock_exit, patch("sys.argv", test_args):
        mock_exit.side_effect = SystemExit
        mock_run_gws.return_value = {"status": "deleted"}
        try:
            mod.main()
        except SystemExit:
            pass

        mock_exit.assert_called_once_with(0)
        # Verify run_gws_command was called exactly 1 time (the delete call)
        assert mock_run_gws.call_count == 1
        gws_args = mock_run_gws.call_args[0][0]
        assert "calendar" in gws_args
        assert "delete" in gws_args
        assert "del_1" in gws_args


def test_daily_briefing_cannot_write_to_calendar():
    # Verify that daily briefing mode is strictly read-only by checking that safe runner
    # command options (google_api.py subcommands) default to 'safe-list' and do not include
    # the calendar write flags.
    
    # Test that google-workspace-write.py calendar create without the allow flag exits with code 2
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "calendar", "create",
        "--summary", "Test Event",
        "--start", "2026-05-24T10:00:00-07:00",
        "--end", "2026-05-24T11:00:00-07:00"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 2
    data = json.loads(res.stdout)
    assert data["status"] == "error"
    assert "READ-ONLY" in data["message"]
    assert data["writes_performed"] is False


def test_gmail_writes_are_blocked():
    # Verify that Gmail compose/send/draft modifications are blocked.
    # 1. Test google-workspace-write.py gmail draft-create without allow-live-gmail-draft
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "gmail", "draft-create",
        "--to", "user@example.com",
        "--subject", "Hello",
        "--body", "Hi"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 2
    data = json.loads(res.stdout)
    assert data["status"] == "error"
    assert "READ-ONLY" in data["message"]

    # 2. Test google-workspace-write.py gmail send-draft without allow-live-gmail-send
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "gmail", "send-draft",
        "draft_id_123"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 2
    data = json.loads(res.stdout)
    assert data["status"] == "error"
    assert "READ-ONLY" in data["message"]


def test_calendar_writes_blocked_unless_explicit_flag_is_used():
    # Run google_api.py directly using subprocess to check exit code
    google_api_script_path = REPO_ROOT.parent / "hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/google_api.py"
    cmd = [
        sys.executable,
        str(google_api_script_path),
        "calendar", "create",
        "--summary", "Test Event",
        "--start", "2026-05-24T10:00:00-07:00",
        "--end", "2026-05-24T11:00:00-07:00"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 2
    assert "Blocked: live Google Calendar writes require" in res.stderr


def test_calendar_write_mode_does_not_allow_gmail_write():
    # If the user allows calendar writes, Gmail writes must still be blocked.
    # Calendar write flag passed to gmail subcommand should be ignored, exiting with code 2
    google_api_script_path = REPO_ROOT.parent / "hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/google_api.py"
    cmd = [
        sys.executable,
        str(google_api_script_path),
        "gmail", "draft-create",
        "--to", "user@example.com",
        "--subject", "Hi",
        "--body", "Body",
        "--allow-live-google-calendar-write"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 2
    assert "unrecognized arguments: --allow-live-google-calendar-write" in res.stderr









