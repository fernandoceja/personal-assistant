# Use Approved Google Doc as Source Material

Use this prompt when Hermes or Open WebUI should summarize or reason from a
local Google Doc source packet that Fernando already approved and Codex already
created.

```text
Use the approved Google Doc source packet at:
[SOURCE_PACKET_PATH]

Treat it as read-only source material. Summarize only what is source-backed.
Do not access Google Drive, Google Docs, Google Sheets, Gmail, Google Calendar,
iMessage, browser pages, links, attachments, or external files. Do not create,
update, append, delete, share, move, upload, send, schedule, or change
permissions anywhere.

Return:
1. Executive Summary: 3 bullets max.
2. Key Source Facts: short bullets, no full document dump.
3. Open Questions / Review With Fernando: items needing human verification.
4. Suggested Next Step: one safe next action.

Keep private/business-sensitive details minimal. Do not include secrets,
tokens, OAuth artifacts, credential data, raw debug blocks, or unnecessary
verbatim text.
```

Replace `[SOURCE_PACKET_PATH]` with a path under `source-packets/docs/`.
