# Safe Morning Assistant Runner

This document describes `scripts/run-morning-assistant-safe.sh`, the manual-first replacement path for the morning assistant. It is designed for Codex/Hermes-compatible workflows without using the old Claude-based automation path.

## What it does

- Creates a safe briefing/prompt file at `briefings/YYYY-MM-DD-HH-safe.md`.
- Supports these modes:
  - `check-in`
  - `ai-news`
  - `calendar-local`
  - `calendar-google-readonly`
  - `full-safe`
- Defaults to dry-run/prompt-only behavior unless `--execute` is explicitly provided and Codex CLI is available.
- Detects Codex CLI with `command -v codex`.
- Detects the known Hermes test CLI path at `/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.local/bin/hermes`.
- Reads local Apple Calendar/iCalendar data in read-only mode for today and tomorrow.
- Uses existing prompt files:
  - `prompts/morning-check-in.md`
  - `prompts/morning-ai-briefing-phase-1.md`

## What it deliberately does not do

- Does not use Claude CLI.
- Does not use Gmail.
- Does not send iMessages or any other messages.
- Does not update `memory.md` automatically.
- Does not create cron jobs, LaunchAgents, schedules, or recurring automation.
- Does not modify calendar events.
- Does not modify emails.
- Does not use broad Google Calendar scopes.
- Does not add real secrets.
- Does not edit `~/.hermes/.env`, `config.yaml`, shell profiles, or global auth files.
- Does not touch legal, immigration, financial, or private family data.

## Dry-run mode

Dry-run is the default safe behavior. It assembles the selected prompt/briefing content and saves it under `briefings/` without calling Codex or any fallback model backend.

Run the default full safe dry run:

```bash
scripts/run-morning-assistant-safe.sh --dry-run
```

Equivalent default mode:

```bash
scripts/run-morning-assistant-safe.sh --dry-run --mode full-safe
```

## Run each mode

Morning check-in prompt only:

```bash
scripts/run-morning-assistant-safe.sh --dry-run --mode check-in
```

Public AI news prompt only:

```bash
scripts/run-morning-assistant-safe.sh --dry-run --mode ai-news
```

Local Apple Calendar/iCalendar summary only:

```bash
scripts/run-morning-assistant-safe.sh --dry-run --mode calendar-local
```

Google Calendar readonly diagnostic only:

```bash
scripts/run-morning-assistant-safe.sh --dry-run --mode calendar-google-readonly
```

This mode performs a live readonly Google Calendar event read and requires separate explicit approval before each test run.

Full safe mode:

```bash
scripts/run-morning-assistant-safe.sh --dry-run --mode full-safe
```

If Codex CLI is installed and you explicitly want to run the assembled prompt through Codex:

```bash
scripts/run-morning-assistant-safe.sh --execute --mode full-safe
```

If Codex CLI is missing, `--execute` falls back to dry-run/prompt-only output. It does not use Claude or Hermes as a hidden backend.

## Apple Calendar read-only behavior

The `calendar-local` and `full-safe` modes use `osascript` to ask Calendar.app for events from today and tomorrow only.

The local Calendar section now writes diagnostics before event output so failures are explicit instead of vague. It can distinguish:

- Calendar.app permission denied or unavailable
- preferred calendars not found
- preferred calendars found but no events today/tomorrow
- events found successfully

Preferred calendar names:

- Work Schedule
- Calendar
- iCloud
- Google

Safe diagnostic output:

- local calendar names only
- preferred calendars found
- preferred calendars missing
- result status for the today/tomorrow event lookup

Captured event fields only:

- title/summary
- start time
- end time
- location, if available
- all-day status, if available

Excluded fields:

- notes/descriptions
- attendees
- URLs
- meeting links

Location safety note: if a location field appears to contain a URL or common meeting-link provider, the runner redacts that location as `[redacted: link or meeting location]` instead of printing the link.

If Calendar.app permission is denied, `osascript` is unavailable, or a preferred calendar is missing, the script writes a clear diagnostic and continues.

## Google Calendar readonly diagnostic behavior

The `calendar-google-readonly` mode is an explicit, separate diagnostic mode. It is not wired into `full-safe`.

It uses the Hermes Google Workspace skill from:

`/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.hermes`

Exact command used by the runner:

```bash
HERMES_HOME="/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.hermes" "/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/hermes-agent/venv/bin/python3" "/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/google_api.py" calendar safe-list --max 25
```

Allowed event fields only:

- summary
- start
- end
- location

Excluded fields:

- descriptions
- attendees
- guests
- URLs
- meeting links
- attachments
- conference data
- reminders
- creator/organizer metadata

Safety boundary:

- No Gmail access.
- No Google Calendar writes, event creation, event edits, deletions, invitations, RSVP changes, or reminder changes.
- No cron jobs, LaunchAgents, schedules, or recurring automation.
- No iMessage sends.
- No memory writes.
- No credential, token, or client secret modifications.
- No credential, token, or client secret contents should be printed.

Running this mode performs a live readonly event read and requires separate explicit approval before continuing with the test.

## Why Gmail is deferred

Gmail is deferred because the current safe workflow is calendar/check-in/public-news only. Email introduces private content, triage risk, and accidental mutation risk. This runner does not authenticate to Gmail, read Gmail, modify Gmail, or summarize Gmail.

## How Codex CLI is detected

The runner checks:

```bash
command -v codex
```

If found, it records the path and safely attempts:

```bash
codex --version
```

Codex is only called when all of these are true:

- `--execute` was passed.
- Codex CLI was found.
- The script is not in dry-run mode.

No other model backend is used as a fallback.

## Next steps to add Codex CLI safely if missing

1. Review Codex CLI’s official installation instructions.
2. Prefer a project-local or user-local install path where possible.
3. Do not install globally unless Fernando explicitly approves it.
4. Do not place secrets in this repo.
5. Do not edit shell profiles or global auth files from this runner.
6. After installation, verify with:

```bash
command -v codex
codex --version
```

7. Test prompt-only behavior first:

```bash
scripts/run-morning-assistant-safe.sh --dry-run --mode full-safe
```

8. Only then test explicit execution:

```bash
scripts/run-morning-assistant-safe.sh --execute --mode full-safe
```
