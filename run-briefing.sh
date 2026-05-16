#!/bin/bash
# Personal Assistant — Daily Briefing Runner
# Invoked by launchd at 8 AM, 1 PM, and 6 PM PST.
# Runs the Claude Code CLI non-interactively against the daily-briefing prompt.

PROJECT_DIR="/Users/fernandoceja/Documents/AI-Projects/personal-assistant"
CLAUDE_BIN="/Users/fernandoceja/.local/bin/claude"
LOG_FILE="$PROJECT_DIR/logs/briefing-$(date '+%Y-%m-%d').log"
SLOT=""
MODE=""

cd "$PROJECT_DIR"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --slot)
      SLOT="${2:-}"
      shift 2
      ;;
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [[ "$MODE" == "full-safe" ]]; then
  echo "Safe briefing wrapper started."
  [[ -n "$SLOT" ]] && echo "Slot: $SLOT"

  bash scripts/run-morning-assistant-safe.sh --dry-run --mode full-safe

  latest_safe="$(ls -t briefings/*-safe.md 2>/dev/null | head -n 1)"
  if [[ -z "$latest_safe" ]]; then
    echo "ERROR: No safe briefing packet found under briefings/." >&2
    exit 1
  fi

  formatter_log="$(mktemp)"
  if bash scripts/format-safe-briefing.sh --input "$latest_safe" --execute >"$formatter_log" 2>&1; then
    formatter_status=0
  else
    formatter_status=$?
  fi
  rm -f "$formatter_log"

  latest_final="${latest_safe%-safe.md}-final.md"

  echo "Safe briefing wrapper complete."
  echo "Safe packet: $latest_safe"
  echo "Final briefing: $latest_final"
  echo "Formatter status: $formatter_status"

  exit "$formatter_status"
fi

echo "=== Briefing run started: $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG_FILE"

echo "Read CLAUDE.md and memory.md in the current directory. Then read prompts/daily-briefing.md and follow it exactly. Today is $(date '+%Y-%m-%d') and the current time is $(date '+%H:%M %Z'). Use Gmail MCP for email and Google Calendar MCP for events. Write the briefing to briefings/ using YYYY-MM-DD-HH.md format. Send iMessage to fceja9864@icloud.com via osascript. Update memory.md." \
  | "$CLAUDE_BIN" \
      --print \
      --permission-mode bypassPermissions \
      --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
  2>&1 >> "$LOG_FILE"

echo "=== Briefing run finished: $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG_FILE"
