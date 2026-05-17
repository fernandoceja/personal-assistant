# Google Workspace Gmail Read-Only Safe-List Patch

## Why this patch exists

This folder preserves a reviewable Google Workspace connector patch artifact for future Gmail read-only safe-list support. It is documentation/reference code only. It must not be copied into the installed Hermes Google Workspace connector, wired into `run-briefing.sh`, or used for live Gmail until the approval gates below are complete.

Purpose: add one narrow Gmail read path for Morning Assistant source packets:

```bash
gmail safe-list --window 48h --max-per-filter 10
```

The command is intended to collect a small set of recent candidate messages for briefing triage without exposing Gmail IDs, thread IDs, bodies, attachments, raw responses, or mutation capabilities.

## Required OAuth scope

The setup/reference patch may request only this Gmail scope:

```text
https://www.googleapis.com/auth/gmail.readonly
```

## Forbidden OAuth scopes

Do not request, store as required, or accept as the Gmail safe-list baseline any broader Gmail scope:

```text
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.compose
https://www.googleapis.com/auth/gmail.insert
https://www.googleapis.com/auth/gmail.labels
https://mail.google.com/
```

## Allowed output fields

The safe-list output may include only normalized briefing fields:

- source: always `gmail_readonly`
- category: local filter/category name, not a Gmail label ID
- sender_display: display name derived from the From header
- sender_domain: domain derived from the From header
- subject: Subject header, capped
- received_at: Date header or normalized received timestamp if available from metadata
- snippet: Gmail snippet only, capped to a short text field
- labels: allow-listed system/category names only when needed for triage
- has_attachment: boolean or `unknown` based only on metadata hints, never attachment details
- matched_filter: safe-list filter name
- triage_hint: one of Priority Now, Review With Me, Calendar Watch, Low Priority, Ignore/Suspicious
- safety_notes: short local note explaining why the record is safe or suspicious

## Excluded fields

The safe-list output must never expose:

- Gmail message IDs or thread IDs
- raw Gmail API responses
- full message bodies, MIME parts, HTML, or raw RFC822 data
- attachments, attachment names, attachment IDs, or attachment contents
- raw headers beyond the normalized From, Subject, and Date values
- To, Cc, Bcc, Reply-To, Message-ID, References, In-Reply-To
- labels outside the local allow-list
- full URLs, tracking links, unsubscribe links, account links, auth/security tokens, one-time passcodes, account numbers
- OAuth/token/config paths or file contents

## Safety model

- Read-only Gmail scope only.
- Explicit command only: `gmail safe-list --window 48h --max-per-filter 10`.
- Recency-limited queries only; default and approved window is 48 hours.
- Candidate discovery uses `users.messages.list` for IDs only.
- Per-message reads use `users.messages.get` with `format=metadata`, never `full` or `raw`.
- Metadata requests ask only for safe headers: `From`, `Subject`, `Date`.
- Field masks are used where the API/client supports them.
- The connector normalizes and drops Gmail IDs/thread IDs before output.
- The connector does not fetch bodies or download attachments.
- The connector does not expose raw Gmail API responses.
- The connector does not register write-capable Gmail commands for this safe path.

## Static validation checks

Before applying this patch to any installed connector, validate the artifact only:

```bash
PATCH_DIR="docs/patches/google-workspace-gmail-readonly"
python3 -m py_compile "$PATCH_DIR/setup.py" "$PATCH_DIR/google_api.py"
grep -R "https://www.googleapis.com/auth/gmail.readonly" "$PATCH_DIR"
grep -R "safe-list" "$PATCH_DIR"
! grep -R "https://www.googleapis.com/auth/gmail.modify\|https://www.googleapis.com/auth/gmail.send\|https://www.googleapis.com/auth/gmail.compose\|https://www.googleapis.com/auth/gmail.insert\|https://www.googleapis.com/auth/gmail.labels\|https://mail.google.com/" "$PATCH_DIR/setup.py" "$PATCH_DIR/google_api.py"
! grep -R "format=.*full\|format=.*raw\|messages().send\|messages().modify\|messages().trash\|messages().delete\|attachments().get" "$PATCH_DIR/google_api.py"
! grep -RE '"(refresh_token|access_token|private_key)"[[:space:]]*:' "$PATCH_DIR"
```

The forbidden-scope grep intentionally targets executable/reference Python files. This README lists forbidden scopes as review documentation, so README hits are expected and are not evidence that the patch requests them.

## Runtime validation checks before future live use

Do not run these during artifact creation. They are approval-gated future checks only:

- Confirm the stored token has exactly the Gmail read-only scope needed for this connector path.
- Confirm the CLI exposes `gmail safe-list` and not Gmail mutation commands for the Morning Assistant safe path.
- Run a tiny explicitly approved live read with `--window 48h --max-per-filter 1`.
- Inspect output for allowed fields only.
- Confirm no message IDs, thread IDs, bodies, attachments, raw payloads, URLs, tokens, or account numbers appear.
- Confirm errors fail closed without falling back to broader reads.

## Approval gates before live use

1. Review and approve this docs patch artifact.
2. Separately approve applying the patch to the installed Hermes Google Workspace connector.
3. Separately approve a Gmail read-only OAuth/setup pass using only `https://www.googleapis.com/auth/gmail.readonly`.
4. Separately approve one live smoke test.
5. Only after successful review, separately approve wiring the safe-list output into the safe runner.

Until all gates are complete, live access status is: not implemented and not run.

## Files preserved here

- `README.md`: safety contract and approval gates.
- `setup.py`: OAuth setup reference limited to Gmail read-only scope.
- `google_api.py`: connector reference for `gmail safe-list` only.
- `validate_artifact.py`: optional static validator for this folder; it performs no live Gmail access.
