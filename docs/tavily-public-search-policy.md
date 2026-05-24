# Tavily Public Search Policy

## Purpose

Tavily is an optional public web search provider for Hermes and
personal-assistant workflows. It is for public-source enrichment only, not
private account analysis.

Use Tavily for:

- Current public facts.
- Public news and product updates.
- Product, vendor, and company research.
- Public source discovery for business or technical briefs.
- Public context that helps interpret a non-private question.

Do not use Tavily for:

- Gmail content, snippets, subjects, sender lists, labels, or message metadata.
- Calendar event content, schedules, locations, attendees, or reminders.
- Drive, Docs, Sheets, source packets, or private file contents.
- Financial, legal, immigration, medical, HR, or account-security details.
- OAuth redirects, tokens, API keys, credentials, or debug output.
- Queries copied from private documents unless Fernando explicitly approves the
  exact text and destination.

## Approval Gate

Tavily must run only after an explicit user request or an explicit
approval flag such as:

```text
--allow-live-web-search
```

Default daily briefings, weekly reviews, Google Doc source-packet workflows,
and Google Workspace checks must not use Tavily automatically.

## Source Packet Rule

Tavily results should be converted into local source packets under:

```text
source-packets/web/
```

The parent `source-packets/` directory is gitignored and must remain
gitignored. Do not commit generated web packets by default.

Each packet should include:

- Query.
- Timestamp.
- Public URLs.
- Short snippets or summaries.
- Why each source was included.
- Safety note confirming no private content was sent.

## Output Boundaries

Public web results may inform a brief, but the final output must separate:

- Public-source facts.
- Inferences.
- Recommendations.
- Unknowns or items needing Fernando's review.

Do not blend public web claims with private Gmail, Calendar, Docs, Drive,
Sheets, or source-packet contents unless Fernando explicitly approves the
combined analysis and the data flow.

## Firecrawl Boundary

Firecrawl may be added later for deeper public-page extraction. It is not part
of this setup. Do not configure Firecrawl, scrape sites, or extract page bodies
until Fernando explicitly approves that separate step.

## Current Setup Status

As of 2026-05-24, Tavily policy is documented first. Configuration requires a
real `TAVILY_API_KEY` in the isolated Hermes `.env`; no API key should be
hardcoded or committed.
