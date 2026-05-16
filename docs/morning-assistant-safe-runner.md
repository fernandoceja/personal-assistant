# Safe Morning Assistant Runner

This document describes `scripts/run-morning-assistant-safe.sh`, the manual-first replacement path for the morning assistant. It is designed for Codex/Hermes-compatible workflows without using the old Claude-based automation path.

The generated `briefings/YYYY-MM-DD-HH-safe.md` file is an assembled briefing input/source packet unless an explicit backend formatter is used. Dry-run output is not a finished personal-assistant briefing.

## What it does

- Creates a safe briefing input/source packet at `briefings/YYYY-MM-DD-HH-safe.md`.
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
- `full-safe` includes Google Calendar readonly diagnostics after local Apple Calendar diagnostics and before backend result output.
- Uses existing prompt files:
  - `prompts/safe-briefing-output-format.md`
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

Dry-run is the default safe behavior. It assembles the selected prompt/briefing source material and saves it under `briefings/` without calling Codex or any fallback model backend.

Dry-run files clearly separate:

- the final desired briefing format contract
- source material prompts
- diagnostics
- backend result, which remains empty unless an explicit backend formatter is used

Important: `full-safe` now includes Google Calendar readonly diagnostics. That means `scripts/run-morning-assistant-safe.sh --dry-run --mode full-safe` still performs a live readonly Google Calendar event read. It does not call Codex, but the Google Calendar readonly diagnostic is live and requires explicit approval before each test run.

## Final briefing format contract

The desired final briefing uses six top-level sections:

1. Executive Summary
2. Priority Now
3. Review With Me
4. Calendar Watch
5. Low Priority
6. Ignore/Suspicious

The contract lives in `prompts/safe-briefing-output-format.md` and is included in safe runner output as the formatting target for any explicit backend formatter.

Key rules:

- Executive Summary is limited to 3 bullets max.
- Priority Now is for urgent or deadline-driven items only and should include Source, Sender/Event, Subject, Timing, Importance, and Next Action.
- Review With Me is for important but non-urgent items or uncertain legal, immigration, money, school, or work-deadline items.
- Calendar Watch summarizes today/tomorrow calendar source material and highlights work, school, bills, and conflicts when source data supports them.
- Low Priority groups non-urgent items.
- Ignore/Suspicious is omitted or marked as no source available until Gmail or message sources are explicitly approved.
- Sections with no source data should be omitted unless a short "No source available yet" note prevents confusion.
- The formatter must not invent deadlines, senders, bills, email findings, or calendar facts.

Formatting changes can be validated without live calendar reads by running non-live modes such as:

```bash
scripts/run-morning-assistant-safe.sh --dry-run --mode check-in
scripts/run-morning-assistant-safe.sh --dry-run --mode ai-news
```

## Formatting source packets into final briefings

Use `scripts/format-safe-briefing.sh` to turn an existing safe source packet into a formatter-ready prompt, and later, with explicit approval, a final six-section briefing file.

The formatter does not create a new source packet and does not read Gmail, Calendar, iMessage, credentials, or any live data source. It only reads an existing `*-safe.md` source packet and the format contract at `prompts/safe-briefing-output-format.md`.

Source packet and final briefing lifecycle:

- Source packet: `briefings/YYYY-MM-DD-HH-safe.md`
- Dry-run formatter prompt: `briefings/YYYY-MM-DD-HH-final-formatter-prompt.md`
- Final formatted briefing, only with `--execute`: `briefings/YYYY-MM-DD-HH-final.md`

Dry-run formatter preview:

```bash
scripts/format-safe-briefing.sh --input briefings/YYYY-MM-DD-HH-safe.md
```

This creates a formatter-ready prompt sidecar and reports paths/status only. It does not call Codex or Hermes and does not print final private briefing contents to the terminal.

Explicit backend formatting, only after separate approval:

```bash
scripts/format-safe-briefing.sh --input briefings/YYYY-MM-DD-HH-safe.md --execute
```

When `--execute` is used, the formatter calls Codex CLI only. If Codex CLI is missing, it fails safely. Final model output is written to the derived `*-final.md` path and is not appended to the source packet.

Formatting can be validated without live calendar reads by using a source packet created from non-live modes such as `check-in` or `ai-news`. `full-safe` remains live-read gated because it includes Google Calendar readonly diagnostics.

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

This mode includes local Apple Calendar diagnostics and then Google Calendar readonly diagnostics before the backend result section. Even with `--dry-run`, it performs a live readonly Google Calendar event read.

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

The Google Calendar readonly diagnostic is available in the explicit `calendar-google-readonly` mode and is also included in `full-safe` after `write_calendar_local` and before backend result output.

Local Apple Calendar diagnostics and Google Calendar readonly diagnostics are separate sections. Apple Calendar uses local Calendar.app/`osascript` reads; Google Calendar uses the Google Workspace readonly safe-list command below.

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
- No email writes.
- No cron jobs, LaunchAgents, schedules, or recurring automation.
- No iMessage sends.
- No memory writes.
- No credential, token, or client secret modifications.
- No credential, token, or client secret contents should be printed.

Running `calendar-google-readonly` or `full-safe` performs a live readonly Google Calendar event read, even with `--dry-run`, and requires separate explicit approval before continuing with the test.

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
