#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_CHECK_IN="$ROOT_DIR/prompts/morning-check-in.md"
PROMPT_AI_NEWS="$ROOT_DIR/prompts/morning-ai-briefing-phase-1.md"
BRIEFINGS_DIR="$ROOT_DIR/briefings"
HERMES_KNOWN_PATH="/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.local/bin/hermes"

MODE="full-safe"
DRY_RUN=1
EXECUTE_REQUESTED=0

usage() {
  cat <<'USAGE'
Usage: scripts/run-morning-assistant-safe.sh [--dry-run] [--execute] [--mode MODE]

Modes:
  check-in        Assemble the morning check-in prompt.
  ai-news         Assemble the public AI news prompt.
  calendar-local  Read Apple Calendar/iCalendar events for today and tomorrow only.
  full-safe       Combine check-in, AI news, local calendar, and Google Calendar placeholder.

Defaults:
  --mode full-safe
  --dry-run behavior unless --execute is provided and Codex CLI is available.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --execute)
      EXECUTE_REQUESTED=1
      DRY_RUN=0
      shift
      ;;
    --mode)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --mode requires a value." >&2
        usage >&2
        exit 2
      fi
      MODE="$2"
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

case "$MODE" in
  check-in|ai-news|calendar-local|full-safe) ;;
  *)
    echo "ERROR: Unsupported mode: $MODE" >&2
    usage >&2
    exit 2
    ;;
esac

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "ERROR: Required file not found: $path" >&2
    exit 1
  fi
}

codex_path=""
if command -v codex >/dev/null 2>&1; then
  codex_path="$(command -v codex)"
fi

hermes_path=""
if [[ -x "$HERMES_KNOWN_PATH" ]]; then
  hermes_path="$HERMES_KNOWN_PATH"
fi

codex_version="not available"
if [[ -n "$codex_path" ]]; then
  codex_version="$($codex_path --version 2>/dev/null | head -n 1 || true)"
  [[ -n "$codex_version" ]] || codex_version="not available"
fi

if [[ $EXECUTE_REQUESTED -eq 1 && -z "$codex_path" ]]; then
  DRY_RUN=1
fi

now_stamp="$(date +%Y-%m-%d-%H)"
today_stamp="$(date +%Y-%m-%d)"
output_file="$BRIEFINGS_DIR/${now_stamp}-safe.md"
mkdir -p "$BRIEFINGS_DIR"

append_prompt_file() {
  local label="$1"
  local path="$2"
  require_file "$path"
  {
    echo
    echo "## $label"
    echo
    echo "Source: ${path#$ROOT_DIR/}"
    echo
    cat "$path"
  } >> "$output_file"
}

write_calendar_local() {
  {
    echo
    echo "## Local Apple Calendar Summary"
    echo
    echo "Scope: Calendar.app events for today and tomorrow only."
    echo "Captured fields only: title/summary, start time, end time, location when available, all-day status when available."
    echo "Excluded fields: notes/descriptions, attendees, URLs, meeting links."
    echo
  } >> "$output_file"

  if ! command -v osascript >/dev/null 2>&1; then
    echo "WARNING: osascript not found; local Apple Calendar summary skipped." >> "$output_file"
    return 0
  fi

  local calendar_output=""
  local status=0
  calendar_output="$(osascript 2>&1 <<'APPLESCRIPT'
set preferredCalendarNames to {"Work Schedule", "Calendar", "iCloud", "Google"}
set startDate to current date
set time of startDate to 0
set endDate to startDate + (2 * days)
set outputLines to {}

try
  tell application "Calendar"
    repeat with calendarName in preferredCalendarNames
      try
        set targetCalendar to calendar (calendarName as text)
        set eventList to every event of targetCalendar whose start date is greater than or equal to startDate and start date is less than endDate
        if (count of eventList) > 0 then
          set end of outputLines to "Calendar: " & (calendarName as text)
          repeat with calendarEvent in eventList
            set eventTitle to summary of calendarEvent
            set eventStart to start date of calendarEvent
            set eventEnd to end date of calendarEvent
            set eventLocation to ""
            try
              set eventLocation to location of calendarEvent
            end try
            set eventAllDay to "unknown"
            try
              set eventAllDay to ((allday event of calendarEvent) as text)
            end try
            set lineText to "- " & eventTitle & " | start: " & (eventStart as text) & " | end: " & (eventEnd as text) & " | all-day: " & eventAllDay
            if eventLocation is not "" then set lineText to lineText & " | location: " & eventLocation
            set end of outputLines to lineText
          end repeat
        end if
      on error
        -- Missing calendars are expected; continue safely.
      end try
    end repeat
  end tell
on error errMsg number errNum
  return "WARNING: Unable to read Calendar.app events. Calendar permission may be denied or Calendar.app may be unavailable. " & errMsg & " (" & errNum & ")"
end try

if (count of outputLines) is 0 then
  return "No events found in preferred local calendars for today/tomorrow, or preferred calendars were unavailable."
else
  set AppleScript's text item delimiters to linefeed
  set joinedOutput to outputLines as text
  set AppleScript's text item delimiters to ""
  return joinedOutput
end if
APPLESCRIPT
)" || status=$?

  if [[ $status -ne 0 ]]; then
    {
      echo "WARNING: Unable to read Calendar.app events. Calendar permission may be denied or Calendar.app may be unavailable."
      echo "$calendar_output"
    } >> "$output_file"
  else
    echo "$calendar_output" >> "$output_file"
  fi
}

write_google_placeholder() {
  {
    echo
    echo "## Google Calendar Placeholder"
    echo
    echo "Google Calendar OAuth is not implemented in this safe runner. Future support must use the preserved calendar.readonly patch under docs/patches/google-workspace-calendar-readonly/ plus an explicit calendar safe-list. No broad calendar scope is used here."
  } >> "$output_file"
}

write_ai_news_note() {
  {
    echo
    echo "## AI News Execution Note"
    echo
    echo "This runner assembles the existing public AI news prompt. If no approved web research backend is configured, treat this as prompt-ready input rather than a completed research briefing."
  } >> "$output_file"
}

{
  echo "# Safe Morning Assistant Run — $today_stamp"
  echo
  echo "Mode: $MODE"
  echo "Dry run: $DRY_RUN"
  echo "Codex CLI: ${codex_path:-not found}"
  echo "Codex version: $codex_version"
  echo "Hermes known CLI: ${hermes_path:-not found at known test path}"
  echo
  echo "Safety contract: read-only; no private email access; no message sending; no automatic persistent-state updates; no calendar writes; no scheduling."
} > "$output_file"

case "$MODE" in
  check-in)
    append_prompt_file "Morning Check-in Prompt" "$PROMPT_CHECK_IN"
    ;;
  ai-news)
    append_prompt_file "Public AI News Prompt" "$PROMPT_AI_NEWS"
    write_ai_news_note
    ;;
  calendar-local)
    write_calendar_local
    write_google_placeholder
    ;;
  full-safe)
    append_prompt_file "Morning Check-in Prompt" "$PROMPT_CHECK_IN"
    append_prompt_file "Public AI News Prompt" "$PROMPT_AI_NEWS"
    write_ai_news_note
    write_calendar_local
    write_google_placeholder
    ;;
esac

{
  echo
  echo "## Backend Result"
  echo
} >> "$output_file"

if [[ $DRY_RUN -eq 1 ]]; then
  {
    echo "Dry-run/prompt-only mode. No execution backend was called."
    if [[ $EXECUTE_REQUESTED -eq 1 && -z "$codex_path" ]]; then
      echo "Codex CLI not found; saved assembled prompt instead."
    fi
  } >> "$output_file"
elif [[ -n "$codex_path" ]]; then
  {
    echo "Codex CLI detected at: $codex_path"
    echo "Running Codex with the assembled prompt."
    echo
    "$codex_path" < "$output_file"
  } >> "$output_file" 2>&1
else
  {
    echo "Codex CLI not found; saved assembled prompt instead."
    echo "No fallback execution backend was used."
  } >> "$output_file"
fi

cat <<SUMMARY
Safe morning assistant runner complete.
Mode: $MODE
Dry run: $DRY_RUN
Output: ${output_file#$ROOT_DIR/}
Codex CLI: ${codex_path:-not found}
Hermes known CLI: ${hermes_path:-not found at known test path}
SUMMARY
