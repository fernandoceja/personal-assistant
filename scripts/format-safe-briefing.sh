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
  Dry-run only. Creates a formatter-ready prompt sidecar and does not call Codex,
  Hermes, Gmail, Calendar, or any live data source.

Output:
  If --output is omitted, the final briefing path is derived by replacing
  -safe.md with -final.md in the input path.

Execution:
  --execute explicitly calls Codex CLI and writes final output to the final
  briefing path. It never appends final output to the source packet.
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
  echo "Return only the final briefing. Use only these top-level sections when source data supports them:"
  echo
  echo "1. Executive Summary"
  echo "2. Priority Now"
  echo "3. Review With Me"
  echo "4. Calendar Watch"
  echo "5. Low Priority"
  echo "6. Ignore/Suspicious"
  echo
  echo "Safety and privacy rules:"
  echo "- Do not invent missing source data."
  echo "- Omit unavailable sections, or state \"No source available yet\" only when helpful."
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

if [[ $EXECUTE_REQUESTED -eq 0 ]]; then
  cat <<SUMMARY
Safe briefing formatter dry-run complete.
Input source packet: $INPUT_PATH
Formatter prompt: $prompt_path
Planned final output: $OUTPUT_PATH
Execution backend: not called
SUMMARY
  exit 0
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: --execute requested, but Codex CLI was not found." >&2
  exit 1
fi

codex < "$prompt_path" > "$OUTPUT_PATH"

cat <<SUMMARY
Safe briefing formatter execution complete.
Input source packet: $INPUT_PATH
Formatter prompt: $prompt_path
Final output: $OUTPUT_PATH
Execution backend: Codex CLI
SUMMARY
