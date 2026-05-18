# Safe Briefing Output Format Contract

## Purpose

Use this contract when turning safe runner source material into a concise personal-assistant briefing. The generated safe runner file is an assembled briefing input/source packet unless an explicit backend formatter writes a final result.

## Final Briefing Sections

The final briefing must always include exactly these six top-level headings, rendered as `## Heading Name`, in this exact order:

1. `## Executive Summary`
2. `## Priority Now`
3. `## Review With Me`
4. `## Calendar Watch`
5. `## Low Priority`
6. `## Ignore/Suspicious`

Do not omit any required heading. If a section has no source-backed items, include the placeholder: `No source-backed items in this packet.`

For `## Ignore/Suspicious`, when no email or message source was approved, include the placeholder: `No email or message source was approved for this packet.`

### Executive Summary
- Include 3 bullets max.
- Use only the highest-impact items supported by source material.
- Keep each bullet short and action-oriented.

### Priority Now
- Include urgent items and deadline-driven items only.
- For each item, include: Source, Sender/Event, Subject, Timing, Importance, Next Action.
- Do not invent deadlines, senders, bills, email findings, or calendar facts.

### Review With Me
- Include important but non-urgent items Fernando should verify.
- When uncertain about legal, immigration, money, school, or work deadlines, classify the item here.
- Use conservative wording and avoid advice beyond the source material.

### Calendar Watch
- Summarize today/tomorrow calendar source material only.
- Highlight work, school, bills, and conflicts when source data supports them.
- Do not include descriptions, attendees, URLs, meeting links, or private notes.

### Low Priority
- Group non-urgent source-backed items compactly.
- Prefer grouped summaries over long item lists.

### Ignore/Suspicious
- Use for spam, phishing, fake billing, or clear noise when an email/message source exists.
- Until Gmail or message sources are approved, use the required placeholder instead of inventing findings.

## Required Empty Section Rules

- Do not omit sections that have no source data.
- Use `No source-backed items in this packet.` for empty sections.
- Use `No email or message source was approved for this packet.` for Ignore/Suspicious when no email or message source was approved.
- Keep the final briefing short and scannable.

## Safety Rules

- Do not add Gmail findings unless Gmail access was explicitly approved for that run with `--allow-live-gmail-readonly`, or mock Gmail mode is explicitly enabled with both `--allow-live-gmail-readonly --gmail-mock`.
- Default full-safe runs include only a non-live Gmail placeholder; do not treat it as email source data.
- If `--allow-live-gmail-readonly` is present without `--gmail-mock`, use only live `gmail safe-list --window 48h --max-per-filter 10` normalized records from the source packet.
- If `--allow-live-gmail-readonly --gmail-mock` is present, use only normalized mock safe-list records from the source packet; do not infer live Gmail access.
- Gmail safe-list records may include only: source, category, sender_display, sender_domain, subject, received_at, snippet capped to 200 characters, labels, has_attachment, matched_filter, triage_hint, safety_notes.
- Gmail safe-list output must never expose full bodies, attachments, attachment names/IDs/contents, raw headers, tracking links, unsubscribe links, tokens, one-time passcodes, account numbers, full URLs, message IDs, thread IDs, raw Gmail API responses, To/Cc/Bcc, or OAuth/token/config paths or contents.
- Map Gmail safe-list triage hints into the six final sections: Priority Now, Review With Me, Calendar Watch, Low Priority, Ignore/Suspicious, and Executive Summary.
- Gmail categories are: Immigration / USCIS / legal; Work / Apple; School / UMGC; Bills / T-Mobile / HelloStorage; Finances / Rocket Money / Fidelity / IBKR / E*TRADE / BofA / IHSS; Suspicious/phishing; Low priority / routine.
- No email writes are ever allowed in safe mode: no send, reply, forward, archive, delete, label, or mark-read actions.
- Do not add iMessage findings unless iMessage access was explicitly approved for that run.
- Do not add calendar facts beyond the safe fields present in the source packet.
- Do not create, modify, send, schedule, archive, delete, or persist anything from the briefing.
