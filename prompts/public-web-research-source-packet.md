# Public Web Research Source Packet

Use this prompt only after Fernando explicitly approves public web research.
Tavily is for public search only.

```text
Task: create a public web research source packet.

Approved topic:
[PUBLIC_TOPIC]

Approved query:
[PUBLIC_QUERY]

Safe packet label:
[SAFE_LABEL]

Allowed source:
- Tavily public web search only, routed through Hermes web_search when
  available.

Forbidden inputs:
- Gmail, Calendar, Drive, Docs, Sheets, iMessage, source packets, private files,
  private screenshots, financial details, legal/immigration details,
  account-security details, credentials, tokens, OAuth redirects, or API keys.

Rules:
- Do not search private content.
- Do not include private account data in queries.
- Do not search likely-private terms such as Gmail, email body, bank account,
  password, token, OAuth, USCIS receipt number, SSN, Social Security, private
  doc, source-packets/docs, or /Users/.
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

Preferred command:
scripts/create-web-source-packet.sh --query "[PUBLIC_QUERY]" --label "[SAFE_LABEL]"

Packet format:
1. Topic
2. Search date/time
3. Safety confirmation: no private content sent
4. Backend/provider if known
5. Public sources reviewed
6. Key public facts
7. Useful quotes or snippets, short only
8. Unknowns / needs verification
9. Recommended use in Fernando's workflow

Firecrawl is out of scope. Do not perform deep extraction unless separately
approved.
```

Replace `[PUBLIC_TOPIC]`, `[PUBLIC_QUERY]`, and `[SAFE_LABEL]` with public-only
text. Do not paste private content into this prompt.
