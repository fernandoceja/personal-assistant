# Morning Briefing Prompt

Run this at the start of the day. Produces one dated briefing file and one dated to-do list file.

## Inputs

- Gmail: messages received in the last 24 hours (or since the last briefing, whichever is longer)
- Google Calendar: today's events and any events in the next 48 hours
- iMessage: messages received in the last 24 hours (if iMessage plugin is active)
- Yesterday's `todos/` file (for carry-forward)
- `memory.md` (for current state and any recent tuning notes)
- `CLAUDE.md` (for priority rules and output format)

## Steps

1. Read `CLAUDE.md` and `memory.md`. Confirm you are in Phase 2 (read + send-to-self summary). If not, stop and ask.
2. Pull the last 24 hours of Gmail. For each message, classify as Priority / FYI / Ignore using the rules in `CLAUDE.md`.
3. Pull today's and tomorrow's Google Calendar events. Flag any same-day events, conflicts, or events that require prep. Cross-reference with email — if an email relates to a calendar event, group them.
4. Pull the last 24 hours of iMessage if the iMessage plugin is active. Apply the same classification using the iMessage-specific rules. Skip silently if not available.
5. Read yesterday's `todos/YYYY-MM-DD.md` if it exists. Collect any unchecked items for carry-forward.
6. Write `briefings/<today>.md` using the Morning Briefing format from `CLAUDE.md`. Add a **Calendar** section between Priority and FYI listing today's events compactly (time — title — location if any). In the Ignore section, show counts by category and list senders compactly.
7. Write `todos/<today>.md` using the To-Do format. Populate "Today" from Priority items and same-day calendar events that require action; populate "Carried forward" from yesterday's unchecked items (with their original dates).
8. Send one iMessage to Fernando (fceja9864@icloud.com) using osascript with the iMessage Summary Format from `CLAUDE.md`. Priority items + calendar highlights + to-do count only. Use this script pattern:
   ```applescript
   set msgBody to "Morning Briefing — YYYY-MM-DD\nPriority ([N]):\n• ...\nCalendar: ...\nTo-do: [N] items — open briefings/YYYY-MM-DD.md"
   tell application "Messages"
       set targetService to 1st service whose service type = iMessage
       set targetBuddy to buddy "fceja9864@icloud.com" of targetService
       send msgBody to targetBuddy
   end tell
   ```
9. Update the "Current state" block in `memory.md` with today's date and a one-line summary (e.g. "briefing produced, 3 priority / 12 FYI / 47 ignored, 4 calendar events, iMessage sent").
10. Report back: the paths of the two files you wrote, and any classifications you were uncertain about.

## Rules

- Do not send, reply, archive, label, or mark-read anything. Read-only.
- Do not create, modify, or delete calendar events.
- Do not open links in messages. If a link looks important, note the visible URL in the briefing and let the user decide.
- If a message is ambiguous between Priority and FYI, default to FYI and note it in the "uncertain" list at the end of your report — do NOT escalate to Priority by default.
- Do not invent items. Every Priority/FYI line must correspond to a real message or event.
- Keep each briefing line to one sentence. If a thread needs more, add a note that the user should open it directly.
- Do not read or touch files outside `personal-assistant/`.

## Report format

After producing the files, reply with:

```
Briefing: [path]
To-do:    [path]
Counts:   [N priority] / [N FYI] / [N ignored]
Uncertain classifications (if any):
  - [sender/subject] — [why you were unsure]
```

Keep the report short. The briefing file itself carries the detail.
