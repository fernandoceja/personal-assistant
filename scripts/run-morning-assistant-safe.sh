#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_CHECK_IN="$ROOT_DIR/prompts/morning-check-in.md"
PROMPT_AI_NEWS="$ROOT_DIR/prompts/morning-ai-briefing-phase-1.md"
PROMPT_SAFE_FORMAT="$ROOT_DIR/prompts/safe-briefing-output-format.md"
BRIEFINGS_DIR="$ROOT_DIR/briefings"
HERMES_KNOWN_PATH="/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.local/bin/hermes"
GOOGLE_HERMES_VENV_PYTHON="/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/hermes-agent/venv/bin/python3"
GOOGLE_HERMES_HOME="/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.hermes"
GOOGLE_API_SCRIPT="$GOOGLE_HERMES_HOME/skills/productivity/google-workspace/scripts/google_api.py"

MODE="full-safe"
DRY_RUN=1
EXECUTE_REQUESTED=0
ALLOW_LIVE_GOOGLE_CALENDAR=0
ALLOW_LIVE_GMAIL_READONLY=0
GMAIL_MOCK=0
GMAIL_MOCK_SCRIPT="$ROOT_DIR/scripts/gmail-safe-list-mock.py"

usage() {
  cat <<'USAGE'
Usage: scripts/run-morning-assistant-safe.sh [--dry-run] [--execute] [--mode MODE] [--allow-live-google-calendar] [--allow-live-gmail-readonly] [--gmail-mock]

Modes:
  check-in                  Assemble the morning check-in prompt.
  ai-news                   Assemble the public AI news prompt.
  calendar-local            Read Apple Calendar/iCalendar events for today and tomorrow only.
  calendar-google-readonly  Run an explicit live Google Calendar readonly safe-list diagnostic.
                            Requires --allow-live-google-calendar.
  full-safe                 Combine check-in, AI news, local calendar, non-live Google Calendar,
                            and non-live Gmail placeholders.
                            Add --allow-live-google-calendar to include Google Calendar readonly diagnostics.
                            --allow-live-gmail-readonly remains live-gated/not implemented.
                            Add --gmail-mock with --allow-live-gmail-readonly to include mock-only Gmail safe-list records.

Defaults:
  --mode full-safe
  --dry-run behavior unless --execute is provided and Codex CLI is available.
  Google Calendar live data is not accessed unless --allow-live-google-calendar is present.
  Gmail live data is not accessed. --allow-live-gmail-readonly records a gated/not-implemented placeholder only.
  Gmail mock data is included only with both --allow-live-gmail-readonly and --gmail-mock.
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
  check-in|ai-news|calendar-local|calendar-google-readonly|full-safe) ;;
  *)
    echo "ERROR: Unsupported mode: $MODE" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ "$MODE" == "calendar-google-readonly" && "$ALLOW_LIVE_GOOGLE_CALENDAR" -ne 1 ]]; then
  echo "ERROR: calendar-google-readonly requires --allow-live-google-calendar." >&2
  usage >&2
  exit 2
fi

if [[ "$GMAIL_MOCK" -eq 1 && "$ALLOW_LIVE_GMAIL_READONLY" -ne 1 ]]; then
  echo "ERROR: --gmail-mock requires --allow-live-gmail-readonly." >&2
  usage >&2
  exit 2
fi

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
    echo "Role: source material for a formatter; not a finished briefing section."
    echo
    cat "$path"
  } >> "$output_file"
}

append_format_contract() {
  require_file "$PROMPT_SAFE_FORMAT"
  {
    echo
    echo "## Final Desired Briefing Format Contract"
    echo
    echo "Source: ${PROMPT_SAFE_FORMAT#$ROOT_DIR/}"
    echo "Role: formatting contract for any explicit backend formatter."
    echo
    cat "$PROMPT_SAFE_FORMAT"
  } >> "$output_file"
}

write_calendar_local() {
  {
    echo
    echo "## Local Apple Calendar Diagnostics"
    echo
    echo "Role: diagnostics/source material for Calendar Watch; not a finished briefing section."
    echo "Scope: Calendar.app events for today and tomorrow only."
    echo "Diagnostic mode: local calendar names only, then preferred calendar status."
    echo "Captured event fields only: title/summary, start time, end time, location when available, all-day status when available."
    echo "Excluded fields: notes/descriptions, attendees, URLs, meeting links."
    echo
  } >> "$output_file"

  if ! command -v osascript >/dev/null 2>&1; then
    echo "Permission/status: unavailable — osascript not found; local Apple Calendar diagnostics skipped." >> "$output_file"
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
set calendarNameLines to {}
set foundPreferredLines to {}
set missingPreferredLines to {}
set eventLines to {}
set foundPreferredCount to 0
set eventCount to 0

on appendLine(theList, theLine)
  set end of theList to theLine
  return theList
end appendLine

on redactUnsafeLocation(locationText)
  set safeLocation to locationText as text
  if safeLocation is "" then return ""
  set lowerLocation to do shell script "printf %s " & quoted form of safeLocation & " | tr '[:upper:]' '[:lower:]'"
  if lowerLocation contains "http://" then return "[redacted: link or meeting location]"
  if lowerLocation contains "https://" then return "[redacted: link or meeting location]"
  if lowerLocation contains "zoom.us" then return "[redacted: link or meeting location]"
  if lowerLocation contains "meet.google" then return "[redacted: link or meeting location]"
  if lowerLocation contains "teams.microsoft" then return "[redacted: link or meeting location]"
  if lowerLocation contains "webex" then return "[redacted: link or meeting location]"
  return safeLocation
end redactUnsafeLocation

try
  tell application "Calendar"
    set allCalendarNames to name of every calendar
    if (count of allCalendarNames) is 0 then
      set calendarNameLines to my appendLine(calendarNameLines, "- [none returned]")
    else
      repeat with calendarName in allCalendarNames
        set calendarNameLines to my appendLine(calendarNameLines, "- " & (calendarName as text))
      end repeat
    end if

    repeat with preferredCalendarName in preferredCalendarNames
      set preferredName to preferredCalendarName as text
      if allCalendarNames contains preferredName then
        set foundPreferredCount to foundPreferredCount + 1
        set foundPreferredLines to my appendLine(foundPreferredLines, "- " & preferredName)
        set targetCalendar to calendar preferredName
        set eventList to every event of targetCalendar whose start date is greater than or equal to startDate and start date is less than endDate
        if (count of eventList) > 0 then
          set eventLines to my appendLine(eventLines, "Calendar: " & preferredName)
          repeat with calendarEvent in eventList
            set eventTitle to summary of calendarEvent
            set eventStart to start date of calendarEvent
            set eventEnd to end date of calendarEvent
            set eventLocation to ""
            try
              set eventLocation to my redactUnsafeLocation(location of calendarEvent)
            end try
            set eventAllDay to "unknown"
            try
              set eventAllDay to ((allday event of calendarEvent) as text)
            end try
            set lineText to "- " & eventTitle & " | start: " & (eventStart as text) & " | end: " & (eventEnd as text) & " | all-day: " & eventAllDay
            if eventLocation is not "" then set lineText to lineText & " | location: " & eventLocation
            set eventLines to my appendLine(eventLines, lineText)
            set eventCount to eventCount + 1
          end repeat
        end if
      else
        set missingPreferredLines to my appendLine(missingPreferredLines, "- " & preferredName)
      end if
    end repeat
  end tell
on error errMsg number errNum
  if errNum is -1743 then
    return "Permission/status: denied — Calendar.app automation access is not allowed. Grant Terminal/iTerm/agent access in System Settings > Privacy & Security > Automation/Calendars, then rerun."
  else
    return "Permission/status: unavailable — Unable to read Calendar.app. " & errMsg & " (" & errNum & ")"
  end if
end try

set outputLines to my appendLine(outputLines, "Permission/status: granted — Calendar.app read completed.")
set outputLines to my appendLine(outputLines, "Window: today and tomorrow only.")
set outputLines to my appendLine(outputLines, "")
set outputLines to my appendLine(outputLines, "Local calendar names:")
repeat with oneLine in calendarNameLines
  set outputLines to my appendLine(outputLines, oneLine as text)
end repeat
set outputLines to my appendLine(outputLines, "")
set outputLines to my appendLine(outputLines, "Preferred calendars found:")
if (count of foundPreferredLines) is 0 then
  set outputLines to my appendLine(outputLines, "- [none]")
else
  repeat with oneLine in foundPreferredLines
    set outputLines to my appendLine(outputLines, oneLine as text)
  end repeat
end if
set outputLines to my appendLine(outputLines, "")
set outputLines to my appendLine(outputLines, "Preferred calendars missing:")
if (count of missingPreferredLines) is 0 then
  set outputLines to my appendLine(outputLines, "- [none]")
else
  repeat with oneLine in missingPreferredLines
    set outputLines to my appendLine(outputLines, oneLine as text)
  end repeat
end if
set outputLines to my appendLine(outputLines, "")

if foundPreferredCount is 0 then
  set outputLines to my appendLine(outputLines, "Result: preferred calendars not found — no event lookup was possible for the configured preferred names.")
else if eventCount is 0 then
  set outputLines to my appendLine(outputLines, "Result: preferred calendars found, but no events were found for today/tomorrow.")
else
  set outputLines to my appendLine(outputLines, "Result: events found successfully.")
  set outputLines to my appendLine(outputLines, "")
  set outputLines to my appendLine(outputLines, "Events:")
  repeat with oneLine in eventLines
    set outputLines to my appendLine(outputLines, oneLine as text)
  end repeat
end if

set AppleScript's text item delimiters to linefeed
set joinedOutput to outputLines as text
set AppleScript's text item delimiters to ""
return joinedOutput
APPLESCRIPT
)" || status=$?

  if [[ $status -ne 0 ]]; then
    {
      echo "Permission/status: unavailable — osascript exited with status $status."
      echo "$calendar_output"
    } >> "$output_file"
  else
    echo "$calendar_output" >> "$output_file"
  fi
}

write_calendar_google_readonly() {
  {
    echo
    echo "## Google Calendar Readonly Diagnostics"
    echo
    echo "Role: live readonly diagnostics/source material for Calendar Watch; not a finished briefing section."
    echo "Scope: live Google Calendar readonly safe-list diagnostic only."
    echo "Exact command: HERMES_HOME=\"$GOOGLE_HERMES_HOME\" \"$GOOGLE_HERMES_VENV_PYTHON\" \"$GOOGLE_API_SCRIPT\" calendar safe-list --max 25"
    echo "Expected safe fields only: summary, start, end, location."
    echo "Excluded fields: descriptions, attendees, guests, URLs, meeting links, attachments, conference data, reminders, creator/organizer metadata."
    echo "Credential safety: credential, token, and client secret contents must never be printed."
    echo
  } >> "$output_file"

  if [[ ! -f "$GOOGLE_API_SCRIPT" ]]; then
    echo "Result: failure — Google API script not found at expected path." >> "$output_file"
    return 0
  fi

  if [[ ! -x "$GOOGLE_HERMES_VENV_PYTHON" ]]; then
    echo "Result: failure — Hermes test venv Python not found or not executable at expected path." >> "$output_file"
    return 0
  fi

  if [[ ! -f "$GOOGLE_HERMES_HOME/google_token.json" ]]; then
    echo "Result: failure — google_token.json not found under GOOGLE_HERMES_HOME." >> "$output_file"
    return 0
  fi

  local google_output=""
  local status=0
  google_output="$(HERMES_HOME="$GOOGLE_HERMES_HOME" "$GOOGLE_HERMES_VENV_PYTHON" "$GOOGLE_API_SCRIPT" calendar safe-list --max 25 2>&1)" || status=$?

  if [[ $status -ne 0 ]]; then
    {
      echo "Result: failure — Google Calendar readonly safe-list exited with status $status."
      echo
      echo "Captured stdout/stderr:"
      echo "$google_output"
    } >> "$output_file"
  else
    {
      echo "Result: success — Google Calendar readonly safe-list completed."
      echo
      echo "Captured stdout/stderr:"
      echo "$google_output"
    } >> "$output_file"
  fi
}

write_google_placeholder() {
  {
    echo
    echo "## Google Calendar Non-Live Placeholder"
    echo
    echo "Role: diagnostics/source material; not a finished briefing section."
    echo "Google Calendar live data not accessed. Run with --allow-live-google-calendar to include readonly Google Calendar."
    echo "No Google Calendar connector, OAuth token check, credential file check, or live API command was run for this section."
  } >> "$output_file"
}

write_gmail_placeholder() {
  {
    echo
    echo "## Gmail Non-Live Placeholder"
    echo
    echo "Role: email diagnostics/source material; not a finished briefing section."
    echo "Gmail live data not accessed. Run with --allow-live-gmail-readonly to include readonly Gmail diagnostics."
    echo "No Gmail connector, OAuth token check, credential check, or API command was run."
    echo "No email reads, writes, archive, delete, label, mark-read, reply, or send actions were performed."
  } >> "$output_file"
}

write_gmail_gated_placeholder() {
  {
    echo
    echo "## Gmail Readonly Planned Placeholder"
    echo
    echo "Role: gated email diagnostics/source material; not a finished briefing section."
    echo "Gmail readonly support is gated but live Gmail is not implemented yet. No Gmail access performed."
    echo "No Gmail connector, OAuth token check, credential check, or API command was run."
    echo "No email reads, writes, archive, delete, label, mark-read, reply, or send actions were performed."
    echo "To include mock-only safe-list records, rerun with --allow-live-gmail-readonly --gmail-mock."
  } >> "$output_file"
}

write_gmail_mock_safe_list() {
  {
    echo
    echo "## Gmail Mock Safe-List"
    echo
    echo "Role: mock-only email source material for the formatter; not live Gmail data and not a finished briefing section."
    echo "Command shape: gmail safe-list --mock --window 48h --max-per-filter 10"
    echo "Executed local equivalent: python3 scripts/gmail-safe-list-mock.py safe-list --mock --window 48h --max-per-filter 10"
    echo "Source: fixtures/gmail-safe-list-mock.json"
    echo "Live Gmail access: not implemented and not performed."
    echo "Safety: no OAuth, token file check, credential check, Gmail connector, Gmail API call, Apple Mail access, email write, or message mutation."
    echo "Allowed fields only: source, category, sender_display, sender_domain, subject, received_at, snippet, labels, has_attachment, matched_filter, triage_hint, safety_notes."
    echo "Excluded fields: full bodies, attachments, attachment names/IDs/contents, raw headers, tracking links, unsubscribe links, tokens, OTPs, account numbers, full URLs, message IDs, thread IDs, raw Gmail API responses, To/Cc/Bcc, OAuth/token/config paths or contents."
    echo
    echo "Records:"
  } >> "$output_file"

  if [[ ! -f "$GMAIL_MOCK_SCRIPT" ]]; then
    echo "Result: failure — mock Gmail safe-list script not found." >> "$output_file"
    return 0
  fi

  local gmail_mock_output=""
  local status=0
  gmail_mock_output="$(python3 "$GMAIL_MOCK_SCRIPT" safe-list --mock --window 48h --max-per-filter 10 2>&1)" || status=$?

  if [[ $status -ne 0 ]]; then
    {
      echo "Result: failure — mock Gmail safe-list exited with status $status."
      echo "$gmail_mock_output"
    } >> "$output_file"
  else
    {
      echo "Result: success — mock Gmail safe-list completed."
      echo "GMAIL_MOCK_SAFE_LIST_JSON_BEGIN"
      echo "$gmail_mock_output"
      echo "GMAIL_MOCK_SAFE_LIST_JSON_END"
    } >> "$output_file"
  fi
}

write_ai_news_note() {
  {
    echo
    echo "## AI News Execution Note"
    echo
    echo "Role: diagnostics/source material; not a finished briefing section."
    echo "This runner assembles the existing public AI news prompt. If no approved web research backend is configured, treat this as prompt-ready input rather than a completed research briefing."
  } >> "$output_file"
}

{
  echo "# Safe Morning Assistant Input Packet — $today_stamp"
  echo
  echo "Packet type: assembled briefing input/source packet."
  echo "Final briefing status: not a finished briefing unless an explicit backend formatter writes content under Backend Result."
  echo "Mode: $MODE"
  echo "Dry run: $DRY_RUN"
  echo "Live Google Calendar allowed: $ALLOW_LIVE_GOOGLE_CALENDAR"
  echo "Live Gmail readonly allowed: $ALLOW_LIVE_GMAIL_READONLY"
  echo "Gmail mock enabled: $GMAIL_MOCK"
  echo "Codex CLI: ${codex_path:-not found}"
  echo "Codex version: $codex_version"
  echo "Hermes known CLI: ${hermes_path:-not found at known test path}"
  echo
  echo "Safety contract: read-only; no private email access; no message sending; no automatic persistent-state updates; no calendar writes; no scheduling; no email writes."
} > "$output_file"

case "$MODE" in
  check-in)
    append_format_contract
    append_prompt_file "Source Material - Morning Check-in Prompt" "$PROMPT_CHECK_IN"
    ;;
  ai-news)
    append_format_contract
    append_prompt_file "Source Material - Public AI News Prompt" "$PROMPT_AI_NEWS"
    write_ai_news_note
    ;;
  calendar-local)
    append_format_contract
    write_calendar_local
    write_google_placeholder
    write_gmail_placeholder
    ;;
  calendar-google-readonly)
    append_format_contract
    write_calendar_google_readonly
    ;;
  full-safe)
    append_format_contract
    append_prompt_file "Source Material - Morning Check-in Prompt" "$PROMPT_CHECK_IN"
    append_prompt_file "Source Material - Public AI News Prompt" "$PROMPT_AI_NEWS"
    write_ai_news_note
    write_calendar_local
    if [[ "$ALLOW_LIVE_GOOGLE_CALENDAR" -eq 1 ]]; then
      write_calendar_google_readonly
    else
      write_google_placeholder
    fi
    if [[ "$ALLOW_LIVE_GMAIL_READONLY" -eq 1 ]]; then
      if [[ "$GMAIL_MOCK" -eq 1 ]]; then
        write_gmail_mock_safe_list
      else
        write_gmail_gated_placeholder
      fi
    else
      write_gmail_placeholder
    fi
    ;;
esac

{
  echo
  echo "## Backend Result"
  echo
  echo "Role: final formatted briefing only when an explicit backend formatter is used."
  echo
} >> "$output_file"

if [[ $DRY_RUN -eq 1 ]]; then
  {
    echo "Dry-run/input-packet mode. No execution backend was called; this file is source material, not a finished briefing."
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
Live Google Calendar allowed: $ALLOW_LIVE_GOOGLE_CALENDAR
Live Gmail readonly allowed: $ALLOW_LIVE_GMAIL_READONLY
Gmail mock enabled: $GMAIL_MOCK
Output: ${output_file#$ROOT_DIR/}
Codex CLI: ${codex_path:-not found}
Hermes known CLI: ${hermes_path:-not found at known test path}
SUMMARY
