#!/usr/bin/env python3
"""Create a local HyperFrames-ready briefing video from sanitized summary text.

The input must be a final briefing or an iMessage draft. This script extracts
counts and status labels only, writes a local HyperFrames composition, and tries
to render an MP4 locally. If rendering fails, the storyboard remains available
and the result is marked partial.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_VISUAL_DURATION_SECONDS = 8
NARRATION_PAD_SECONDS = 1.0
MAX_FINAL_TAIL_SECONDS = 3.0
DEFAULT_VOICE_ORDER = ("Ava", "Samantha")

REQUIRED_HEADINGS = (
    "Executive Summary",
    "Priority Now",
    "Review With Me",
    "Calendar Watch",
    "Low Priority",
    "Ignore/Suspicious",
)

NO_SOURCE_PREFIXES = (
    "no source-backed",
    "no clear",
    "no items",
    "none",
    "nothing urgent",
    "0 items",
)

SENSITIVE_PATTERNS = (
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\+?\d[\d\-\s().]{7,}\d"),
    re.compile(r"\b(message|thread|attachment|token|secret|password|api key)\b\s*[:#]?\s*\S*", re.IGNORECASE),
    re.compile(r"\b[A-Z0-9]{8,}\b"),
)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def validate_input_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Input file not found: {resolved}")
    if not (resolved.name.endswith("-final.md") or resolved.name.endswith("-imessage-draft.txt")):
        raise ValueError("Input must be briefings/*-final.md or briefings/*-imessage-draft.txt")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_text(value: str, max_len: int = 120) -> str:
    text = value.strip()
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub("[redacted]", text)
    text = re.sub(r"\([^)]*(?:\.com|\.org|\.net|\.gov|\.edu)[^)]*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" -.;")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip(" ,.;:-") + "..."


def field_value(line: str, label: str) -> str | None:
    match = re.search(rf"\b{re.escape(label)}:\s*(.*?)(?=\s+\b[A-Z][A-Za-z /-]+:\s*|$)", line)
    if not match:
        return None
    value = sanitize_text(match.group(1), max_len=140)
    return value or None


def confidence_text(line: str) -> str:
    value = field_value(line, "Confidence")
    if value:
        return value.split()[0].strip(" .;:")
    lowered = line.lower()
    if "timing unclear" in lowered or "verify" in lowered or "unknown" in lowered:
        return "Low"
    return "Medium"


def action_first_line(line: str, max_len: int = 118) -> str:
    action = field_value(line, "Next Action")
    importance = field_value(line, "Importance")
    subject = field_value(line, "Subject")
    if action:
        return sanitize_text(f"Action: {action} Confidence {confidence_text(line)}.", max_len=max_len)
    if importance:
        return sanitize_text(f"Why: {importance} Confidence {confidence_text(line)}.", max_len=max_len)
    if subject:
        return sanitize_text(f"Subject: {subject} Confidence {confidence_text(line)}.", max_len=max_len)
    return sanitize_text(line, max_len=max_len)


def parse_sections(markdown: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in markdown.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            heading = match.group(1).strip()
            current = heading if heading in REQUIRED_HEADINGS else None
            if current:
                sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def usable_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in lines:
        text = action_first_line(raw.lstrip("-*0123456789. )\t"))
        if text:
            cleaned.append(text)
    return cleaned


def count_items(lines: list[str]) -> int:
    cleaned = usable_lines(lines)
    if not cleaned:
        return 0
    return sum(1 for line in cleaned if not line.lower().startswith(NO_SOURCE_PREFIXES))


def extract_from_final(text: str) -> dict[str, Any]:
    sections = parse_sections(text)
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in sections]
    priority_count = count_items(sections.get("Priority Now", []))
    review_count = count_items(sections.get("Review With Me", []))
    calendar_count = count_items(sections.get("Calendar Watch", []))
    suspicious_count = count_items(sections.get("Ignore/Suspicious", []))
    narration_lines = []
    section_lines: dict[str, list[str]] = {}
    for heading in REQUIRED_HEADINGS:
        lines = usable_lines(sections.get(heading, []))
        section_lines[heading] = lines[:3]
        if lines:
            narration_lines.append(f"{heading}: {lines[0]}")
    return {
        "source_type": "final_briefing",
        "required_headings_present": not missing,
        "missing_headings": missing,
        "narration_lines": narration_lines,
        "section_lines": section_lines,
        "cards": [
            {"label": "Priority", "value": f"{priority_count} item(s)", "tone": "urgent" if priority_count else "clear"},
            {"label": "Review", "value": f"{review_count} item(s)", "tone": "review" if review_count else "clear"},
            {"label": "Calendar", "value": f"{calendar_count} item(s)", "tone": "calendar" if calendar_count else "clear"},
            {"label": "Suspicious", "value": f"{suspicious_count} grouped", "tone": "watch" if suspicious_count else "clear"},
        ],
    }


def extract_from_draft(text: str) -> dict[str, Any]:
    lines = [sanitize_text(line) for line in text.splitlines() if sanitize_text(line)]
    safe_lines = []
    for line in lines:
        label = line.split(":", 1)[0] if ":" in line else "Status"
        if label in {"Status", "Priority Now", "Review With Me", "Calendar Watch", "Ignore/Suspicious"}:
            safe_lines.append(line[:120])
    return {
        "source_type": "imessage_draft",
        "required_headings_present": True,
        "missing_headings": [],
        "narration_lines": safe_lines,
        "section_lines": {
            "Priority Now": safe_lines[:2],
            "Review With Me": safe_lines[2:4],
            "Calendar Watch": safe_lines[4:6],
        },
        "cards": [
            {"label": "Draft", "value": "Review-only", "tone": "clear"},
            {"label": "Lines", "value": f"{len(safe_lines)} safe line(s)", "tone": "review"},
            {"label": "Mode", "value": "Dry-run", "tone": "clear"},
            {"label": "Send", "value": "Blocked", "tone": "watch"},
        ],
    }


def build_storyboard(input_path: Path) -> dict[str, Any]:
    text = input_path.read_text(encoding="utf-8")
    if input_path.name.endswith("-final.md"):
        summary = extract_from_final(text)
    else:
        summary = extract_from_draft(text)
    return {
        "title": "Daily Briefing",
        "subtitle": "Dry-run local preview",
        "safety": "No iMessage sent. No Gmail, Calendar, Drive, Docs, or Sheets writes.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "path": str(input_path),
            "sha256": sha256_file(input_path),
            "source_type": summary["source_type"],
        },
        "summary": summary,
    }


def slide_body(summary: dict[str, Any], heading: str, fallback: str) -> list[str]:
    lines = summary.get("section_lines", {}).get(heading, [])
    if not lines:
        return [fallback]
    return [action_first_line(line, max_len=118) for line in lines[:2]]


def build_visual_slides(storyboard: dict[str, Any], target_duration: float) -> list[dict[str, Any]]:
    summary = storyboard["summary"]
    cards = {card["label"]: card for card in summary["cards"]}
    return [
        {
            "kicker": "Dry-run local preview",
            "title": storyboard["title"],
            "body": [
                f"Priority {cards.get('Priority', {}).get('value', '0 item(s)')}",
                f"Review {cards.get('Review', {}).get('value', '0 item(s)')}",
                f"Calendar {cards.get('Calendar', {}).get('value', '0 item(s)')}",
            ],
            "tone": "clear",
        },
        {
            "kicker": "Priority Now",
            "title": cards.get("Priority", {}).get("value", "0 item(s)"),
            "body": slide_body(summary, "Priority Now", "No source-backed priority items."),
            "tone": cards.get("Priority", {}).get("tone", "clear"),
        },
        {
            "kicker": "Review With Me",
            "title": cards.get("Review", {}).get("value", "0 item(s)"),
            "body": slide_body(summary, "Review With Me", "No source-backed review items."),
            "tone": cards.get("Review", {}).get("tone", "clear"),
        },
        {
            "kicker": "Calendar Watch",
            "title": cards.get("Calendar", {}).get("value", "0 item(s)"),
            "body": slide_body(summary, "Calendar Watch", "No source-backed calendar conflicts."),
            "tone": cards.get("Calendar", {}).get("tone", "clear"),
        },
        {
            "kicker": "Safety Status",
            "title": "Local dry-run complete",
            "body": [
                "No iMessage sent.",
                "No Gmail, Calendar, Drive, Docs, or Sheets writes.",
                "Video/audio artifacts remain local.",
            ],
            "tone": "watch",
        },
    ]


def write_hyperframes_project(workspace: Path, storyboard: dict[str, Any], target_duration: float = BASE_VISUAL_DURATION_SECONDS) -> tuple[Path, Path]:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "hyperframes.json").write_text(
        json.dumps({"name": workspace.name, "entry": "index.html"}, indent=2) + "\n",
        encoding="utf-8",
    )
    (workspace / "storyboard.json").write_text(json.dumps(storyboard, indent=2) + "\n", encoding="utf-8")

    slides = build_visual_slides(storyboard, target_duration)
    slide_duration = max(1.0, target_duration / len(slides))
    slide_html = "\n".join(
        f'<section class="slide {html.escape(slide["tone"])}" style="--delay: {index * slide_duration:.3f}s; --span: {slide_duration:.3f}s;">'
        f'<div class="slide-kicker">{html.escape(slide["kicker"])}</div>'
        f'<h1>{html.escape(slide["title"])}</h1>'
        f'<div class="slide-lines">'
        + "".join(f'<p>{html.escape(line)}</p>' for line in slide["body"])
        + "</div>"
        "</section>"
        for index, slide in enumerate(slides)
    )
    index = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <style>
      * {{ box-sizing: border-box; }}
      html, body {{
        margin: 0;
        width: 1920px;
        height: 1080px;
        overflow: hidden;
        background: #111111;
        color: #f6f1e8;
        font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      #root {{
        position: relative;
        width: 1920px;
        height: 1080px;
        background:
          linear-gradient(140deg, rgba(17,17,17,.92), rgba(31,36,35,.94)),
          radial-gradient(circle at 72% 24%, rgba(133,215,207,.18), transparent 34%),
          repeating-linear-gradient(90deg, rgba(255,255,255,.04) 0 1px, transparent 1px 160px);
        animation: drift {max(target_duration, 1):.3f}s linear both;
      }}
      #root::before {{
        content: "";
        position: absolute;
        inset: 54px;
        border: 1px solid rgba(246,241,232,.14);
      }}
      @keyframes drift {{
        from {{ background-position: 0 0, 0 0, 0 0; }}
        to {{ background-position: 0 0, 80px -50px, 220px 0; }}
      }}
      .slide {{
        position: absolute;
        inset: 0;
        padding: 82px 118px 120px;
        opacity: 0;
        transform: translateY(28px);
        animation: slideShow var(--span) ease-in-out var(--delay) both;
        display: flex;
        flex-direction: column;
        justify-content: center;
      }}
      @keyframes slideShow {{
        0% {{ opacity: 0; transform: translateY(28px); }}
        12% {{ opacity: 1; transform: translateY(0); }}
        86% {{ opacity: 1; transform: translateY(0); }}
        100% {{ opacity: 0; transform: translateY(-18px); }}
      }}
      .slide-kicker {{
        color: #85d7cf;
        font-size: 36px;
        letter-spacing: 0;
        margin-bottom: 28px;
      }}
      h1 {{
        margin: 0 0 24px;
        font-size: 92px;
        line-height: 1;
        letter-spacing: 0;
      }}
      .slide-lines {{
        max-width: 1480px;
        display: grid;
        gap: 18px;
      }}
      .slide-lines p {{
        margin: 0;
        color: #d9d2c4;
        font-size: 34px;
        line-height: 1.28;
        padding: 18px 24px;
        border-left: 4px solid rgba(133,215,207,.58);
        background: rgba(246,241,232,.065);
        max-height: 132px;
        overflow: hidden;
      }}
      .urgent .slide-lines p {{ border-left-color: #ef6f6c; }}
      .review .slide-lines p {{ border-left-color: #f0c36a; }}
      .calendar .slide-lines p {{ border-left-color: #85d7cf; }}
      .watch .slide-lines p {{ border-left-color: #b38cff; }}
      .clear .slide-lines p {{ border-left-color: #85d7cf; }}
      .progress {{
        position: absolute;
        left: 120px;
        right: 120px;
        bottom: 66px;
        height: 6px;
        background: rgba(246,241,232,.13);
      }}
      .progress::before {{
        content: "";
        display: block;
        height: 100%;
        background: #85d7cf;
        transform-origin: left center;
        animation: progress {max(target_duration, 1):.3f}s linear both;
      }}
      @keyframes progress {{
        from {{ transform: scaleX(0); }}
        to {{ transform: scaleX(1); }}
      }}
      .stamp {{
        position: absolute;
        right: 120px;
        bottom: 78px;
        color: #8c857b;
        font-size: 28px;
      }}
    </style>
  </head>
  <body>
    <main id="root" data-composition-id="daily-briefing" data-start="0" data-duration="{target_duration:.3f}" data-width="1920" data-height="1080">
      {slide_html}
      <div class="progress"></div>
      <div class="stamp">local only</div>
    </main>
  </body>
</html>
"""
    index_path = workspace / "index.html"
    index_path.write_text(index, encoding="utf-8")
    return index_path, workspace / "storyboard.json"


def ffprobe_validate(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "reason": "missing"}
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
        data = json.loads(completed.stdout or "{}")
        return {"ok": True, "format": data.get("format", {})}
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return {"ok": False, "reason": str(exc)}


def ffprobe_duration(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "reason": "missing"}
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)]
    try:
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
        data = json.loads(completed.stdout or "{}")
        duration = float(data.get("format", {}).get("duration", 0))
    except (subprocess.CalledProcessError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {"ok": False, "reason": str(exc)}
    return {"ok": True, "duration": duration}


def ffprobe_streams(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "reason": "missing"}
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=index,codec_type,codec_name",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
        data = json.loads(completed.stdout or "{}")
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return {"ok": False, "reason": str(exc)}
    streams = data.get("streams", [])
    stream_types = {stream.get("codec_type") for stream in streams}
    return {
        "ok": "video" in stream_types and "audio" in stream_types,
        "streams": streams,
    }


def build_narration_text(storyboard: dict[str, Any]) -> str:
    summary = storyboard["summary"]
    card_text = ", ".join(f"{card['label']} {card['value']}" for card in summary["cards"])
    narration_lines = summary.get("narration_lines") or []
    if narration_lines:
        body = " ".join(action_first_line(line, max_len=180) for line in narration_lines[:5])
    else:
        body = "No source backed briefing lines available for narration."
    text = (
        f"{storyboard['title']}. "
        f"Local dry run briefing. "
        f"{card_text}. "
        f"{body}. "
        "Safety confirmed. No messages sent and no cloud writes."
    )
    return sanitize_text(text, max_len=1600)


def write_narration_text(workspace: Path, storyboard: dict[str, Any]) -> Path:
    narration_path = workspace / "narration.txt"
    narration_path.write_text(build_narration_text(storyboard) + "\n", encoding="utf-8")
    return narration_path


def available_say_voices() -> set[str]:
    try:
        completed = subprocess.run(["say", "-v", "?"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return set()
    voices: set[str] = set()
    for line in completed.stdout.splitlines():
        name = line.split("#", 1)[0].strip()
        if not name:
            continue
        voices.add(re.split(r"\s{2,}", name, maxsplit=1)[0].strip())
    return voices


def select_narration_voice() -> str | None:
    requested = os.environ.get("BRIEFING_VOICE", "").strip()
    voices = available_say_voices()
    if requested:
        return requested
    for voice in DEFAULT_VOICE_ORDER:
        if voice in voices:
            return voice
    return None


def generate_narration_audio(workspace: Path, narration_path: Path) -> dict[str, Any]:
    aiff_path = workspace / "narration.aiff"
    m4a_path = workspace / "narration.m4a"
    selected_voice = select_narration_voice()
    preferred_cmd = ["say", "-o", str(aiff_path), "--input-file", str(narration_path)]
    if selected_voice:
        preferred_cmd = ["say", "-v", selected_voice, "-o", str(aiff_path), "--input-file", str(narration_path)]
    fallback_cmd = ["say", "-o", str(aiff_path), "--input-file", str(narration_path)]
    say_result = subprocess.run(preferred_cmd, capture_output=True, text=True)
    say_command = preferred_cmd
    voice_used = selected_voice
    if say_result.returncode != 0:
        say_result = subprocess.run(fallback_cmd, capture_output=True, text=True)
        say_command = fallback_cmd
        voice_used = None
    if say_result.returncode != 0:
        return {
            "status": "partial",
            "command": say_command,
            "returncode": say_result.returncode,
            "stderr_tail": say_result.stderr[-1000:],
        }
    convert_cmd = ["ffmpeg", "-y", "-i", str(aiff_path), "-c:a", "aac", str(m4a_path)]
    convert_result = subprocess.run(convert_cmd, capture_output=True, text=True)
    if convert_result.returncode != 0:
        return {
            "status": "partial",
            "command": convert_cmd,
            "returncode": convert_result.returncode,
            "stderr_tail": convert_result.stderr[-1000:],
        }
    duration_probe = ffprobe_duration(m4a_path)
    if not duration_probe.get("ok"):
        return {
            "status": "partial",
            "command": ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(m4a_path)],
            "reason": duration_probe.get("reason", "unknown duration probe failure"),
        }
    narration_duration = float(duration_probe["duration"])
    target_video_duration = max(BASE_VISUAL_DURATION_SECONDS, math.ceil(narration_duration + NARRATION_PAD_SECONDS))
    return {
        "status": "ready",
        "say_command": say_command,
        "voice": voice_used or "system default",
        "convert_command": convert_cmd,
        "narration_text_path": str(narration_path),
        "aiff_path": str(aiff_path),
        "m4a_path": str(m4a_path),
        "duration_seconds": narration_duration,
        "target_video_duration_seconds": target_video_duration,
    }


def extend_video_to_duration(video_path: Path, output_path: Path, target_duration: float) -> dict[str, Any]:
    duration_probe = ffprobe_duration(video_path)
    if not duration_probe.get("ok"):
        return {
            "status": "partial",
            "input_path": str(video_path),
            "reason": duration_probe.get("reason", "unknown duration probe failure"),
        }
    current_duration = float(duration_probe["duration"])
    if current_duration >= target_duration:
        return {
            "status": "ready",
            "input_path": str(video_path),
            "output_path": str(video_path),
            "duration_seconds": current_duration,
            "target_duration_seconds": target_duration,
            "extended": False,
        }
    extra_duration = max(0.0, target_duration - current_duration)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"tpad=stop_mode=clone:stop_duration={extra_duration:.3f}",
        "-t",
        f"{target_duration:.3f}",
        "-r",
        "24",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(output_path),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        return {
            "status": "partial",
            "command": cmd,
            "returncode": completed.returncode,
            "stderr_tail": completed.stderr[-1000:],
        }
    output_probe = ffprobe_duration(output_path)
    return {
        "status": "ready" if output_probe.get("ok") else "partial",
        "command": cmd,
        "input_path": str(video_path),
        "output_path": str(output_path),
        "duration_seconds": output_probe.get("duration"),
        "target_duration_seconds": target_duration,
        "extended": True,
    }


def mux_audio_into_video(video_path: Path, audio_path: Path, output_path: Path, target_duration: float) -> dict[str, Any]:
    temp_path = output_path.with_name(f"{output_path.stem}-with-audio.tmp.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-t",
        f"{target_duration:.3f}",
        "-movflags",
        "+faststart",
        str(temp_path),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        return {
            "status": "partial",
            "command": cmd,
            "returncode": completed.returncode,
            "stderr_tail": completed.stderr[-1000:],
        }
    temp_path.replace(output_path)
    stream_probe = ffprobe_streams(output_path)
    final_duration_probe = ffprobe_duration(output_path)
    audio_duration_probe = ffprobe_duration(audio_path)
    final_duration = final_duration_probe.get("duration")
    audio_duration = audio_duration_probe.get("duration")
    duration_ok = (
        isinstance(final_duration, float)
        and isinstance(audio_duration, float)
        and final_duration + 0.05 >= audio_duration
        and final_duration <= audio_duration + MAX_FINAL_TAIL_SECONDS + 0.25
    )
    return {
        "status": "ready" if stream_probe.get("ok") and duration_ok else "partial",
        "command": cmd,
        "output_path": str(output_path),
        "ffprobe_streams": stream_probe,
        "final_duration": final_duration_probe,
        "audio_duration": audio_duration_probe,
        "duration_ok": duration_ok,
    }


def render_video(workspace: Path, output_path: Path, storyboard: dict[str, Any]) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    silent_path = output_path.with_name(f"{output_path.stem}-silent.mp4")
    narration_path = workspace / "narration.txt"
    audio_result = generate_narration_audio(workspace, narration_path)
    if audio_result.get("status") != "ready":
        return {"status": "partial", "audio": audio_result}
    target_duration = float(audio_result["target_video_duration_seconds"])
    index_path, storyboard_path = write_hyperframes_project(workspace, storyboard, target_duration)
    cmd = [
        "npx",
        "--yes",
        "hyperframes@0.5.7",
        "render",
        str(workspace),
        "--output",
        str(silent_path),
        "--quality",
        "draft",
        "--fps",
        "24",
        "--workers",
        "1",
        "--no-browser-gpu",
        "--quiet",
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "partial", "command": cmd, "error": str(exc)}
    if completed.returncode != 0:
        return {
            "status": "partial",
            "command": cmd,
            "returncode": completed.returncode,
            "stderr_tail": completed.stderr[-1000:],
        }
    probe = ffprobe_validate(silent_path)
    if not probe.get("ok"):
        return {
            "status": "partial",
            "command": cmd,
            "silent_output_path": str(silent_path),
            "ffprobe": probe,
        }
    extended_path = output_path.with_name(f"{output_path.stem}-visual-extended.mp4")
    extend_result = extend_video_to_duration(silent_path, extended_path, target_duration)
    if extend_result.get("status") != "ready":
        return {
            "status": "partial",
            "command": cmd,
            "silent_output_path": str(silent_path),
            "ffprobe": probe,
            "audio": audio_result,
            "extend": extend_result,
        }
    visual_path = Path(extend_result.get("output_path") or silent_path)
    mux_result = mux_audio_into_video(visual_path, Path(audio_result["m4a_path"]), output_path, target_duration)
    return {
        "status": "ready" if mux_result.get("status") == "ready" else "partial",
        "command": cmd,
        "index_path": str(index_path),
        "storyboard_path": str(storyboard_path),
        "silent_output_path": str(silent_path),
        "visual_output_path": str(visual_path),
        "output_path": str(output_path),
        "ffprobe": probe,
        "audio": audio_result,
        "extend": extend_result,
        "mux": mux_result,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create local sanitized HyperFrames briefing video artifact.")
    parser.add_argument("input_path", help="briefings/*-final.md or briefings/*-imessage-draft.txt")
    parser.add_argument("--workspace-root", default="video-workspace", help="Local gitignored video workspace root")
    parser.add_argument("--skip-render", action="store_true", help="Write storyboard/project only; do not run HyperFrames")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        repo_root = repo_root_from_script()
        input_path = validate_input_path(Path(args.input_path))
        stem = input_path.name.removesuffix("-final.md").removesuffix("-imessage-draft.txt")
        workspace = (repo_root / args.workspace_root / stem).resolve()
        output_path = workspace / "renders" / f"{stem}-briefing.mp4"
        storyboard = build_storyboard(input_path)
        index_path, storyboard_path = write_hyperframes_project(workspace, storyboard)
        narration_path = write_narration_text(workspace, storyboard)
        render_result = {"status": "partial", "reason": "render skipped"}
        if not args.skip_render:
            render_result = render_video(workspace, output_path, storyboard)

        result = {
            "status": render_result.get("status", "partial"),
            "safety_mode": "dry-run-local-no-send",
            "input_path": str(input_path),
            "workspace": str(workspace),
            "index_path": str(index_path),
            "storyboard_path": str(storyboard_path),
            "narration_text_path": str(narration_path),
            "narration_voice": render_result.get("audio", {}).get("voice", "not selected"),
            "video_output_path": str(output_path) if output_path.exists() else None,
            "render": render_result,
        }
        summary_path = workspace / "video-summary.json"
        summary_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        result["summary_path"] = str(summary_path)
        print(json.dumps(result, indent=2))
        return 0
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
