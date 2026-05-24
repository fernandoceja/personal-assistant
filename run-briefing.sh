#!/bin/bash
# Personal Assistant — Daily Briefing Runner
# Invoked by launchd at 8 AM, 1 PM, and 6 PM PST.
# Runs the Claude Code CLI non-interactively against the daily-briefing prompt.
#
# Approved manual daily command:
#   scripts/run-live-morning-briefing.sh
#
# Legacy non-safe path below may send iMessage and update memory.md through
# Claude CLI. Do not use it unless Fernando explicitly approves that legacy
# behavior for the run. The full-safe mode remains the default approved path for
# local operator validation.

PROJECT_DIR="/Users/fernandoceja/Documents/AI-Projects/personal-assistant"
CLAUDE_BIN="/Users/fernandoceja/.local/bin/claude"
LOG_FILE="$PROJECT_DIR/logs/briefing-$(date '+%Y-%m-%d').log"
SLOT=""
MODE=""
ALLOW_LIVE_GOOGLE_CALENDAR=0
ALLOW_LIVE_GMAIL_READONLY=0
GMAIL_MOCK=0

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
    --allow-live-google-calendar)
      ALLOW_LIVE_GOOGLE_CALENDAR=1
      shift
      ;;
    --allow-live-gmail-readonly)
      ALLOW_LIVE_GMAIL_READONLY=1
      shift
      ;;
    --gmail-mock)
      GMAIL_MOCK=1
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [[ "$MODE" == "full-safe" ]]; then
  echo "Safe briefing wrapper started."
  [[ -n "$SLOT" ]] && echo "Slot: $SLOT"

  runner_args=(--dry-run --mode full-safe)
  if [[ "$ALLOW_LIVE_GOOGLE_CALENDAR" -eq 1 ]]; then
    runner_args+=(--allow-live-google-calendar)
  fi
  if [[ "$ALLOW_LIVE_GMAIL_READONLY" -eq 1 ]]; then
    runner_args+=(--allow-live-gmail-readonly)
  fi
  if [[ "$GMAIL_MOCK" -eq 1 ]]; then
    runner_args+=(--gmail-mock)
  fi

  bash scripts/run-morning-assistant-safe.sh "${runner_args[@]}"

  latest_safe="$(ls -t briefings/*-safe.md 2>/dev/null | head -n 1)"
  if [[ -z "$latest_safe" ]]; then
    echo "ERROR: No safe briefing packet found under briefings/." >&2
    exit 1
  fi

  formatter_log="$(mktemp)"
  if bash scripts/format-safe-briefing.sh --input "$latest_safe" >"$formatter_log" 2>&1; then
    formatter_status=0
  else
    formatter_status=$?
  fi
  rm -f "$formatter_log"

  latest_final="${latest_safe%-safe.md}-final.md"

  validation_status=0
  if [[ ! -f "$latest_safe" ]]; then
    echo "ERROR: Safe packet was not generated: $latest_safe" >&2
    validation_status=1
  fi
  if [[ ! -f "$latest_final" ]]; then
    echo "ERROR: Final briefing was not generated: $latest_final" >&2
    validation_status=1
  fi

  for heading in "Executive Summary" "Priority Now" "Review With Me" "Calendar Watch" "Low Priority" "Ignore/Suspicious"; do
    if [[ -f "$latest_final" ]] && grep -Fq "## $heading" "$latest_final"; then
      echo "Heading validation: $heading: Pass"
    else
      echo "Heading validation: $heading: Fail" >&2
      validation_status=1
    fi
  done

  if [[ "$ALLOW_LIVE_GOOGLE_CALENDAR" -eq 0 && -f "$latest_safe" ]]; then
    if grep -Eq 'Google Calendar readonly safe-list|calendar safe-list --max' "$latest_safe"; then
      echo "ERROR: Default full-safe packet contains live Google Calendar path markers." >&2
      validation_status=1
    fi
    if ! grep -Fq "Google Calendar live data not accessed. Run with --allow-live-google-calendar to include readonly Google Calendar." "$latest_safe"; then
      echo "ERROR: Default full-safe packet is missing the Google Calendar non-live placeholder." >&2
      validation_status=1
    fi
  fi

  if [[ "$ALLOW_LIVE_GMAIL_READONLY" -eq 0 && -f "$latest_safe" ]]; then
    if grep -Eq 'Gmail Live Safe-List|gmail\.readonly|google_token\.json|GMAIL_SAFE_LIST_JSON_BEGIN|GMAIL_MOCK_SAFE_LIST_JSON_BEGIN' "$latest_safe"; then
      echo "ERROR: Default full-safe packet contains live Gmail path markers." >&2
      validation_status=1
    fi
    if grep -Ei 'Gmail.*OAuth token check|OAuth token check.*Gmail' "$latest_safe" | grep -Fv "No Gmail connector, OAuth token check, credential check, or API command was run." >/dev/null; then
      echo "ERROR: Default full-safe packet contains a Gmail OAuth token check marker outside the non-live placeholder." >&2
      validation_status=1
    fi
    if ! grep -Fq "Gmail live data not accessed. Run with --allow-live-gmail-readonly to include readonly Gmail diagnostics." "$latest_safe"; then
      echo "ERROR: Default full-safe packet is missing the Gmail non-live placeholder." >&2
      validation_status=1
    fi
    if ! grep -Fq "No Gmail connector, OAuth token check, credential check, or API command was run." "$latest_safe"; then
      echo "ERROR: Default full-safe packet is missing the Gmail no-access confirmation." >&2
      validation_status=1
    fi
  fi

  if [[ "$ALLOW_LIVE_GMAIL_READONLY" -eq 1 && "$GMAIL_MOCK" -eq 0 && -f "$latest_safe" ]]; then
    if ! grep -Fq "## Gmail Live Safe-List" "$latest_safe" || ! grep -Fq "GMAIL_SAFE_LIST_JSON_BEGIN" "$latest_safe"; then
      echo "ERROR: Live Gmail run did not include the Gmail safe-list section and marker." >&2
      validation_status=1
    fi
    if grep -Eq 'GMAIL_MOCK_SAFE_LIST_JSON_BEGIN|gmail-safe-list-mock\.py|--mock' "$latest_safe"; then
      echo "ERROR: Live Gmail run contains mock Gmail markers." >&2
      validation_status=1
    fi
    if [[ -f "$latest_final" ]] && grep -Eq 'GMAIL_SAFE_LIST_JSON|GMAIL_MOCK_SAFE_LIST_JSON|^\s*[\[{]|"(id|threadId|payload|raw|body|attachment)' "$latest_final"; then
      echo "ERROR: Final briefing exposes raw Gmail JSON or excluded Gmail fields." >&2
      validation_status=1
    fi
  fi

  if [[ "$ALLOW_LIVE_GMAIL_READONLY" -eq 1 && "$GMAIL_MOCK" -eq 1 && -f "$latest_safe" ]]; then
    if ! grep -Fq "GMAIL_MOCK_SAFE_LIST_JSON_BEGIN" "$latest_safe"; then
      echo "ERROR: Gmail mock run did not include mock safe-list records." >&2
      validation_status=1
    fi
    if grep -Fq "GMAIL_SAFE_LIST_JSON_BEGIN" "$latest_safe" || grep -Fq "## Gmail Live Safe-List" "$latest_safe"; then
      echo "ERROR: Gmail mock run contains live Gmail markers." >&2
      validation_status=1
    fi
  fi

  if [[ -f "$latest_safe" ]] && grep -Eiq 'Gmail|iMessage|memory\.md|send msgBody|google_token\.json' "$latest_safe"; then
    echo "Safety validation note: safe packet contains prohibited-source terms only as static safety/prompt text; no connector call is made by this wrapper."
  fi

  echo "Safe briefing wrapper complete."
  echo "Safe packet: $latest_safe"
  echo "Final briefing: $latest_final"
  echo "Formatter status: $formatter_status"

  if [[ $formatter_status -ne 0 ]]; then
    validation_status=$formatter_status
  fi

  exit "$validation_status"
fi

echo "=== Briefing run started: $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG_FILE"

echo "Read CLAUDE.md and memory.md in the current directory. Then read prompts/daily-briefing.md and follow it exactly. Today is $(date '+%Y-%m-%d') and the current time is $(date '+%H:%M %Z'). Use Gmail MCP for email and Google Calendar MCP for events. Write the briefing to briefings/ using YYYY-MM-DD-HH.md format. Send iMessage to fceja9864@icloud.com via osascript. Update memory.md." \
  | "$CLAUDE_BIN" \
      --print \
      --permission-mode bypassPermissions \
      --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
  2>&1 >> "$LOG_FILE"

echo "=== Briefing run finished: $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG_FILE"
