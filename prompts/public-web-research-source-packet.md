# Public Web Research Source Packet

Use this prompt only after Fernando explicitly approves public web research.
Tavily is for public search only.

```text
Task: create a public web research source packet.

Approved topic:
[PUBLIC_TOPIC]

Allowed source:
- Tavily public web search only.

Forbidden inputs:
- Gmail, Calendar, Drive, Docs, Sheets, iMessage, source packets, private files,
  private screenshots, financial details, legal/immigration details,
  account-security details, credentials, tokens, OAuth redirects, or API keys.

Rules:
- Do not search private content.
- Do not include private account data in queries.
- Do not create, update, delete, share, move, upload, send, schedule, or change
  permissions anywhere.
- Use public sources only.
- Prefer official sources, primary sources, vendor/product pages, public docs,
  reputable news, and clearly dated pages.
- Do not invent facts, dates, pricing, capabilities, or claims.
- Label uncertainty.
- Keep snippets short.

Write a local source packet under:
source-packets/web/

Packet format:
1. Topic
2. Search date/time
3. Safety confirmation: no private content sent
4. Public sources reviewed
5. Key public facts
6. Useful quotes or snippets, short only
7. Unknowns / needs verification
8. Recommended use in Fernando's workflow

Firecrawl is out of scope. Do not perform deep extraction unless separately
approved.
```

Replace `[PUBLIC_TOPIC]` with a public-only topic. Do not paste private content
into this prompt.
