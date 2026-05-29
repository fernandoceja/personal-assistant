#!/usr/bin/env python3
"""Google Workspace Write utility for Hermes / Personal Assistant.

Supports three safety modes:
1. Safe Read-Only (Mode 1): Default. Refuses all write actions.
2. Draft/Preview Mode (Mode 2): Generates proposed actions/JSON. No live writes.
3. Approved Write Mode (Mode 3): Requires explicit write approval flags. Performs live writes.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

# Core Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
HERMES_AGENT_TEST_DIR = Path(
    os.environ.get("HERMES_AGENT_TEST_DIR", os.path.expanduser("~/Projects/hermes-agent-test"))
)
GOOGLE_HERMES_HOME = HERMES_AGENT_TEST_DIR / "home/.hermes"
DEFAULT_PYTHON = GOOGLE_HERMES_HOME / "venvs/google-workspace/bin/python"
DEFAULT_GOOGLE_API = GOOGLE_HERMES_HOME / "skills/productivity/google-workspace/scripts/google_api.py"
LOGS_DIR = REPO_ROOT / "logs"
WRITE_LOG_FILE = LOGS_DIR / "google-workspace-writes.log"

def get_tz_offset(date_str: str, tz_name: str = "America/Los_Angeles") -> str:
    """Calculate the timezone offset (+/-HH:MM) for a specific date in tz_name."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
        offset = dt.utcoffset()
        if offset is None:
            return "-07:00"
        total_seconds = int(offset.total_seconds())
        sign = "+" if total_seconds >= 0 else "-"
        minutes = abs(total_seconds) // 60
        hours = minutes // 60
        minutes = minutes % 60
        return f"{sign}{hours:02d}:{minutes:02d}"
    except Exception:
        return "-07:00"

def normalize_datetime(dt_str: str, date_str: str, offset: str) -> str:
    """Normalize plain times or datetimes to full ISO 8601 with timezone offset."""
    dt_str = dt_str.strip()
    
    # 1. Plain 24h time like "09:30" or "09:30:00"
    time_match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", dt_str)
    if time_match:
        h = int(time_match.group(1))
        m = int(time_match.group(2))
        s = int(time_match.group(3)) if time_match.group(3) else 0
        return f"{date_str}T{h:02d}:{m:02d}:{s:02d}{offset}"
    
    # 2. Time with AM/PM like "09:30 AM" or "9:30 PM"
    time_ampm_match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)", dt_str)
    if time_ampm_match:
        h = int(time_ampm_match.group(1))
        m = int(time_ampm_match.group(2))
        pm = time_ampm_match.group(3).upper() == "PM"
        if pm and h < 12:
            h += 12
        elif not pm and h == 12:
            h = 0
        return f"{date_str}T{h:02d}:{m:02d}:00{offset}"
    
    # 3. ISO Datetime
    if "T" in dt_str:
        if dt_str.endswith("Z"):
            return dt_str
        tail = dt_str.split("T")[1]
        if "+" in tail or "-" in tail:
            return dt_str
        return dt_str + offset
        
    return dt_str

def parse_shift_text(text: str, date_str: str) -> list[dict]:
    """Parse work segments and breaks from raw OCR / manual text."""
    segments = []
    lines = text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Search for a time range in the line
        pattern = r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)?\s*[-–—to\s]+\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)?"
        match = re.search(pattern, line)
        if match:
            sh_str, sm_str, smid, eh_str, em_str, emid = match.groups()
            start_idx, end_idx = match.span()
            
            # Title is the rest of the text
            title = line[:start_idx] + line[end_idx:]
            title = re.sub(r"\b[pP][sS][tT]\b", "", title)  # Strip timezone references
            title = title.strip(" :(),;-–—")
            if not title:
                title = "Work Segment"
            
            sh = int(sh_str)
            sm = int(sm_str) if sm_str else 0
            eh = int(eh_str)
            em = int(em_str) if em_str else 0
            
            # Infer meridians
            s_pm = False
            e_pm = False
            
            if smid:
                s_pm = smid.upper() == "PM"
            if emid:
                e_pm = emid.upper() == "PM"
                
            if smid and not emid:
                if eh < sh:
                    e_pm = not s_pm
                else:
                    e_pm = s_pm
            elif emid and not smid:
                if sh > eh:
                    s_pm = not e_pm
                else:
                    s_pm = e_pm
            elif not smid and not emid:
                s_pm = (sh < 7 or sh == 12)
                e_pm = (eh < 7 or eh == 12)
                
            if s_pm and sh < 12:
                sh += 12
            elif not s_pm and sh == 12:
                sh = 0
                
            if e_pm and eh < 12:
                eh += 12
            elif not e_pm and eh == 12:
                eh = 0
                
            segments.append({
                "title": title,
                "start": f"{sh:02d}:{sm:02d}",
                "end": f"{eh:02d}:{em:02d}"
            })
    return segments

def load_segments_json(path: str) -> list[dict]:
    """Load and return structured segments from a JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["segments", "events", "shift_segments", "items"]:
            if key in data and isinstance(data[key], list):
                return data[key]
    raise ValueError("Invalid segments JSON structure")

def canonicalize_title(title: str) -> str:
    """Normalize event titles to support slightly mismatched duplicates."""
    title = title.lower()
    # Remove prefix "apple - " or "apple -"
    title = re.sub(r"^apple\s*-\s*", "", title)
    # Remove parenthetical location/team text like "(genius bar)"
    title = re.sub(r"\(.*?\)", "", title)
    # Replace common symbols
    title = title.replace("&", "and")
    # Clean spaces
    title = " ".join(title.split()).strip()
    
    canonical_maps = {
        "mobile support genius bar": "mobile support",
        "genius bar": "mobile support",
        "learn & grow": "learn and grow",
        "learn and grow": "learn and grow",
        "daily download": "daily download",
        "break": "break",
    }
    if title in canonical_maps:
        title = canonical_maps[title]
    return title

def is_duplicate_title(t1: str, t2: str, map_meal_to_break: bool = False) -> bool:
    """Compare two event titles using normalized and contains logic."""
    c1 = canonicalize_title(t1)
    c2 = canonicalize_title(t2)
    if not c1 or not c2:
        return False

    # Normalize meals/lunch if explicitly requested
    if map_meal_to_break:
        if c1 in ["meal break", "meal", "lunch"] or c1.startswith("meal"):
            c1 = "break"
        if c2 in ["meal break", "meal", "lunch"] or c2.startswith("meal"):
            c2 = "break"

    if c1 == c2:
        return True

    # Avoid "Break" mapping to "Meal Break" (and vice versa) via contains check
    # unless map_meal_to_break is explicitly True.
    is_break_1 = (c1 == "break")
    is_break_2 = (c2 == "break")
    is_meal_1 = (c1 in ["meal break", "meal", "lunch"] or c1.startswith("meal"))
    is_meal_2 = (c2 in ["meal break", "meal", "lunch"] or c2.startswith("meal"))

    if (is_break_1 and is_meal_2) or (is_break_2 and is_meal_1):
        return map_meal_to_break

    if c1 in c2 or c2 in c1:
        return True
    return False

def log_write(action: str, details: dict):
    """Write an audit log entry for any successful write operation."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "action": action,
        "details": details
    }
    with open(WRITE_LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def service_write_approved(args) -> bool:
    """Return True only when the command has the matching service-specific live gate."""
    if args.service == "calendar":
        if args.action in ["delete", "cleanup-duplicates"]:
            return bool(getattr(args, "allow_live_calendar_delete", False))
        return bool(getattr(args, "allow_live_calendar_write", False))
    if args.service == "gmail":
        if args.action == "draft-create":
            return bool(getattr(args, "allow_live_gmail_draft", False))
        if args.action == "send-draft":
            return bool(getattr(args, "allow_live_gmail_send", False))
        return False
    if args.service == "docs":
        return bool(getattr(args, "allow_live_docs_write", False))
    if args.service == "sheets":
        return bool(getattr(args, "allow_live_sheets_write", False))
    if args.service == "drive":
        return bool(getattr(args, "allow_live_drive_write", False))
    return False

def run_gws_command(args_list: list[str]) -> dict:
    """Execute a command via the underlying google_api.py compat script."""
    cmd = [
        str(DEFAULT_PYTHON),
        str(DEFAULT_GOOGLE_API),
    ] + args_list
    env = os.environ.copy()
    env["HERMES_HOME"] = str(GOOGLE_HERMES_HOME)
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env
    )
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or f"Process exited with {result.returncode}"
        raise RuntimeError(err)
        
    stdout = result.stdout.strip()
    if not stdout:
        return {}
        
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Unexpected non-JSON response from google_api.py: {stdout}")

def main():
    preview_flag = False
    allow_live_writes_flag = False
    allow_live_calendar_delete_flag = False
    mode_flag = None
    
    cleaned_args = []
    i = 0
    args_to_process = sys.argv[1:]
    while i < len(args_to_process):
        arg = args_to_process[i]
        if arg == "--preview":
            preview_flag = True
        elif arg == "--allow-live-google-writes":
            allow_live_writes_flag = True
        elif arg == "--allow-live-calendar-delete":
            allow_live_calendar_delete_flag = True
        elif arg == "--mode":
            if i + 1 < len(args_to_process):
                mode_flag = args_to_process[i+1]
                i += 1
        else:
            cleaned_args.append(arg)
        i += 1

    parser = argparse.ArgumentParser(description="Google Workspace controlled writes for Personal Assistant.")
    
    # Subcommands
    sub = parser.add_subparsers(dest="service", required=True)
    
    # --- Calendar Subcommand ---
    cal = sub.add_parser("calendar")
    cal_sub = cal.add_subparsers(dest="action", required=True)
    
    # Create shift events
    p = cal_sub.add_parser("create-shift-events")
    p.add_argument("--source", required=True, help="Source e.g. ukg")
    p.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    p.add_argument("--calendar-id", default="primary")
    p.add_argument("--segments-json", help="Path to structured segments JSON")
    p.add_argument("--segments-text", help="Raw shift segment text")
    p.add_argument("--create-breaks", action="store_true", help="Create events for breaks/meals")
    p.add_argument("--map-meal-to-break", action="store_true", help="Map meal/lunch breaks to 'Break' for duplicate detection")
    p.add_argument("--allow-live-calendar-write", action="store_true", help="Live calendar write gate")
    
    # Generic create
    p = cal_sub.add_parser("create")
    p.add_argument("--summary", required=True)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--location", default="")
    p.add_argument("--description", default="")
    p.add_argument("--calendar", default="primary")
    p.add_argument("--allow-live-calendar-write", action="store_true", help="Live calendar write gate")
    
    # Generic update
    p = cal_sub.add_parser("update")
    p.add_argument("event_id")
    p.add_argument("--summary", default="")
    p.add_argument("--start", default="")
    p.add_argument("--end", default="")
    p.add_argument("--location", default="")
    p.add_argument("--description", default="")
    p.add_argument("--calendar", default="primary")
    p.add_argument("--allow-live-calendar-write", action="store_true", help="Live calendar write gate")
    
    # Cleanup duplicates
    p = cal_sub.add_parser("cleanup-duplicates")
    p.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    p.add_argument("--calendar-id", default="primary")
    p.add_argument("--cleanup-preview", help="Path to a reviewed preview JSON file")
    p.add_argument("--allow-live-calendar-delete", action="store_true", help="Dedicated live calendar delete gate")

    # Generic delete
    p = cal_sub.add_parser("delete")
    p.add_argument("event_id")
    p.add_argument("--calendar", default="primary")
    p.add_argument("--allow-live-calendar-delete", action="store_true", help="Dedicated live calendar delete gate")
    
    # --- Gmail Subcommand ---
    gmail = sub.add_parser("gmail")
    gmail_sub = gmail.add_subparsers(dest="action", required=True)
    
    # Create draft
    p = gmail_sub.add_parser("draft-create")
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--cc", default="")
    p.add_argument("--from-header", default="")
    p.add_argument("--html", action="store_true")
    p.add_argument("--thread-id", default="")
    p.add_argument("--allow-live-gmail-draft", action="store_true", help="Live draft write gate")
    
    # Send draft
    p = gmail_sub.add_parser("send-draft")
    p.add_argument("draft_id")
    p.add_argument("--allow-live-gmail-send", action="store_true", help="Live draft send gate")
    
    # --- Docs Subcommand ---
    docs = sub.add_parser("docs")
    docs_sub = docs.add_subparsers(dest="action", required=True)
    
    # Create doc
    p = docs_sub.add_parser("create")
    p.add_argument("--title", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--allow-live-docs-write", action="store_true", help="Live docs write gate")
    
    # Append doc
    p = docs_sub.add_parser("append")
    p.add_argument("doc_id")
    p.add_argument("--text", required=True)
    p.add_argument("--allow-live-docs-write", action="store_true", help="Live docs write gate")
    
    # --- Sheets Subcommand ---
    sheets = sub.add_parser("sheets")
    sheets_sub = sheets.add_subparsers(dest="action", required=True)
    
    # Create sheet
    p = sheets_sub.add_parser("create")
    p.add_argument("--title", required=True)
    p.add_argument("--sheet-name", default="")
    p.add_argument("--allow-live-sheets-write", action="store_true", help="Live sheets write gate")
    
    # Update sheet range
    p = sheets_sub.add_parser("update")
    p.add_argument("sheet_id")
    p.add_argument("range")
    p.add_argument("--values", required=True)
    p.add_argument("--allow-live-sheets-write", action="store_true", help="Live sheets write gate")
    
    # Append sheet range
    p = sheets_sub.add_parser("append")
    p.add_argument("sheet_id")
    p.add_argument("range")
    p.add_argument("--values", required=True)
    p.add_argument("--allow-live-sheets-write", action="store_true", help="Live sheets write gate")
    
    # --- Drive Subcommand ---
    drive = sub.add_parser("drive")
    drive_sub = drive.add_subparsers(dest="action", required=True)
    
    # Upload
    p = drive_sub.add_parser("upload")
    p.add_argument("path")
    p.add_argument("--name", default="")
    p.add_argument("--parent", default="")
    p.add_argument("--mime-type", default="")
    p.add_argument("--allow-live-drive-write", action="store_true", help="Live drive write gate")
    
    args = parser.parse_args(cleaned_args)
    args.preview = preview_flag
    args.allow_live_google_writes = allow_live_writes_flag
    args.allow_live_calendar_delete = getattr(args, "allow_live_calendar_delete", False) or allow_live_calendar_delete_flag
    args.mode = mode_flag
    
    # Mode 3 (Approved Write Mode) always requires the matching service-specific gate.
    # --mode write and --allow-live-google-writes do not bypass per-action flags.
    is_approved = service_write_approved(args)
            
    # Resolve exact mode
    mode = "read-only"
    if is_approved:
        mode = "write"
    elif args.preview or args.mode == "preview" or (args.service == "calendar" and args.action == "cleanup-duplicates"):
        mode = "preview"
    elif args.mode == "read-only":
        mode = "read-only"
        
    # Execute according to Safety Mode
    if mode == "read-only":
        err_msg = "READ-ONLY: Summarize only. Do NOT modify, delete, reply to, or alter emails/events."
        print(json.dumps({
            "status": "error",
            "message": err_msg,
            "writes_performed": False
        }, indent=2))
        sys.exit(2)
        
    # -------------------------------------------------------------
    # Action Handlers
    # -------------------------------------------------------------
    
    # 1. Create Shift Events
    if args.service == "calendar" and args.action == "create-shift-events":
        # Extract segments
        raw_segments = []
        if args.segments_json:
            raw_segments = load_segments_json(args.segments_json)
        elif args.segments_text:
            raw_segments = parse_shift_text(args.segments_text, args.date)
        else:
            # Check stdin
            if not sys.stdin.isatty():
                stdin_text = sys.stdin.read()
                raw_segments = parse_shift_text(stdin_text, args.date)
                
        # Normalize and filter segments
        offset = get_tz_offset(args.date)
        processed_events = []
        for seg in raw_segments:
            title = seg.get("title", "Work Segment")
            
            # Filter breaks/meals if not requested
            is_break = title.lower() in ["break", "meal", "lunch", "rest", "rest break", "meal break"] or title.lower().startswith("break")
            if is_break and not args.create_breaks:
                continue
                
            start = normalize_datetime(seg.get("start", ""), args.date, offset)
            end = normalize_datetime(seg.get("end", ""), args.date, offset)
            processed_events.append({
                "title": title,
                "start": start,
                "end": end,
                "calendar_id": args.calendar_id
            })
            
        if mode == "preview":
            print(json.dumps({
                "status": "preview",
                "created_events": processed_events,
                "writes_performed": False
            }, indent=2))
            sys.exit(0)
            
        # Check for existing events to prevent duplicates
        existing_events = []
        try:
            start_query = f"{args.date}T00:00:00{offset}"
            end_query = f"{args.date}T23:59:59{offset}"
            existing_events = run_gws_command([
                "calendar", "safe-list",
                "--start", start_query,
                "--end", end_query
            ])
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to fetch existing events for duplicate check: {e}\n")

        existing_keys = []
        for ee in existing_events:
            summary = ee.get("title") or ee.get("summary") or ""
            start_t = ee.get("start", "")
            end_t = ee.get("end", "")
            existing_keys.append((summary, start_t, end_t))

        # Approved Live Write
        created_events = []
        skipped_events = []
        for event in processed_events:
            is_duplicate = False
            for exist_summary, exist_start, exist_end in existing_keys:
                if event["start"] == exist_start and event["end"] == exist_end:
                    if is_duplicate_title(event["title"], exist_summary, map_meal_to_break=args.map_meal_to_break):
                        is_duplicate = True
                        break

            if is_duplicate:
                skipped_events.append({
                    "title": event["title"],
                    "start": event["start"],
                    "end": event["end"],
                    "calendar_id": event["calendar_id"],
                    "note": "Skipped duplicate"
                })
                continue

            desc = f"Shift event imported from {args.source} on {args.date}."
            gws_args = [
                "calendar", "create",
                "--summary", event["title"],
                "--start", event["start"],
                "--end", event["end"],
                "--calendar", event["calendar_id"],
                "--description", desc,
                "--allow-live-google-calendar-write"
            ]
            res = run_gws_command(gws_args)
            event_id = res.get("id", "unknown-id")
            
            created_events.append({
                "title": event["title"],
                "start": event["start"],
                "end": event["end"],
                "calendar_id": event["calendar_id"],
                "event_id": event_id
            })
            
        writes_performed = len(created_events) > 0
        log_write("calendar.create-shift-events", {
            "source": args.source,
            "date": args.date,
            "events_count": len(created_events),
            "created_events": created_events,
            "skipped_events": skipped_events
        })
        
        print(json.dumps({
            "status": "success",
            "created_events": created_events,
            "skipped_events": skipped_events,
            "writes_performed": writes_performed
        }, indent=2))
        sys.exit(0)
        
    # 2. Generic Calendar actions
    elif args.service == "calendar":
        if args.action == "create":
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "title": args.summary,
                    "start": args.start,
                    "end": args.end,
                    "calendar_id": args.calendar,
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            res = run_gws_command([
                "calendar", "create",
                "--summary", args.summary,
                "--start", args.start,
                "--end", args.end,
                "--location", args.location,
                "--description", args.description,
                "--calendar", args.calendar,
                "--allow-live-google-calendar-write"
            ])
            log_write("calendar.create", {"event_id": res.get("id"), "summary": args.summary})
            print(json.dumps({
                "status": "success",
                "event_id": res.get("id"),
                "writes_performed": True
            }, indent=2))
            sys.exit(0)
            
        elif args.action == "update":
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "event_id": args.event_id,
                    "summary": args.summary,
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            cmd = ["calendar", "update", args.event_id, "--calendar", args.calendar, "--allow-live-google-calendar-write"]
            if args.summary: cmd.extend(["--summary", args.summary])
            if args.start: cmd.extend(["--start", args.start])
            if args.end: cmd.extend(["--end", args.end])
            if args.location: cmd.extend(["--location", args.location])
            if args.description: cmd.extend(["--description", args.description])
            
            res = run_gws_command(cmd)
            log_write("calendar.update", {"event_id": args.event_id, "fields": {"summary": args.summary}})
            print(json.dumps({
                "status": "success",
                "event_id": args.event_id,
                "writes_performed": True
            }, indent=2))
            sys.exit(0)
            
        elif args.action == "cleanup-duplicates":
            # Determine timezone offset
            offset = get_tz_offset(args.date)
            start_query = f"{args.date}T00:00:00{offset}"
            end_query = f"{args.date}T23:59:59{offset}"

            if args.cleanup_preview:
                # Read from reviewed JSON file
                with open(args.cleanup_preview, "r") as f:
                    preview_data = json.load(f)
                
                delete_candidates = []
                for group in preview_data.get("duplicate_groups", []):
                    for cand in group.get("delete_candidates", []):
                        if cand.get("event_id"):
                            delete_candidates.append(cand)
                
                # Check for delete authorization
                if not getattr(args, "allow_live_calendar_delete", False) or mode == "preview":
                    # Output preview of what would be deleted
                    print(json.dumps({
                        "status": "preview",
                        "cleanup_file": args.cleanup_preview,
                        "delete_candidates": delete_candidates,
                        "writes_performed": False,
                        "delete_performed": False
                    }, indent=2))
                    sys.exit(0)
                
                # Live delete
                deleted_ids = []
                for cand in delete_candidates:
                    eid = cand["event_id"]
                    run_gws_command(["calendar", "delete", eid, "--calendar", args.calendar_id, "--allow-live-google-calendar-write"])
                    log_write("calendar.delete-cleanup", {"event_id": eid, "title": cand.get("title")})
                    deleted_ids.append(eid)
                
                print(json.dumps({
                    "status": "success",
                    "deleted_event_ids": deleted_ids,
                    "writes_performed": False,
                    "delete_performed": len(deleted_ids) > 0
                }, indent=2))
                sys.exit(0)
            
            else:
                # No cleanup-preview path provided. Query calendar to find duplicates
                existing_events = []
                try:
                    existing_events = run_gws_command([
                        "calendar", "list",
                        "--start", start_query,
                        "--end", end_query
                    ])
                except Exception as e:
                    sys.stderr.write(f"Error: Failed to fetch calendar list: {e}\n")
                    sys.exit(1)
                
                # Group by time and canonical/fuzzy titles
                groups = {}
                for ev in existing_events:
                    title = ev.get("summary") or ev.get("title") or ""
                    start = ev.get("start", "")
                    end = ev.get("end", "")
                    if not start or not end:
                        continue
                    
                    key = (start, end)
                    matched_group_key = None
                    for gkey in groups:
                        # Same start/end time
                        if gkey == key:
                            # Fuzzy/canonical title match
                            for first_ev in groups[gkey]:
                                first_title = first_ev.get("summary") or first_ev.get("title") or ""
                                if is_duplicate_title(title, first_title, map_meal_to_break=True):
                                    matched_group_key = gkey
                                    break
                            if matched_group_key:
                                break
                    
                    if matched_group_key:
                        groups[matched_group_key].append(ev)
                    else:
                        groups[key] = [ev]
                
                # Filter only groups that have duplicates (len > 1)
                duplicate_groups = []
                for key, evs in groups.items():
                    if len(evs) > 1:
                        # Determine which one to keep
                        # Prefer keeping the event created by the local API workflow with better title consistency.
                        def get_preference_score(e):
                            summary = e.get("summary") or e.get("title") or ""
                            desc = e.get("description") or ""
                            score = 0
                            if summary.startswith("Apple - "):
                                score += 10
                            if "Shift event imported" in desc:
                                score += 5
                            return score
                        
                        sorted_evs = sorted(evs, key=get_preference_score, reverse=True)
                        keep_ev = sorted_evs[0]
                        delete_evs = sorted_evs[1:]
                        
                        canonical = canonicalize_title(keep_ev.get("summary") or keep_ev.get("title") or "")
                        duplicate_groups.append({
                            "canonical_title": canonical,
                            "start": key[0],
                            "end": key[1],
                            "keep_event": {
                                "event_id": keep_ev.get("id"),
                                "title": keep_ev.get("summary") or keep_ev.get("title")
                            },
                            "delete_candidates": [
                                {
                                    "event_id": de.get("id"),
                                    "title": de.get("summary") or de.get("title"),
                                    "reason": "Duplicate title/time match"
                                } for de in delete_evs
                            ]
                        })
                
                print(json.dumps({
                    "status": "preview",
                    "writes_performed": False,
                    "delete_performed": False,
                    "duplicate_groups": duplicate_groups
                }, indent=2))
                sys.exit(0)

        elif args.action == "delete":
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "event_id": args.event_id,
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            if not getattr(args, "allow_live_calendar_delete", False):
                err_msg = "REFUSED: Deleting calendar events requires the dedicated explicit flag: --allow-live-calendar-delete"
                print(json.dumps({
                    "status": "error",
                    "message": err_msg,
                    "writes_performed": False
                }, indent=2))
                sys.exit(2)
                
            run_gws_command(["calendar", "delete", args.event_id, "--calendar", args.calendar, "--allow-live-google-calendar-write"])
            log_write("calendar.delete", {"event_id": args.event_id})
            print(json.dumps({
                "status": "success",
                "event_id": args.event_id,
                "writes_performed": True
            }, indent=2))
            sys.exit(0)
            
    # 3. Gmail actions
    elif args.service == "gmail":
        if args.action == "draft-create":
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "to": args.to,
                    "subject": args.subject,
                    "body_preview": args.body[:100],
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            cmd = [
                "gmail", "draft-create",
                "--to", args.to,
                "--subject", args.subject,
                "--body", args.body,
                "--allow-live-gmail-draft"
            ]
            if args.cc: cmd.extend(["--cc", args.cc])
            if args.from_header: cmd.extend(["--from", args.from_header])
            if args.html: cmd.append("--html")
            if args.thread_id: cmd.extend(["--thread-id", args.thread_id])
            
            res = run_gws_command(cmd)
            log_write("gmail.draft-create", {"draft_id": res.get("draftId"), "to": args.to})
            print(json.dumps({
                "status": "success",
                "draft_id": res.get("draftId"),
                "writes_performed": True
            }, indent=2))
            sys.exit(0)
            
        elif args.action == "send-draft":
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "draft_id": args.draft_id,
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            res = run_gws_command([
                "gmail", "send-draft", args.draft_id,
                "--allow-live-gmail-send",
                "--send-approved-draft"
            ])
            log_write("gmail.send-draft", {"draft_id": args.draft_id, "message_id": res.get("id")})
            print(json.dumps({
                "status": "success",
                "message_id": res.get("id"),
                "writes_performed": True
            }, indent=2))
            sys.exit(0)
            
    # 4. Docs actions
    elif args.service == "docs":
        if args.action == "create":
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "title": args.title,
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            cmd = ["docs", "create", "--title", args.title, "--allow-live-docs-write"]
            if args.body: cmd.extend(["--body", args.body])
            
            res = run_gws_command(cmd)
            log_write("docs.create", {"doc_id": res.get("documentId"), "title": args.title})
            print(json.dumps({
                "status": "success",
                "doc_id": res.get("documentId"),
                "url": res.get("url"),
                "writes_performed": True
            }, indent=2))
            sys.exit(0)
            
        elif args.action == "append":
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "doc_id": args.doc_id,
                    "text_preview": args.text[:100],
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            res = run_gws_command(["docs", "append", args.doc_id, "--text", args.text, "--allow-live-docs-write"])
            log_write("docs.append", {"doc_id": args.doc_id, "length": len(args.text)})
            print(json.dumps({
                "status": "success",
                "doc_id": args.doc_id,
                "writes_performed": True
            }, indent=2))
            sys.exit(0)
            
    # 5. Sheets actions
    elif args.service == "sheets":
        if args.action == "create":
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "title": args.title,
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            cmd = ["sheets", "create", "--title", args.title, "--allow-live-sheets-write"]
            if args.sheet_name: cmd.extend(["--sheet-name", args.sheet_name])
            
            res = run_gws_command(cmd)
            log_write("sheets.create", {"sheet_id": res.get("spreadsheetId"), "title": args.title})
            print(json.dumps({
                "status": "success",
                "sheet_id": res.get("spreadsheetId"),
                "url": res.get("spreadsheetUrl"),
                "writes_performed": True
            }, indent=2))
            sys.exit(0)
            
        elif args.action in ["update", "append"]:
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "sheet_id": args.sheet_id,
                    "range": args.range,
                    "values": json.loads(args.values),
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            res = run_gws_command([
                "sheets", args.action, args.sheet_id, args.range,
                "--values", args.values,
                "--allow-live-sheets-write"
            ])
            log_write(f"sheets.{args.action}", {"sheet_id": args.sheet_id, "range": args.range})
            print(json.dumps({
                "status": "success",
                "sheet_id": args.sheet_id,
                "writes_performed": True
            }, indent=2))
            sys.exit(0)
            
    # 6. Drive actions
    elif args.service == "drive":
        if args.action == "upload":
            if mode == "preview":
                print(json.dumps({
                    "status": "preview",
                    "path": args.path,
                    "name": args.name,
                    "writes_performed": False
                }, indent=2))
                sys.exit(0)
                
            cmd = ["drive", "upload", args.path, "--allow-live-drive-write"]
            if args.name: cmd.extend(["--name", args.name])
            if args.parent: cmd.extend(["--parent", args.parent])
            if args.mime_type: cmd.extend(["--mime-type", args.mime_type])
            
            res = run_gws_command(cmd)
            log_write("drive.upload", {"file_id": res.get("id"), "name": res.get("name")})
            print(json.dumps({
                "status": "success",
                "file_id": res.get("id"),
                "url": res.get("webViewLink"),
                "writes_performed": True
            }, indent=2))
            sys.exit(0)

if __name__ == "__main__":
    main()
