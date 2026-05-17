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
- `full-safe` is non-live by default. It includes Google Calendar readonly diagnostics only when the run is explicitly opted in with `--allow-live-google-calendar`.
- Gmail readonly is gated behind the future `--allow-live-gmail-readonly` flag, but live Gmail access is not implemented yet. Default `full-safe` writes a non-live Gmail placeholder only.
- Uses existing prompt files:
  - `prompts/safe-briefing-output-format.md`
  - `prompts/morning-check-in.md`
  - `prompts/morning-ai-briefing-phase-1.md`

## What it deliberately does not do

- Does not use Claude CLI.
- Does not use Gmail by default. Gmail live access is not implemented yet; `--allow-live-gmail-readonly` records a gated/not-implemented placeholder only.
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

Important: default `full-safe` is non-live. The wrapper command below does not perform a live Google Calendar read unless the explicit live-source gate is provided:

```bash
bash run-briefing.sh --slot morning --mode full-safe
```

Google Calendar readonly access requires explicit opt-in for that run:

```bash
bash run-briefing.sh --slot morning --mode full-safe --allow-live-google-calendar
```

Google Calendar writes are never allowed. Gmail is not implemented yet and must not be accessed by the safe runner. No email writes are ever allowed in safe mode.

## Final briefing format contract

The desired final briefing preserves these six top-level sections exactly:

```markdown
## Executive Summary
## Priority Now
## Review With Me
## Calendar Watch
## Low Priority
## Ignore/Suspicious
```

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

Formatting can be validated without live calendar reads by using a source packet created from non-live modes such as `check-in`, `ai-news`, or default `full-safe`. Google Calendar readonly content appears only when a run is explicitly opted in with `--allow-live-google-calendar`.

Run the default full safe briefing through the wrapper:

```bash
bash run-briefing.sh --slot morning --mode full-safe
```

Equivalent default safety model: default `full-safe` is non-live. Add `--allow-live-google-calendar` only when explicitly approving Google Calendar readonly access. Future Gmail readonly requires `--allow-live-gmail-readonly`, but the current implementation still performs no Gmail access and records only a not-implemented placeholder.

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

Google Calendar readonly diagnostic only, explicit live opt-in required:

```bash
bash run-briefing.sh --slot morning --mode calendar-google-readonly --allow-live-google-calendar
```

This mode performs a live readonly Google Calendar event read only when the explicit `--allow-live-google-calendar` gate is present. It never writes Google Calendar events.

Default full safe mode, non-live:

```bash
bash run-briefing.sh --slot morning --mode full-safe
```

This mode does not perform Google Calendar or Gmail live access by default. It writes a Gmail non-live placeholder confirming no Gmail connector, OAuth token check, credential check, or API command was run.

Full safe mode with explicit Google Calendar readonly opt-in:

```bash
bash run-briefing.sh --slot morning --mode full-safe --allow-live-google-calendar
```

With that flag, the runner may include Google Calendar readonly diagnostics before the backend result section. Google Calendar writes are never allowed.

Full safe mode with the future Gmail readonly gate:

```bash
bash run-briefing.sh --slot morning --mode full-safe --allow-live-gmail-readonly
```

This flag is parsed for safety scaffolding only. Gmail readonly support is gated but not implemented yet, so the runner writes a planned/not-implemented placeholder and performs no Gmail connector call, OAuth token check, credential check, or API command. No email writes are ever allowed in safe mode.

If Codex CLI is installed and you explicitly want to run the assembled prompt through Codex, keep the same live-source rule: default `full-safe` is non-live, and Google Calendar readonly requires `--allow-live-google-calendar`.

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

The Google Calendar readonly diagnostic is available only when the run is explicitly opted in with `--allow-live-google-calendar`. Default `full-safe` is non-live and does not access Google Calendar.

Examples:

```bash
bash run-briefing.sh --slot morning --mode full-safe
bash run-briefing.sh --slot morning --mode full-safe --allow-live-google-calendar
```

The first command is non-live. The second command opts in to Google Calendar readonly access for that run only.

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

- No Gmail access. Gmail is not implemented yet and must not be accessed.
- Future Gmail readonly access should require an explicit `--allow-live-gmail-readonly` gate before any Gmail read is allowed.
- No Google Calendar writes, event creation, event edits, deletions, invitations, RSVP changes, or reminder changes.
- No email writes.
- No cron jobs, LaunchAgents, schedules, or recurring automation.
- No iMessage sends.
- No memory writes.
- No credential, token, or client secret modifications.
- No credential, token, or client secret contents should be printed.

Running default `full-safe` is non-live. Running with `--allow-live-google-calendar` performs a live readonly Google Calendar event read and requires separate explicit approval before continuing with the test.

## Why Gmail is deferred

Gmail is not implemented yet. It is deferred because email introduces private content, triage risk, and accidental mutation risk. This runner does not authenticate to Gmail, read Gmail, modify Gmail, or summarize Gmail.

Future Gmail readonly behavior requires an explicit opt-in gate before any Gmail read is allowed:

```bash
--allow-live-gmail-readonly
```

Current behavior: the flag is accepted, but live Gmail access is still not implemented. The runner records: “Gmail readonly support is gated but not implemented yet. No Gmail access performed.” Default `full-safe` records: “Gmail live data not accessed. Run with --allow-live-gmail-readonly to include readonly Gmail diagnostics.”

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

7. Test prompt-only behavior first through the wrapper:

```bash
bash run-briefing.sh --slot morning --mode full-safe
```

8. Only then test explicit execution, still non-live unless the Google Calendar readonly gate is explicitly included:

```bash
bash run-briefing.sh --slot morning --mode full-safe --execute
```
