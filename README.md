# Personal Assistant

A **trust-first daily briefing system** that assembles read-only source packets from approved connectors (when explicitly enabled), formats them into a fixed six-section executive brief, validates structure with automated tests, and supports optional review-only delivery artifacts plus a local video briefing pipeline.

## Why this exists

AI assistants fail when they act too much, expose too much, or guess too confidently. This project treats automation as **decision support**: dry-run by default, live reads only with explicit per-run flags, and no silent writes or sends.

## How it works

```text
Source assembly (safe packet) → Field-minimized connectors → Six-section formatter → pytest + shell validation → Optional review draft / local video
```

1. **Read-only first** — Gmail and Calendar access are off unless you pass `--allow-live-gmail-readonly` or `--allow-live-google-calendar`.  
2. **Field-minimized packets** — Connectors emit normalized safe-list records (capped snippets, categories, triage hints) — not bodies, IDs, URLs, or tokens.  
3. **Fixed briefing contract** — Every final brief uses six sections: Executive Summary, Priority Now, Review With Me, Calendar Watch, Low Priority, Ignore/Suspicious.  
4. **Validated output** — Shell heading checks plus pytest suites guard structure and redaction rules.  
5. **Review before send** — Mobile summary drafts are local text files; sending is a separate explicit step.  
6. **Local video (optional)** — `run-video-briefing.sh` chains text briefings into a local render workspace using mock or sanitized input for demos.

See **[CASE_STUDY.md](CASE_STUDY.md)** for architecture, safety model, testing strategy, and portfolio context.

## Quick start (safe — no live APIs)

```bash
# Non-live source packet + heading validation
bash run-briefing.sh --mode full-safe

# Same path with mock Gmail safe-list (fixtures only)
bash run-briefing.sh --mode full-safe --allow-live-gmail-readonly --gmail-mock

# Run automated tests
pytest
```

Approved manual live-readonly wrapper (explicit opt-in for that run only):

```bash
./run-live-briefing.sh morning
# or: scripts/run-live-morning-briefing.sh
```

## Key scripts and docs

| Path | Role |
|------|------|
| `run-briefing.sh` | Main wrapper; default `full-safe` mode |
| `scripts/run-morning-assistant-safe.sh` | Source packet assembly |
| `scripts/format-safe-briefing.sh` | Six-section formatter |
| `scripts/gmail-safe-list-mock.py` | Mock connector for tests and demos |
| `fixtures/gmail-safe-list-mock.json` | Synthetic safe-list records |
| `prompts/safe-briefing-output-format.md` | Output contract |
| `docs/morning-assistant-safe-runner.md` | Runner modes and safety gates |
| `docs/daily-briefing-quality-rubric.md` | Triage standards |
| `docs/patches/google-workspace-*-readonly/` | Reference readonly connector patches |

## Safety highlights

- **Phase-gated capabilities** — readonly first; writes and sends require separate scripts and flags  
- **Explicit gates per run** — no live Gmail, Calendar, or send without opt-in flags  
- **pytest redaction tests** — token-like strings, raw bodies, and message IDs must not appear in formatted output  
- **Separate write path** — `scripts/google-workspace-write.py` refuses mutations without explicit write flags  

## Private by design

Real briefings, logs, todos, memory, credentials, and video outputs are **gitignored** and not part of the public repository. Use mock fixtures and sanitized samples for demos and portfolio artifacts.
