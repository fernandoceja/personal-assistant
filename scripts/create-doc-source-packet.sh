#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GAPI="${GAPI:-/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/google_api.py}"
HERMES_TEST_HOME="${HOME_OVERRIDE:-/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home}"
HERMES_TEST_HOME_DIR="${HERMES_HOME_OVERRIDE:-/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.hermes}"
OUTPUT_DIR="$ROOT_DIR/source-packets/docs"

DOC_ID=""
LABEL=""
MAX_CHARS="2000"
SUMMARY_ONLY=0

usage() {
  cat <<'USAGE'
Usage:
  scripts/create-doc-source-packet.sh --doc-id DOC_ID --label LABEL [--max-chars N] [--summary-only]

Creates local source-packets/docs/*.md from an explicitly approved Google Doc.
Read-only: calls google_api.py docs get DOC_ID --allow-live-docs-read.
Does not print document contents to terminal.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --doc-id)
      [[ $# -ge 2 ]] || { echo "ERROR: --doc-id requires a value." >&2; exit 2; }
      DOC_ID="$2"
      shift 2
      ;;
    --label)
      [[ $# -ge 2 ]] || { echo "ERROR: --label requires a value." >&2; exit 2; }
      LABEL="$2"
      shift 2
      ;;
    --max-chars)
      [[ $# -ge 2 ]] || { echo "ERROR: --max-chars requires a value." >&2; exit 2; }
      MAX_CHARS="$2"
      shift 2
      ;;
    --summary-only)
      SUMMARY_ONLY=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$DOC_ID" ]]; then
  echo "ERROR: --doc-id is required." >&2
  usage >&2
  exit 2
fi

if [[ -z "$LABEL" ]]; then
  echo "ERROR: --label is required." >&2
  usage >&2
  exit 2
fi

if ! [[ "$MAX_CHARS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --max-chars must be a non-negative integer." >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"

tmp_json="$(mktemp -t google_doc_source_packet.XXXXXX.json)"
chmod 600 "$tmp_json"
cleanup() {
  rm -f "$tmp_json"
}
trap cleanup EXIT

HOME="$HERMES_TEST_HOME" \
HERMES_HOME="$HERMES_TEST_HOME_DIR" \
python3 "$GAPI" docs get "$DOC_ID" --allow-live-docs-read > "$tmp_json"

python3 - "$tmp_json" "$OUTPUT_DIR" "$DOC_ID" "$LABEL" "$MAX_CHARS" "$SUMMARY_ONLY" <<'PY'
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

json_path = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
doc_id = sys.argv[3]
label = sys.argv[4]
max_chars = int(sys.argv[5])
summary_only = sys.argv[6] == "1"

data = json.loads(json_path.read_text(encoding="utf-8"))
title = str(data.get("title") or "").strip() or "(untitled Google Doc)"
document_id = str(data.get("documentId") or doc_id).strip()
body = str(data.get("body") or "")

if document_id != doc_id:
    raise SystemExit("ERROR: returned document ID did not match requested doc ID")

def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def sanitize_label(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return cleaned[:60] or "google-doc"

def sentence_candidates(text: str) -> list[str]:
    compact = clean_text(text)
    pieces = re.split(r"(?<=[.!?])\s+", compact)
    safe = []
    for piece in pieces:
        piece = piece.strip()
        if 40 <= len(piece) <= 220:
            safe.append(piece)
        if len(safe) >= 5:
            break
    return safe

lower = body.lower()
summary = []
if "business" in lower or "growth" in lower:
    summary.append("Business growth planning is a primary theme.")
if "marketing" in lower or "brand" in lower or "social media" in lower:
    summary.append("Marketing, brand, or audience-development planning appears in the document.")
if "sales" in lower or "revenue" in lower or "financial" in lower or "budget" in lower:
    summary.append("Sales, revenue, finance, or budget planning appears in the document.")
if "operations" in lower or "inventory" in lower or "vendor" in lower or "supplier" in lower:
    summary.append("Operations, inventory, vendor, or execution planning appears in the document.")
if "goal" in lower or "strategy" in lower or "timeline" in lower or "milestone" in lower:
    summary.append("Goals, strategy, timeline, or milestone planning appears in the document.")

if not summary:
    summary = sentence_candidates(body)[:3]
if not summary:
    summary = ["Document read succeeded, but no safe summary signal was extracted."]
summary = summary[:5]

created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
safe_label = sanitize_label(label)
output_path = output_dir / f"{stamp}-{safe_label}-{document_id[:12]}.md"

excerpt = clean_text(body)[:max_chars]
if len(clean_text(body)) > len(excerpt):
    excerpt = excerpt.rstrip() + "..."

lines = [
    f"# Google Doc Source Packet - {label}",
    "",
    "## Metadata",
    f"- Title: {title}",
    f"- Doc ID: {document_id}",
    f"- Created: {created}",
    "- Source type: Google Docs",
    "- Safety note: read-only pull through `docs get --allow-live-docs-read`; no write/share/move/delete operation.",
    "",
    "## Brief Safe Summary",
]
lines.extend(f"- {item}" for item in summary)

if not summary_only:
    lines.extend(
        [
            "",
            f"## Bounded Extract ({max_chars} chars max)",
            "",
            excerpt or "[no text extracted]",
        ]
    )
else:
    lines.extend(["", "## Bounded Extract", "", "[omitted by --summary-only]"])

output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

print(f"PACKET_PATH={output_path}")
print(f"TITLE={title}")
print(f"DOC_ID={document_id}")
print(f"SUMMARY_BULLETS={len(summary)}")
print(f"EXTRACT_MODE={'summary-only' if summary_only else f'max-{max_chars}-chars'}")
print("SAFETY=read-only docs pull; no document contents printed to terminal")
PY
