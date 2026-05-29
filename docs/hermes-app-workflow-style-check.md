# Hermes App Workflow Style Check

Date/time: 2026-05-23 19:00 PDT

Hermes app version: 0.4.5

Remote mode URL: http://127.0.0.1:8642

## App Status

- Hermes Agent launched successfully from `/Applications/Hermes Agent.app`.
- Settings showed Desktop v0.4.5 and Remote mode selected.
- Test Connection returned "CONNECTED SUCCESSFULLY!" for `http://127.0.0.1:8642`.
- Visible app sections included Chat, Sessions, Profiles, Office, Kanban, Models, Providers, Skills, Persona, Memory, Tools, Schedules, Gateway, and Settings.
- Schedules showed "No scheduled tasks yet."
- Gateway was not available in Remote mode; no allow-all toggle or broad gateway enablement was visible.
- Tools and Skills were also not available in Remote mode through the desktop UI.

## Workflow Understanding

Hermes restated Fernando's personal-assistant style as read-only by default, conservative, source-backed, concise, and action-oriented. It preserved the six-section briefing format:

1. Executive Summary
2. Priority Now
3. Review With Me
4. Calendar Watch
5. Low Priority
6. Ignore/Suspicious

It correctly prioritized UMGC/school, money/bills, legal/immigration, Apple/work, account security, and deadlines. It also stated that ambiguous school, money, legal, immigration, or security items should go to Review With Me.

## Simulation Results

Morning briefing simulation:

- Correctly named the safe command:
  `cd ~/Projects/personal-assistant && scripts/run-live-morning-briefing.sh`
- Correctly described read-only behavior and no Gmail/Calendar/Drive/Docs/Sheets mutations.
- Correctly prohibited cron, schedules, LaunchAgents, Gateway changes, `memory.md` edits, OAuth/token/credential edits, and raw private content printing.
- Correctly used the six-section final format.
- Gap: did not explicitly name "Gmail safe-list" and "Calendar safe-list" in the simulated answer, though it did describe read-only Gmail and Calendar behavior.

Google Doc source simulation:

- Correctly required an exact approved Google Doc ID.
- Correctly named `scripts/create-doc-source-packet.sh`.
- Correctly preferred `--summary-only` for sensitive strategy material.
- Correctly used the local source packet as the input layer.
- Correctly said not to browse Drive, read arbitrary Docs, write/share/move/delete Docs or Drive files, or use Tavily/web search by default.
- Correctly separated source-backed facts from strategic recommendations and unknowns.

## Observed Gaps

- Hermes should be nudged to explicitly say "Gmail safe-list" and "Calendar safe-list" when explaining daily briefing behavior.
- Chat title remained visible as "New Chat"; the conversation was framed by the first message as "Personal Assistant Workflow Style."
- Desktop Remote mode hides Gateway, Tools, and Skills internals, so gateway posture was confirmed by UI absence of enablement plus prior local service/config expectations, not by a visible allow-all setting.

## Recommended Follow-Up

Ask Hermes to add one sentence to its daily-briefing mental model:

> Daily briefings use Gmail safe-list and Calendar safe-list only; never broad Gmail/Calendar reads or account mutations.

Then rerun the morning simulation once to confirm that phrase appears naturally.
