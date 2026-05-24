#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIEFINGS_DIR="$ROOT_DIR/briefings"
PROMPT_PATH="$ROOT_DIR/prompts/weekly-review.md"
OUTPUT_DIR="$ROOT_DIR/weekly-reviews"
SINCE_DAYS=7
SOURCE_PACKETS=()

usage() {
  cat <<'USAGE'
Usage:
  scripts/run-weekly-review.sh [--since-days N] [--source-packet PATH ...]

Local files only. Reads briefings/*-final.md and optional explicitly named
source-packets/docs/*.md. No live Gmail, Calendar, Drive, Docs, or Sheets.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --since-days)
      [[ $# -ge 2 ]] || { echo "ERROR: --since-days requires a value." >&2; exit 2; }
      SINCE_DAYS="$2"
      shift 2
      ;;
    --source-packet)
      [[ $# -ge 2 ]] || { echo "ERROR: --source-packet requires a value." >&2; exit 2; }
      SOURCE_PACKETS+=("$2")
      shift 2
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

if ! [[ "$SINCE_DAYS" =~ ^[0-9]+$ ]] || [[ "$SINCE_DAYS" -lt 1 ]]; then
  echo "ERROR: --since-days must be a positive integer." >&2
  exit 2
fi

if [[ ! -f "$PROMPT_PATH" ]]; then
  echo "ERROR: Prompt not found: $PROMPT_PATH" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
output_path="$OUTPUT_DIR/$(date +%Y-%m-%d)-weekly-review-source.md"
cutoff_epoch="$(python3 - "$SINCE_DAYS" <<'PY'
import sys, time
days = int(sys.argv[1])
print(int(time.time()) - days * 86400)
PY
)"

{
  echo "# Weekly Review Source Packet - $(date +%Y-%m-%d)"
  echo
  echo "Safety: local files only; no live Gmail, Calendar, Drive, Docs, Sheets, web search, cron, Gateway, or writes."
  echo "Window: final briefings modified in the last $SINCE_DAYS day(s)."
  echo
  echo "## Prompt"
  cat "$PROMPT_PATH"
  echo
  echo "## Final Briefing Inputs"
} > "$output_path"

found_final=0
while IFS= read -r final_path; do
  [[ -n "$final_path" ]] || continue
  found_final=1
  {
    echo
    echo "### ${final_path#$ROOT_DIR/}"
    echo
    cat "$final_path"
  } >> "$output_path"
done < <(find "$BRIEFINGS_DIR" -type f -name '*-final.md' -print0 2>/dev/null | xargs -0 stat -f '%m %N' 2>/dev/null | awk -v cutoff="$cutoff_epoch" '$1 >= cutoff { $1=""; sub(/^ /, ""); print }' | sort)

if [[ "$found_final" -eq 0 ]]; then
  {
    echo
    echo "No local final briefings found in window."
  } >> "$output_path"
fi

source_packet_count=0
if [[ "${SOURCE_PACKETS+x}" == "x" ]]; then
  source_packet_count="${#SOURCE_PACKETS[@]}"
fi

if [[ "$source_packet_count" -gt 0 ]]; then
  {
    echo
    echo "## Approved Local Source Packets"
  } >> "$output_path"
fi

if [[ "$source_packet_count" -gt 0 ]]; then
for packet in "${SOURCE_PACKETS[@]}"; do
  packet_path="$ROOT_DIR/$packet"
  if [[ "$packet" = /* ]]; then
    packet_path="$packet"
  fi
  packet_resolved="$(cd "$(dirname "$packet_path")" && pwd)/$(basename "$packet_path")"
  case "$packet_resolved" in
    "$ROOT_DIR"/source-packets/docs/*.md) ;;
    *)
      echo "ERROR: --source-packet must be under source-packets/docs/: $packet" >&2
      exit 2
      ;;
  esac
  if [[ ! -f "$packet_resolved" ]]; then
    echo "ERROR: Source packet not found: $packet" >&2
    exit 1
  fi
  {
    echo
    echo "### ${packet_resolved#$ROOT_DIR/}"
    echo
    cat "$packet_resolved"
  } >> "$output_path"
done
fi

cat <<SUMMARY
Weekly review source packet created.
Output: ${output_path#$ROOT_DIR/}
Live services: not accessed
SUMMARY
