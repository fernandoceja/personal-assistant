# Safe Morning Assistant Runner

This document describes `scripts/run-morning-assistant-safe.sh`, the manual-first replacement path for the morning assistant. It is designed for Codex/Hermes-compatible workflows without using the old Claude-based automation path.

## What it does

- Creates a safe briefing/prompt file at `briefings/YYYY-MM-DD-HH-safe.md`.
- Supports these modes:
  - `check-in`
  - `ai-news`
  - `calendar-local`
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

Preferred calendar names:

- Work Schedule
- Calendar
- iCloud
- Google

Captured fields only:

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

If Calendar.app permission is denied, `osascript` is unavailable, or a preferred calendar is missing, the script writes a clear warning and continues.

## Why Google Calendar OAuth is deferred

Google Calendar support is intentionally not implemented yet. Future support should use the preserved `calendar.readonly` patch under:

`docs/patches/google-workspace-calendar-readonly/`

Before enabling it, add an explicit calendar safe-list and verify the OAuth flow uses only read-only calendar scope. The safe runner avoids broad calendar scopes.

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
