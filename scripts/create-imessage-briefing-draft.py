#!/usr/bin/env python3
"""Create a review-only iMessage-ready draft from the latest final briefing.

This script writes a local text file only. It never opens Messages.app, never
runs AppleScript, and has no send path.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTION_NAMES = (
    "Executive Summary",
    "Priority Now",
    "Review With Me",
    "Calendar Watch",
    "Low Priority",
    "Ignore/Suspicious",
)

RAW_DETAIL_PATTERNS = (
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"\b(message|thread)\s*id\b\s*[:#]?\s*\S*", re.IGNORECASE),
    re.compile(r"\battachment\b\s*[:#]?\s*\S*", re.IGNORECASE),
    re.compile(r"\([^)]*\.[a-z]{2,}[^)]*\)", re.IGNORECASE),
)

NO_SOURCE_PREFIXES = (
    "no source-backed",
    "no clear",
    "no items",
    "none",
    "nothing urgent",
)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def find_latest_final_briefing(repo_root: Path) -> Path:
    briefings_dir = repo_root / "briefings"
    candidates = sorted(briefings_dir.glob("*-final.md"))
    if not candidates:
        raise FileNotFoundError("No final briefing found at briefings/*-final.md")
    return candidates[-1]


def validate_final_briefing_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.name.endswith("-final.md"):
        raise ValueError("Input must be a final briefing ending in -final.md; safe packets are not allowed")
    if not resolved.is_file():
        raise FileNotFoundError(f"Final briefing not found: {resolved}")
    return resolved


def output_path_for(final_path: Path) -> Path:
    name = final_path.name.removesuffix("-final.md") + "-imessage-draft.txt"
    return final_path.with_name(name)


def parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            heading = match.group(1).strip()
            current = heading if heading in SECTION_NAMES else None
            if current:
                sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def clean_line(text: str) -> str:
    text = text.strip().lstrip("-•0123456789. )\t")
    for pattern in RAW_DETAIL_PATTERNS:
        text = pattern.sub("", text)
    text = text.replace("Gmail readonly —", "").replace("raw Gmail details omitted", "safe details omitted")
    text = re.sub(r"\breceived\s+[^.;]+[.;]?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" -—.;")
    return text


def content_lines(section_text: str) -> list[str]:
    lines = []
    for raw in section_text.splitlines():
        cleaned = clean_line(raw)
        if cleaned:
            lines.append(cleaned)
    return lines


def has_no_source(lines: list[str]) -> bool:
    return not lines or all(line.lower().startswith(NO_SOURCE_PREFIXES) for line in lines)


def count_actionable(lines: list[str]) -> int:
    if has_no_source(lines):
        return 0
    bullet_count = sum(1 for line in lines if not line.lower().startswith(NO_SOURCE_PREFIXES))
    return bullet_count


def summarize_priority(section_text: str) -> str:
    lines = content_lines(section_text)
    count = count_actionable(lines)
    if count == 0:
        return "No urgent source-backed items."
    return f"{count} item(s) need prompt attention; review the final briefing before acting."


def summarize_review(section_text: str) -> str:
    lines = content_lines(section_text)
    count = count_actionable(lines)
    if count == 0:
        return "0 items need review."
    return f"{count} item(s) need your review before any action."


def summarize_calendar(section_text: str) -> str:
    lines = content_lines(section_text)
    if has_no_source(lines):
        return "No clear date/time commitments."
    first = lines[0]
    if len(lines) > 1:
        return f"{len(lines)} calendar item(s); first: {first[:110]}"
    return first[:140]


def summarize_ignore(section_text: str) -> str:
    lines = content_lines(section_text)
    if has_no_source(lines):
        return "No source-backed suspicious items."
    count = count_actionable(lines)
    first = lines[0]
    return f"{count} grouped item(s); {first[:100]}"


def build_draft(final_text: str) -> str:
    sections = parse_sections(final_text)
    draft_lines = [
        "Status: Review-only briefing draft. Nothing sent.",
        f"Priority Now: {summarize_priority(sections.get('Priority Now', ''))}",
        f"Review With Me: {summarize_review(sections.get('Review With Me', ''))}",
        f"Calendar Watch: {summarize_calendar(sections.get('Calendar Watch', ''))}",
        f"Ignore/Suspicious: {summarize_ignore(sections.get('Ignore/Suspicious', ''))}",
    ]
    draft = "\n".join(draft_lines)
    if len(draft) <= 900:
        return draft
    # Conservative fallback: keep required headings and counts only.
    review_count = count_actionable(content_lines(sections.get("Review With Me", "")))
    priority_count = count_actionable(content_lines(sections.get("Priority Now", "")))
    ignore_count = count_actionable(content_lines(sections.get("Ignore/Suspicious", "")))
    fallback = "\n".join(
        [
            "Status: Review-only briefing draft. Nothing sent.",
            f"Priority Now: {priority_count} item(s).",
            f"Review With Me: {review_count} item(s) need review.",
            "Calendar Watch: See final briefing for safe summary.",
            f"Ignore/Suspicious: {ignore_count} grouped item(s).",
        ]
    )
    return fallback[:900]


def create_draft(final_path: Path) -> tuple[Path, str]:
    final_path = validate_final_briefing_path(final_path)
    final_text = final_path.read_text(encoding="utf-8")
    draft = build_draft(final_text)
    output_path = output_path_for(final_path)
    output_path.write_text(draft + "\n", encoding="utf-8")
    return output_path, draft


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local review-only iMessage draft text file from a final briefing. Never sends."
    )
    parser.add_argument(
        "final_briefing",
        nargs="?",
        help="Optional path to briefings/YYYY-MM-DD-HH-final.md. Defaults to latest briefings/*-final.md.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        repo_root = repo_root_from_script()
        final_path = Path(args.final_briefing) if args.final_briefing else find_latest_final_briefing(repo_root)
        output_path, draft = create_draft(final_path)
        print(f"Draft path: {output_path}")
        print("Preview:")
        print(draft)
        print("Safety: local draft file only; no iMessage was sent.")
        return 0
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
