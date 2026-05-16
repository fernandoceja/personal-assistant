# Safe Briefing Output Format Contract

## Purpose

Use this contract when turning safe runner source material into a concise personal-assistant briefing. The generated safe runner file is an assembled briefing input/source packet unless an explicit backend formatter writes a final result.

## Final Briefing Sections

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
- Until Gmail or message sources are approved, omit this section or write "No source available yet" only if that helps clarify the gap.

## Omission Rules

- Omit sections that have no source data.
- If a missing section could confuse the reader, write "No source available yet" instead of inventing content.
- Keep the final briefing short and scannable.

## Safety Rules

- Do not add Gmail findings unless Gmail access was explicitly approved for that run.
- Do not add iMessage findings unless iMessage access was explicitly approved for that run.
- Do not add calendar facts beyond the safe fields present in the source packet.
- Do not create, modify, send, schedule, archive, delete, or persist anything from the briefing.
