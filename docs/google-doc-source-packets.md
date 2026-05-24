# Google Doc Source Packets

Use this workflow when Fernando approves one exact Google Doc as source
material for Hermes, Open WebUI, or the terminal-backed personal assistant.

## Safety Model

- Read-only only.
- Requires an exact approved Google Doc ID.
- Uses `docs get --allow-live-docs-read`.
- Writes a local markdown source packet under `source-packets/docs/`.
- Does not create, update, append, delete, share, move, upload, or overwrite
  Drive, Docs, or Sheets files.
- Does not run Gmail or Calendar operations.
- Does not print tokens, credentials, OAuth artifacts, or full document contents
  to the terminal.
- `source-packets/` is gitignored because packets may contain private or
  business-sensitive material.

## Command

```bash
scripts/create-doc-source-packet.sh \
  --doc-id 1ssh-x25GcU2QUtHIyfj50xgz0dzqy6C5D0HJEDUwd0M \
  --label "80s Obsession Business Growth Plan" \
  --summary-only
```

For a bounded extract, use:

```bash
scripts/create-doc-source-packet.sh \
  --doc-id 1ssh-x25GcU2QUtHIyfj50xgz0dzqy6C5D0HJEDUwd0M \
  --label "80s Obsession Business Growth Plan" \
  --max-chars 2000
```

## Packet Contents

Each packet includes:

- Title.
- Doc ID.
- Created timestamp.
- Source type.
- Safety note.
- Brief safe summary.
- Optional bounded extract.

## Approval Rule

Do not run the wrapper against a document until Fernando approves the exact
file ID. Do not read adjacent Drive files or follow links inside document text
without separate approval.

## Next Use

After packet creation, feed only the local packet path to Hermes/Open WebUI as
source material. Do not paste private packet contents into shared systems unless
Fernando approves that destination and payload.
