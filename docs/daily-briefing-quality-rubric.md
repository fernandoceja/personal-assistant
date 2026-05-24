# Daily Briefing Quality Rubric

## Purpose

Good daily briefing helps Fernando decide what needs attention today, what needs
review, and what can safely wait. It must be short, source-backed, and
conservative around money, school, work, legal/immigration, and account
security.

## Required Structure

Final briefings must contain exactly these top-level sections, in order:

1. Executive Summary
2. Priority Now
3. Review With Me
4. Calendar Watch
5. Low Priority
6. Ignore/Suspicious

## Priority Now Standard

Use only for urgent or deadline-driven items. Each item must include:

- Source
- Sender/Event
- Subject
- Timing
- Importance
- Next Action

Good example:

- Source: Gmail readonly. Sender/Event: Apple HR. Subject: Schedule action needed. Timing: Today. Importance: work schedule may affect today/tomorrow coverage. Next Action: Review Apple source directly before acting.

If timing is unclear, do not invent it. Write: `Timing unclear - verify.`

## Review With Me Standard

Use for important but non-urgent items and uncertain high-stakes items. Each
item must include:

- Why this matters
- What to verify
- Category: money, school, work, legal/immigration, account security, routine, or uncertain
- Conservative next action

Good example:

- Student Accounts — Statement available. Why this matters: possible school or tuition impact. What to verify: amount, due date, and whether any hold/drop risk exists. Category: school. Conservative next action: Review with Fernando before any payment or schedule action.

## Conservative Triage Rules

- UMGC, tuition, statement, drop/withdrawal, FAFSA, financial aid, student account: Review With Me, or Priority Now if source says timing is urgent.
- Bank/payment/account balance/security alerts: Review With Me unless clearly suspicious or urgent.
- USCIS/legal/immigration: Review With Me, or Priority Now if deadline/action exists.
- Apple/work schedule or HR: Priority Now if timing-sensitive, otherwise Review With Me.
- Unknown sender plus billing/security language: Ignore/Suspicious.
- Do not invent deadlines, senders, balances, links, event facts, or actions.
- If source timing is unclear, write `Timing unclear - verify.`

## Must Never Appear

- Raw email bodies.
- Raw Gmail API payloads.
- Gmail message IDs or thread IDs unless needed locally and explicitly approved.
- OAuth material, auth codes, redirects, token contents, refresh tokens, client secrets, credential JSON.
- Full private document contents.
- Full URLs, tracking links, unsubscribe links, attachment IDs, one-time passcodes, account numbers.
- Calendar descriptions, attendees, meeting links, conference data, reminders, or private notes.

## Good Briefing Behavior

- Lead with the three highest-impact facts only.
- Separate urgent action from review-worthy uncertainty.
- Preserve suspicious/fake billing items under Ignore/Suspicious.
- Say when no approved source exists instead of inventing findings.
- Keep action language conservative: review, verify, confirm, check source directly.
