#!/usr/bin/env python3
"""Write a paths-only daily briefing dry-run audit manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_HEADINGS = (
    "Executive Summary",
    "Priority Now",
    "Review With Me",
    "Calendar Watch",
    "Low Priority",
    "Ignore/Suspicious",
)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def file_status(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"exists": False}
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    digest = hashlib.sha256()
    if resolved.is_file():
        with resolved.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
    return {
        "path": str(resolved),
        "exists": True,
        "size_bytes": resolved.stat().st_size if resolved.is_file() else None,
        "sha256": digest.hexdigest() if resolved.is_file() else None,
    }


def validate_final(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    headings = [line.removeprefix("## ").strip() for line in text.splitlines() if line.startswith("## ")]
    return {
        "required_headings_present": headings == list(REQUIRED_HEADINGS),
        "headings": headings,
    }


def validate_draft(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    blocked_patterns = (
        r"https?://\S+",
        r"\b(message|thread)\s*id\b",
        r"\battachment\b",
        r"\braw\s+(gmail|api)\b",
        r"\b(gmail|calendar)\s+api\b",
    )
    return {
        "non_empty": bool(text),
        "char_count": len(text),
        "under_900_chars": len(text) <= 900,
        "blocked_patterns_absent": not any(re.search(pattern, text, re.IGNORECASE) for pattern in blocked_patterns),
    }


def load_video_summary(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {"status": "missing"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "partial", "error": str(exc)}
    allowed = {
        "status": data.get("status"),
        "workspace": data.get("workspace"),
        "index_path": data.get("index_path"),
        "storyboard_path": data.get("storyboard_path"),
        "video_output_path": data.get("video_output_path"),
        "summary_path": str(path.resolve()),
    }
    render = data.get("render", {})
    if isinstance(render, dict):
        allowed["render_status"] = render.get("status")
        allowed["ffprobe"] = render.get("ffprobe")
    return allowed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write paths-only dry-run manifest.")
    parser.add_argument("--final-briefing", required=True)
    parser.add_argument("--imessage-draft", required=True)
    parser.add_argument("--video-summary-json")
    parser.add_argument("--briefing-status", default="unknown")
    parser.add_argument("--imessage-preview-status", default="unknown")
    parser.add_argument("--output-dir", default="logs/audit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = repo_root_from_script()
    final_path = Path(args.final_briefing).expanduser().resolve()
    draft_path = Path(args.imessage_draft).expanduser().resolve()
    video_summary_path = Path(args.video_summary_json).expanduser().resolve() if args.video_summary_json else None
    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "safety_mode": "dry-run-local-no-send",
        "briefing_status": args.briefing_status,
        "imessage_preview_status": args.imessage_preview_status,
        "final_briefing": file_status(final_path),
        "imessage_draft": file_status(draft_path),
        "video": load_video_summary(video_summary_path),
        "validation_results": {
            "final": validate_final(final_path) if final_path.exists() else {"required_headings_present": False},
            "draft": validate_draft(draft_path) if draft_path.exists() else {"non_empty": False},
        },
        "privacy": {
            "raw_gmail_content_included": False,
            "raw_calendar_content_included": False,
            "private_message_bodies_included": False,
            "secrets_included": False,
        },
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"daily-briefing-dry-run-{timestamp}.json"
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Audit manifest: {output_path}")
    print(
        json.dumps(
            {
                "safety_mode": manifest["safety_mode"],
                "briefing_status": manifest["briefing_status"],
                "imessage_preview_status": manifest["imessage_preview_status"],
                "final_briefing_path": manifest["final_briefing"].get("path"),
                "imessage_draft_path": manifest["imessage_draft"].get("path"),
                "video_status": manifest["video"].get("status"),
                "video_output_path": manifest["video"].get("video_output_path"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
