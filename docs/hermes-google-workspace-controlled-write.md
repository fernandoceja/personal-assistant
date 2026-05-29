# Hermes Google Workspace Controlled Write Status

This note records the controlled-write state for the isolated Hermes Google
Workspace skill after the 2026-05-23 Drive/Docs/Sheets preparation. It does not change
the Personal Assistant safe runner defaults: read-only and dry-run paths remain
the default unless Fernando explicitly approves a live write and the matching
gate flag is present.

## Isolated profile

Use the isolated Hermes profile for this setup:

```bash
HOME=~/Projects/hermes-agent-test/home
HERMES_HOME=~/Projects/hermes-agent-test/home/.hermes
```

Installed Google Workspace skill:

```text
~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/
```

## Current authorized scopes

The existing Google OAuth token was safely checked without printing token
contents. It currently includes these previously approved controlled Gmail and
Calendar scopes:

```text
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/gmail.compose
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.modify
```

The 2026-05-23 prep added gated support for these target scopes, but the
existing token has not been modified yet. Fernando must manually approve a new
consent screen before these become active:

```text
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.metadata.readonly
https://www.googleapis.com/auth/documents
https://www.googleapis.com/auth/spreadsheets
```

These broader scopes were checked and confirmed absent:

```text
https://mail.google.com/
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive
```

Do not print token contents, refresh tokens, auth codes, client secrets,
credential JSON, or raw OAuth redirects while checking this state.

## Daily Briefing Read Access

The current token is not read-only, but it has practical read access needed for
daily briefing summaries:

- `gmail.modify` includes Gmail read access for daily summaries plus Gmail
  compose/send capability. It does not allow immediate permanent deletion that
  bypasses Trash.
- `calendar.events` includes Calendar event read access for daily and tomorrow
  schedule summaries plus event write capability.

Gemini, Hermes, and Open WebUI can use this token for daily briefing reads.
Read-only and dry-run behavior remains the operational default by policy, not
because this token is limited to read-only scopes.

Default daily summary behavior is:

- Read Gmail.
- Read Calendar events.
- Summarize only.
- Do not archive, delete, label, reply, send, create drafts, or mutate Calendar
  events unless Fernando explicitly approves that live action.

The token has write capability, but controlled write commands still require the
explicit safety gates below.

## Drive / Docs / Sheets OAuth prep

The setup script now supports these service groups:

```text
drive-read
drive-write
docs-read
docs-write
sheets-read
sheets-write
workspace-docs
```

All Drive/Docs/Sheets scope preparation requires:

```bash
--allow-drive-docs-scopes
```

The combined consent URL was generated only after syntax checks and negative
gate tests passed. It is stored in the isolated Hermes profile:

```text
~/Projects/hermes-agent-test/home/.hermes/google_oauth_last_url.txt
```

Do not paste or print the URL unless Fernando explicitly asks to proceed to
manual consent. Token exchange must use non-echoing input for the redirect URL
or authorization code.

## Why `drive.file`

Use `https://www.googleapis.com/auth/drive.file` instead of full
`https://www.googleapis.com/auth/drive` because `drive.file` limits file access
to files the app creates or files the user explicitly opens/authorizes for the
app. Pair it with `drive.metadata.readonly` so the assistant can search/list
metadata when explicitly requested without granting broad full-content Drive
access.

## Tested capabilities

No live Drive, Docs, Sheets, Gmail, or Calendar mutation was run during the
2026-05-23 preparation. Negative tests only were run.

Blocked by the installed controlled gates:

- Drive write without `--allow-live-drive-write`.
- Drive read/search without `--allow-live-drive-read`.
- Docs read without `--allow-live-docs-read`.
- Docs write without `--allow-live-docs-write`.
- Sheets read without `--allow-live-sheets-read`.
- Sheets write without `--allow-live-sheets-write`.
- Broad Drive OAuth service request (`drive`).
- Drive delete/share commands are absent from the parser.
- Direct `gmail send`.
- Direct `gmail reply`.

## Default workflow

Use draft-first Gmail handling:

1. Keep read-only and dry-run behavior as the default.
2. Create a Gmail draft only after explicit approval.
3. Have Fernando manually inspect the draft in Gmail.
4. Treat sending as a separate approval step.
5. Use Calendar writes only for an explicitly approved event mutation and
   preserve the event ID needed for a separately approved cleanup.

## Safety gates

The installed Google Workspace helper gates live writes before dispatching to
the Google API mutation helpers:

```bash
# Calendar create/update/delete
--allow-live-google-calendar-write

# Gmail draft creation
--allow-live-gmail-draft

# Gmail draft sending requires both flags
--allow-live-gmail-send
--send-approved-draft

# Drive
--allow-live-drive-read
--allow-live-drive-write

# Docs
--allow-live-docs-read
--allow-live-docs-write

# Sheets
--allow-live-sheets-read
--allow-live-sheets-write
```

Direct Gmail send/reply remain blocked for controlled workflows. Use draft
creation plus manual review instead.

Drive delete, move, share, permission changes, and broad full Drive scope remain
blocked by default.

## Rollback backups

The controlled-write patch backups are stored beside the installed skill files:

```text
~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/SKILL.md.20260523-134921.drive-docs-sheets.bak
~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/google_api.py.20260523-134921.drive-docs-sheets.bak
~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/setup.py.20260523-134921.drive-docs-sheets.bak
~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/SKILL.md.20260522-123747.controlled-write.bak
~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/google_api.py.20260522-123747.controlled-write.bak
~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/setup.py.20260522-123747.controlled-write.bak
```

Older pre-controlled-write script backups also exist for reference:

```text
~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/google_api.py.20260515-114548.bak
~/Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/setup.py.20260515-114548.bak
```

Do not restore or delete skill files, tokens, OAuth files, or credentials
without a separate approved rollback task.

## Future Operator Rules

- Read-only and dry-run remain default unless a live write flag is explicitly
  provided.
- Calendar create/update/delete require
  `--allow-live-google-calendar-write`.
- Gmail draft creation requires `--allow-live-gmail-draft`.
- Gmail draft send requires both `--allow-live-gmail-send` and
  `--send-approved-draft`.
- Direct Gmail send/reply remain blocked.
- Drive metadata search/list requires `--allow-live-drive-read`.
- Drive upload requires `--allow-live-drive-write`.
- Docs read/write require `--allow-live-docs-read` or
  `--allow-live-docs-write`.
- Sheets read/write require `--allow-live-sheets-read` or
  `--allow-live-sheets-write`.
- Never use `https://mail.google.com/`, broad Calendar scope, or broad Drive
  full-access scope.
- Never delete, move, share, or change permissions on Drive files by default.
- Never print token or credential contents.
