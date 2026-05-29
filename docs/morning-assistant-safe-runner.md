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
- Detects the known Hermes test CLI path at `~/Projects/hermes-agent-test/home/.local/bin/hermes`.
- Reads local Apple Calendar/iCalendar data in read-only mode for today and tomorrow.
- `full-safe` is non-live by default. It includes Google Calendar readonly diagnostics only when the run is explicitly opted in with `--allow-live-google-calendar`.
- Gmail readonly live safe-list access is gated behind `--allow-live-gmail-readonly`. Default `full-safe` writes a non-live Gmail placeholder only.
- Mock Gmail safe-list data is available only when both `--allow-live-gmail-readonly` and `--gmail-mock` are present. It reads only `fixtures/gmail-safe-list-mock.json` through `scripts/gmail-safe-list-mock.py` and performs no OAuth, token, credential, connector, Gmail API, or Apple Mail access.
- Uses existing prompt files:
  - `prompts/safe-briefing-output-format.md`
  - `prompts/morning-check-in.md`
  - `prompts/morning-ai-briefing-phase-1.md`

## What it deliberately does not do

- Does not use Claude CLI.
- Does not use Gmail by default. `--allow-live-gmail-readonly` runs only the Gmail readonly safe-list command; `--gmail-mock` keeps the path fixture-only.
- Does not run Gmail OAuth, read Gmail tokens, check Gmail credentials, call Gmail APIs, or access Apple Mail by default. Live Gmail access is only the explicit `gmail safe-list` command; mock Gmail mode reads only checked-in fixture data.
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

Google Calendar writes are never allowed. Gmail is accessed only when explicitly opted in with `--allow-live-gmail-readonly`, and then only through Gmail readonly safe-list. No email writes are ever allowed in safe mode.

## Manual live morning wrapper

For an approved, manual/run-on-demand live read-only morning briefing, use:

```bash
scripts/run-live-morning-briefing.sh
```

This convenience wrapper intentionally does only this command:

```bash
bash run-briefing.sh --slot morning --mode full-safe --allow-live-google-calendar --allow-live-gmail-readonly
```

It is not scheduled yet. Do not add cron jobs, LaunchAgents, or recurring automation until that is separately approved.

Safety boundaries for this wrapper:

- It does not send iMessage.
- It does not update `memory.md`.
- It does not create, modify, or delete calendar events.
- It does not run Gmail legacy commands.
- It opts in only to Google Calendar readonly and Gmail readonly safe-list access already supported by `full-safe`.
- It validates that safe and final briefing files are generated through the existing `run-briefing.sh` full-safe validation path.

## Drive / Docs / Sheets boundary

The safe morning runner does not use Google Drive, Docs, or Sheets by default.
Those capabilities are prepared only in the isolated Hermes Google Workspace
skill for explicitly requested document work.

Default runner behavior remains:

- No Drive search/list.
- No Docs read/export.
- No Sheets read.
- No Drive uploads.
- No Docs or Sheets creation/update.
- No Drive delete, move, share, or permission changes.
- No broad `https://www.googleapis.com/auth/drive` scope.

When a future run explicitly needs Drive/Docs/Sheets, use the gated Hermes
commands documented in `docs/hermes-google-workspace-controlled-write.md`; do
not fold those operations into the morning briefing runner without separate
approval.

## Hermes/Open WebUI Trigger Prompt

Use this prompt when Hermes or Open WebUI should request the terminal-backed live read-only briefing workflow:

```text
Run the personal-assistant terminal-backed safe morning briefing workflow from:
~/Projects/personal-assistant

Use only:
scripts/run-live-morning-briefing.sh

The workflow may read Gmail through the readonly safe-list path and read Google Calendar for today/tomorrow through the approved readonly path. Summarize only in the existing six-section briefing format. Do not send, reply, draft, archive, trash, label, or otherwise modify Gmail. Do not create, update, or delete Calendar events. Do not create cron jobs, schedules, LaunchAgents, recurring automations, or gateway allow-all access. Do not modify memory.md, OAuth files, tokens, credentials, Hermes backend config, or any other project. Report the generated briefing file path and the read-only validation result.
```

This prompt is for manual/run-on-demand operation. It does not grant approval for live write flags, scheduling, Gateway exposure, or backend config changes.

## Review-only iMessage draft helper

After a final briefing exists, create a short local iMessage-ready draft text file with:

```bash
scripts/create-imessage-briefing-draft.py
```

To use a specific final briefing instead of the latest `briefings/*-final.md`, run:

```bash
scripts/create-imessage-briefing-draft.py briefings/YYYY-MM-DD-HH-final.md
```

The helper reads only the final briefing file. It does not read the safe packet, does not access Gmail, does not access Google Calendar, does not touch credentials, and does not update `memory.md`.

Output is written to:

```text
briefings/YYYY-MM-DD-HH-imessage-draft.txt
```

The draft is review-only. It is a local text file preview for Fernando to inspect/edit manually. It does not send an iMessage, does not open Messages.app, does not run `osascript`, and does not create cron jobs, LaunchAgents, or any scheduling.

## Explicit-send iMessage draft helper

After Fernando has reviewed the local draft file, preview the draft with the explicit-send helper:

```bash
scripts/send-imessage-briefing-draft.py
```

To preview a specific reviewed draft instead of the latest `briefings/*-imessage-draft.txt`, run:

```bash
scripts/send-imessage-briefing-draft.py briefings/YYYY-MM-DD-HH-imessage-draft.txt
```

Default behavior is dry-run/no-send. In dry-run mode, the helper prints the draft preview and does not call `osascript`, does not open or send through Messages.app, does not access Gmail, does not access Google Calendar, does not read the safe packet, does not touch credentials, and does not update `memory.md`.

Sending is manual and requires both an explicit approval flag and an explicit recipient:

```bash
export SELF_BRIEFING_RECIPIENT="<your-approved-self-email>"
scripts/send-imessage-briefing-draft.py briefings/YYYY-MM-DD-HH-imessage-draft.txt \
  --send-approved-draft \
  --recipient "$SELF_BRIEFING_RECIPIENT" \
  --confirm "SEND DAILY BRIEF TO FERNANDO"
```

Recipient may also be a Messages/iMessage buddy name if that is how Messages.app resolves the contact. It must exactly match `SELF_BRIEFING_RECIPIENT`:

```bash
export SELF_BRIEFING_RECIPIENT="<your-approved-self-email-or-buddy-name>"
scripts/send-imessage-briefing-draft.py --send-approved-draft \
  --recipient "$SELF_BRIEFING_RECIPIENT" \
  --confirm "SEND DAILY BRIEF TO FERNANDO"
```

Safety boundaries for explicit-send:

- The helper reads only `*-imessage-draft.txt` files.
- It refuses safe packets and non-draft inputs.
- It refuses send mode when `--recipient` is missing.
- It refuses drafts over 900 characters.
- It refuses drafts containing links, message IDs, thread IDs, attachment markers, or raw Gmail/API markers.
- It never auto-generates and sends in one step; create/review the draft first, then run the send helper separately.

Scheduling is still not implemented. This is not automatic daily delivery yet. Do not add cron jobs, LaunchAgents, or recurring automation until that is separately approved.

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

Equivalent default safety model: default `full-safe` is non-live. Add `--allow-live-google-calendar` only when explicitly approving Google Calendar readonly access. Add `--allow-live-gmail-readonly` only when explicitly approving Gmail readonly safe-list access.

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

Full safe mode with explicit Gmail readonly safe-list opt-in:

```bash
bash run-briefing.sh --slot morning --mode full-safe --allow-live-gmail-readonly
```

This flag runs live Gmail readonly safe-list only, using the Hermes Google Workspace skill command below. It does not run Gmail search/get/labels/send/reply/modify, fetch full bodies, download attachments, print message IDs/thread IDs, or access Apple Mail. No email writes are ever allowed in safe mode.

Exact command used by the runner:

```bash
HOME="~/Projects/hermes-agent-test/home" HERMES_HOME="~/Projects/hermes-agent-test/home/.hermes" "~/Projects/hermes-agent-test/home/.hermes/venvs/google-workspace/bin/python" "~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/google_api.py" gmail safe-list --window 48h --max-per-filter 10
```

The safe packet stores only normalized safe-list records between Gmail safe-list markers. The final formatter maps those records into the six required sections and never prints raw Gmail JSON, message IDs, thread IDs, full bodies, attachment details, credentials, or raw Gmail API payloads.

Full safe mode with mock Gmail safe-list records:

```bash
bash run-briefing.sh --slot morning --mode full-safe --allow-live-gmail-readonly --gmail-mock
```

This still performs no live Gmail access. The runner executes the local mock equivalent of:

```bash
gmail safe-list --mock --window 48h --max-per-filter 10
```

Current local equivalent:

```bash
python3 scripts/gmail-safe-list-mock.py safe-list --mock --window 48h --max-per-filter 10
```

The mock command reads only `fixtures/gmail-safe-list-mock.json` and emits normalized records with these allowed fields only: `source`, `category`, `sender_display`, `sender_domain`, `subject`, `received_at`, `snippet` capped to 200 characters, `labels`, `has_attachment`, `matched_filter`, `triage_hint`, and `safety_notes`.

Excluded fields: full message bodies, attachments, attachment names/IDs/contents, raw headers, tracking links, unsubscribe links, auth/security tokens, one-time passcodes, account numbers, full URLs, message IDs, thread IDs, raw Gmail API responses, To/Cc/Bcc, and OAuth/token/config paths or contents.

Mock Gmail categories:

- Immigration / USCIS / legal
- Work / Apple
- School / UMGC
- Bills / T-Mobile / HelloStorage
- Finances / Rocket Money / Fidelity / IBKR / E*TRADE / BofA / IHSS
- Suspicious/phishing
- Low priority / routine

Triage mapping:

- Priority Now: deadlines, payment failed/past due, service interruption, work schedule action, school deadline, fraud/account lock, legal/immigration deadline.
- Review With Me: immigration/legal ambiguity, financial aid, statements/tax forms, unclear work/school actions, security alerts that may be legitimate.
- Calendar Watch: only clear date/time commitments; the runner does not create events.
- Low Priority: routine confirmations, newsletters, routine notices.
- Ignore/Suspicious: phishing, fake billing, credential pressure, suspicious attachments, unknown sender with legal/banking/immigration language.

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

`~/Projects/hermes-agent-test/home/.hermes`

Exact command used by the runner:

```bash
HERMES_HOME="~/Projects/hermes-agent-test/home/.hermes" "~/Projects/hermes-agent-test/hermes-agent/venv/bin/python3" "~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/google_api.py" calendar safe-list --max 25
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

- No default Gmail access. Gmail readonly access requires `--allow-live-gmail-readonly` and uses only `gmail safe-list`.
- Gmail readonly access requires an explicit `--allow-live-gmail-readonly` gate before any Gmail read is allowed.
- No Google Calendar writes, event creation, event edits, deletions, invitations, RSVP changes, or reminder changes.
- No email writes.
- No cron jobs, LaunchAgents, schedules, or recurring automation.
- No iMessage sends.
- No memory writes.
- No credential, token, or client secret modifications.
- No credential, token, or client secret contents should be printed.

Running default `full-safe` is non-live. Running with `--allow-live-google-calendar` performs a live readonly Google Calendar event read and requires separate explicit approval before continuing with the test.

## Gmail readonly safe-list behavior

Gmail remains non-live by default because email introduces private content, triage risk, and accidental mutation risk. Live Gmail readonly is available only through the normalized safe-list connector and only after an explicit opt-in gate for that run.

Gmail readonly behavior requires this explicit opt-in gate before any Gmail read is allowed:

```bash
--allow-live-gmail-readonly
```

Current behavior: the flag runs only `gmail safe-list --window 48h --max-per-filter 10` with the configured Hermes HOME/HERMES_HOME context. Default `full-safe` records: “Gmail live data not accessed. Run with --allow-live-gmail-readonly to include readonly Gmail diagnostics.”

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
