# Weekly Review Workflow

## Purpose

Use weekly review to summarize local final briefings and optionally approved
local Google Doc source packets. It is a local-file workflow only.

## Inputs

- `briefings/*-final.md`
- Optional explicitly named `source-packets/docs/*.md`

## Safety Boundaries

- No live Gmail.
- No live Calendar.
- No live Drive, Docs, or Sheets.
- No writes to Gmail, Calendar, Drive, Docs, or Sheets.
- No cron jobs, LaunchAgents, schedules, or Gateway changes.
- No `memory.md` update.
- No tokens, credentials, OAuth artifacts, raw email bodies, or full private
  document contents in terminal output.

## Command

```bash
scripts/run-weekly-review.sh
```

Include an approved local doc packet:

```bash
scripts/run-weekly-review.sh --source-packet source-packets/docs/PACKET.md
```

## Output

The script writes a local markdown packet under `weekly-reviews/`. That folder
is gitignored because weekly reviews may contain private or business-sensitive
summaries.

## Required Sections

1. Executive Summary
2. Unresolved Priority Items
3. Money / Bills / Account Review
4. School / UMGC Review
5. Work / Apple Review
6. Calendar Load and Conflicts
7. Business / Projects
8. Suggested Next Week Focus
9. Review With Me

## Hermes / Open WebUI Use

Give Hermes or Open WebUI only the generated local weekly-review packet path.
Do not paste full private packet contents into shared systems unless Fernando
approves the exact destination and payload.
