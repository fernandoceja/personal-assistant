#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORMAT_CONTRACT="$ROOT_DIR/prompts/safe-briefing-output-format.md"

INPUT_PATH=""
OUTPUT_PATH=""
EXECUTE_REQUESTED=0

usage() {
  cat <<'USAGE'
Usage: scripts/format-safe-briefing.sh --input PATH [--output PATH] [--execute]

Default behavior:
  Creates a formatter-ready prompt sidecar and a deterministic local final
  briefing. Does not call Codex, Hermes, Gmail, Calendar, or any live data source.

Output:
  If --output is omitted, the final briefing path is derived by replacing
  -safe.md with -final.md in the input path.

Execution:
  --execute explicitly calls Codex CLI and writes final output to the final
  briefing path. It never appends final output to the source packet. Omit
  --execute for fully local non-live validation.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --input requires a value." >&2
        usage >&2
        exit 2
      fi
      INPUT_PATH="$2"
      shift 2
      ;;
    --output)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --output requires a value." >&2
        usage >&2
        exit 2
      fi
      OUTPUT_PATH="$2"
      shift 2
      ;;
    --execute)
      EXECUTE_REQUESTED=1
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

if [[ -z "$INPUT_PATH" ]]; then
  echo "ERROR: --input is required." >&2
  usage >&2
  exit 2
fi

if [[ ! -f "$INPUT_PATH" ]]; then
  echo "ERROR: Input source packet not found: $INPUT_PATH" >&2
  exit 1
fi

if [[ ! -f "$FORMAT_CONTRACT" ]]; then
  echo "ERROR: Format contract not found: $FORMAT_CONTRACT" >&2
  exit 1
fi

if [[ -z "$OUTPUT_PATH" ]]; then
  if [[ "$INPUT_PATH" != *-safe.md ]]; then
    echo "ERROR: --output is required when input does not end with -safe.md." >&2
    exit 2
  fi
  OUTPUT_PATH="${INPUT_PATH%-safe.md}-final.md"
fi

output_dir="$(dirname "$OUTPUT_PATH")"
mkdir -p "$output_dir"

prompt_path="${OUTPUT_PATH%.md}-formatter-prompt.md"

{
  echo "# Safe Briefing Formatter Prompt"
  echo
  echo "Goal: Convert the source packet below into a final personal-assistant briefing."
  echo
  echo "Return only the final briefing. Always include exactly these six top-level headings as ## headings, in this exact order:"
  echo
  echo "1. Executive Summary"
  echo "2. Priority Now"
  echo "3. Review With Me"
  echo "4. Calendar Watch"
  echo "5. Low Priority"
  echo "6. Ignore/Suspicious"
  echo
  echo "Required empty-section placeholders:"
  echo "- If a section has no source-backed items, write: No source-backed items in this packet."
  echo "- For Ignore/Suspicious with no approved email or message source, write: No email or message source was approved for this packet."
  echo
  echo "Safety and privacy rules:"
  echo "- Do not invent missing source data."
  echo "- Do not omit any of the six required headings."
  echo "- Treat legal, immigration, money, work, school, and deadline uncertainty as Review With Me."
  echo "- Keep output short and scannable."
  echo "- Do not include secrets, tokens, credentials, OAuth artifacts, or raw debug blocks."
  echo "- Do not expose more private calendar detail than needed."
  echo "- Do not create, modify, send, schedule, archive, delete, or persist anything beyond the requested output file."
  echo
  echo "## Format Contract"
  echo
  cat "$FORMAT_CONTRACT"
  echo
  echo "## Source Packet"
  echo
  cat "$INPUT_PATH"
} > "$prompt_path"

source_has() {
  grep -Fq "$1" "$INPUT_PATH"
}

calendar_state_summary() {
  local local_state="not_checked"
  local google_state="not_checked"

  if source_has "## Local Apple Calendar Diagnostics"; then
    if source_has "Result: events found successfully."; then
      local_state="items_found"
    elif source_has "Result: preferred calendars found, but no events were found for today/tomorrow."; then
      local_state="checked_no_items"
    elif source_has "Permission/status: granted — Calendar.app read completed."; then
      local_state="checked_no_items"
    fi
  fi

  if source_has "## Google Calendar Readonly Diagnostics"; then
    if source_has "Result: success — Google Calendar readonly safe-list completed."; then
      if awk '
        /^## Google Calendar Readonly Diagnostics$/ { in_section=1; next }
        in_section && /^## / { in_section=0 }
        in_section && /^\[\]$/ { found_empty=1 }
        END { exit(found_empty ? 0 : 1) }
      ' "$INPUT_PATH"; then
        google_state="checked_no_items"
      else
        google_state="items_found"
      fi
    fi
  elif source_has "Google Calendar live data not accessed. Run with --allow-live-google-calendar to include readonly Google Calendar."; then
    google_state="not_checked"
  fi

  printf '%s|%s\n' "$local_state" "$google_state"
}

calendar_watch_text() {
  local local_state="$1"
  local google_state="$2"

  if [[ "$local_state" == "items_found" || "$google_state" == "items_found" ]]; then
    if [[ "$local_state" == "items_found" && "$google_state" == "items_found" ]]; then
      echo "Local calendar and Google Calendar readonly sources were checked; today/tomorrow items were found. Review the source packet for safe event details."
    elif [[ "$local_state" == "items_found" ]]; then
      if [[ "$google_state" == "checked_no_items" ]]; then
        echo "Local calendar was checked and returned today/tomorrow items; Google Calendar readonly was checked and returned no events."
      else
        echo "Local calendar was checked and returned today/tomorrow items; Google Calendar readonly was not checked."
      fi
    else
      if [[ "$local_state" == "checked_no_items" ]]; then
        echo "Local calendar was checked and returned no today/tomorrow events; Google Calendar readonly was checked and returned items."
      else
        echo "Google Calendar readonly was checked and returned today/tomorrow items; local calendar was not checked."
      fi
    fi
  elif [[ "$local_state" == "checked_no_items" && "$google_state" == "checked_no_items" ]]; then
    echo "Local calendar and Google Calendar readonly sources were checked; no today/tomorrow events were found."
  elif [[ "$local_state" == "checked_no_items" ]]; then
    echo "Local calendar was checked; no today/tomorrow events were found. Google Calendar readonly was not checked."
  elif [[ "$google_state" == "checked_no_items" ]]; then
    echo "Google Calendar readonly was checked; no today/tomorrow events were found. Local calendar was not checked."
  else
    echo "Calendar sources were not checked in this packet."
  fi
}

executive_summary_text() {
  local local_state="$1"
  local google_state="$2"

  if [[ "$local_state" == "items_found" || "$google_state" == "items_found" ]]; then
    echo "Calendar sources were checked and returned today/tomorrow items; review Calendar Watch."
  elif [[ "$local_state" == "checked_no_items" || "$google_state" == "checked_no_items" ]]; then
    echo "No urgent or calendar-backed items found for today/tomorrow."
  else
    echo "No source-backed items in this packet."
  fi
}

write_local_final() {
  local states local_state google_state executive_summary calendar_note
  states="$(calendar_state_summary)"
  local_state="${states%%|*}"
  google_state="${states#*|}"
  executive_summary="$(executive_summary_text "$local_state" "$google_state")"
  calendar_note="$(calendar_watch_text "$local_state" "$google_state")"

  cat > "$OUTPUT_PATH" <<FINAL
# Safe Briefing — $(date +%Y-%m-%d)

## Executive Summary
$executive_summary

## Priority Now
No source-backed items in this packet.

## Review With Me
No source-backed items in this packet.

## Calendar Watch
$calendar_note

## Low Priority
No source-backed items in this packet.

## Ignore/Suspicious
No email or message source was approved for this packet.
FINAL
}

if [[ $EXECUTE_REQUESTED -eq 0 ]]; then
  write_local_final
  cat <<SUMMARY
Safe briefing formatter local formatting complete.
Input source packet: $INPUT_PATH
Formatter prompt: $prompt_path
Final output: $OUTPUT_PATH
Execution backend: not called
SUMMARY
  exit 0
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: --execute requested, but Codex CLI was not found." >&2
  exit 1
fi

codex exec - --output-last-message "$OUTPUT_PATH" < "$prompt_path"

cat <<SUMMARY
Safe briefing formatter execution complete.
Input source packet: $INPUT_PATH
Formatter prompt: $prompt_path
Final output: $OUTPUT_PATH
Execution backend: Codex CLI
SUMMARY
