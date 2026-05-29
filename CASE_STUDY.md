# Case Study: Personal Assistant — Trust-First Daily Briefing System

> A locally orchestrated personal assistant that turns approved read-only signals into a structured daily briefing — with explicit safety gates, field-level data minimization, and automated validation before any optional delivery step.

**Author:** Fernando Ceja  
**Repo:** [github.com/Thor0589/personal-assistant](https://github.com/Thor0589/personal-assistant)  
**Status:** Active development — Phase 2 (read-only sources + optional review-only delivery artifacts)  
**Stack:** Bash orchestration, Python helpers, Hermes Agent / Google Workspace skill integration, local Calendar reads, pytest validation

---

## Project overview

Personal Assistant is a **governed automation system** for daily situational awareness. It assembles source packets from approved read-only connectors, formats them into a fixed six-section briefing contract, validates output structure automatically, and optionally produces review-only delivery artifacts (short mobile summary, local HTML/video briefing).

The design goal is **trust-first operation**: start read-only, prove correctness with tests and dry-runs, and earn broader capability in explicit phases — never default to broad OAuth scopes, silent writes, or unreviewed outbound messaging.

---

## Problem solved

High-volume personal inboxes and calendars create three failure modes for AI assistants:

1. **Over-action** — drafting, sending, or mutating data without explicit approval  
2. **Over-exposure** — leaking bodies, tokens, IDs, or private metadata into logs or summaries  
3. **Over-confidence** — inventing deadlines, senders, or urgency from incomplete context  

This project treats the briefing as a **decision-support artifact**, not an autonomous agent. The system separates:

- **Source packet assembly** (what was actually read, with diagnostics)  
- **Formatting** (mapping normalized records into a strict output contract)  
- **Delivery** (review-only drafts; send requires separate explicit flags)

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                     run-briefing.sh (wrapper)                   │
│  Default: --mode full-safe │ validates headings │ dry-run first │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐
│ Safe runner   │     │ Field-masked    │     │ Formatter        │
│ (source       │────▶│ connectors      │────▶│ (six-section     │
│  assembly)    │     │ Gmail safe-list │     │  contract)       │
│               │     │ Calendar safe-  │     │                  │
│               │     │ list / local    │     │                  │
└───────────────┘     └─────────────────┘     └────────┬─────────┘
        │                       │                      │
        │                       │                      ▼
        │                       │            ┌──────────────────┐
        │                       │            │ Validation       │
        │                       │            │ (headings, no    │
        │                       │            │  token/body leak)│
        │                       │            └────────┬─────────┘
        │                       │                      │
        ▼                       ▼                      ▼
  *-safe.md              fixtures/mock OR        *-final.md
  source packet          live readonly gates     (formatted brief)
                                                      │
                              ┌───────────────────────┼───────────────────────┐
                              ▼                       ▼                       ▼
                    mobile draft              audit manifest           local video
                    (review-only)             (hashes, status)         (optional pipeline)
```

### Pipeline stages

| Stage | Artifact | Purpose |
|-------|----------|---------|
| 1. Source assembly | `briefings/*-safe.md` | Captures approved inputs and diagnostics; non-live by default (gitignored) |
| 2. Formatting | `briefings/*-final.md` | Applies six-section contract from `prompts/safe-briefing-output-format.md` |
| 3. Review draft | `briefings/*-imessage-draft.txt` | Short self-summary preview; no auto-send |
| 4. Optional send | explicit `--send-approved-draft --recipient` | Separate manual gate |
| 5. Optional video | `video-workspace/<run>/` | Local briefing video render chain (gitignored) |
| 6. Audit | `logs/audit/*.json` | Provenance: validation flags and artifact metadata (gitignored) |

### Key design choices

- **Opt-in flags per run** — live Gmail and Calendar reads require `--allow-live-gmail-readonly` and `--allow-live-google-calendar`; default runs are non-live.  
- **Normalized safe-list schema** — connector output limited to triage fields (sender domain, capped snippet, category, hint); excludes bodies, IDs, URLs, and tokens.  
- **Separate write path** — `scripts/google-workspace-write.py` refuses calendar mutations unless preview or live-write flags are passed; covered by pytest.  
- **No hidden backends** — the safe runner documents backend detection; dry-run is the default.

---

## Safety model

### Phased capability (current: Phase 2)

| Capability | Default | Explicit gate required |
|------------|---------|-------------------------|
| Local repo file writes | Allowed | — |
| Gmail read | **Off** | `--allow-live-gmail-readonly` |
| Gmail mock (CI/dev) | **Off** | `--allow-live-gmail-readonly --gmail-mock` |
| Google Calendar read | **Off** | `--allow-live-google-calendar` |
| Calendar or email writes | **Off** | separate write script and flags |
| Mobile message send | **Off** | `--send-approved-draft --recipient` |
| Cron or LaunchAgents | **Off** | not implemented in safe path |
| Automatic memory updates | **Off** | legacy path disabled unless explicitly approved |

### Output contract (always enforced)

Final briefings must contain exactly these sections, in order:

1. Executive Summary  
2. Priority Now  
3. Review With Me  
4. Calendar Watch  
5. Low Priority  
6. Ignore/Suspicious  

Rules: no invented deadlines; uncertain high-stakes items route to **Review With Me**; suspicious billing or security patterns route to **Ignore/Suspicious**; empty sections use explicit placeholders.

### Data minimization (must never appear in output)

- Raw email bodies, message or thread IDs, OAuth material  
- Full URLs, tracking links, attachment contents  
- Calendar descriptions, attendees, meeting links  
- Credential paths or token values  

Documented in `docs/daily-briefing-quality-rubric.md` and enforced by `tests/test_safe_briefing_format.py`.

### Connector patches (reference implementations)

Reviewable patches under `docs/patches/` document intended readonly OAuth scopes:

- Gmail: `gmail.readonly` plus a narrow `gmail safe-list` command  
- Calendar: `calendar.readonly` plus a narrow `calendar safe-list` command  

These patches are **reference artifacts** — not silently deployed into production connectors without review.

---

## Validation and testing

### Automated tests

```bash
pytest tests/test_safe_briefing_format.py
pytest tests/test_google_workspace_write.py
pytest tests/test_create_imessage_briefing_draft.py
pytest tests/test_send_imessage_briefing_draft.py
```

**What tests prove:**

- Required headings are exact and ordered  
- Snippets containing token-like strings or raw bodies do not leak into formatted output  
- Empty calendar sources do not produce false “events found” claims  
- High-stakes categories conservatively route to Review With Me  
- Phishing-style mock records route to Ignore/Suspicious  
- Google Workspace write CLI returns a read-only refusal without explicit write flags  

### Manual dry-run (no live APIs)

```bash
bash run-briefing.sh --mode full-safe
bash run-briefing.sh --mode full-safe --allow-live-gmail-readonly --gmail-mock
```

The mock path uses `fixtures/gmail-safe-list-mock.json` — synthetic records labeled mock-only for local validation and CI-style runs.

### Wrapper validation

`run-briefing.sh` validates all six headings after formatting and reports pass or fail per section without requiring live connector access when mock mode is enabled.

---

## Local video briefing pipeline

The optional video path chains an approved text briefing into a **local-first** render workspace:

```bash
./run-video-briefing.sh morning
```

Stages (see `scripts/create-local-video-briefing.sh` and `scripts/create-briefing-video.py`):

1. Run the live-safe text briefing wrapper (`run-live-briefing.sh`)  
2. Build storyboard and narration artifacts under `video-workspace/<run>/`  
3. Render HTML and optional MP4 locally  

**Public demonstration rule:** use mock or sanitized briefing input only. Real video workspaces and rendered outputs are gitignored and must not be published.

---

## Demo artifacts suitable for a public portfolio

| Artifact | Description | Status |
|----------|-------------|--------|
| Architecture diagram | Pipeline and safety gates (above) | Ready to publish |
| Synthetic sample briefing | Generated from `--gmail-mock` plus formatter | Create before publish |
| pytest output | Heading and redaction tests passing | Ready after one local run |
| Safe-list schema table | Allowed vs forbidden fields from patch READMEs | Ready to publish |
| Sanitized audit manifest example | Schema keys only (`safety_mode`, `validation_results`) | Create sanitized copy |
| Short demo video | Local HTML render with mock narration | Optional |

**Do not publish:** real briefing files, audit logs tied to live runs, or any artifact containing live sender data or account details.

---

## Results (qualitative)

- Established a **repeatable dry-run → optional live-readonly → format → validate** workflow  
- Reduced connector blast radius via **safe-list field masks** and **per-run opt-in flags**  
- Codified triage behavior in tests so classification rules survive refactors  
- Separated **review draft** from **explicit send**, preventing one-step accidental messaging  
- Documented readonly Google Workspace patches for auditable third-party integration review  

Add quantitative claims only after measurement (for example, time saved per briefing or triage accuracy on a labeled mock set).

---

## Resume bullets (general)

- Built a **trust-first personal assistant pipeline** with phased read-only defaults, explicit per-run capability flags, and automated six-section output validation.  
- Designed **field-minimized API connectors** (Gmail and Calendar safe-list) with pytest-enforced redaction rules blocking bodies, tokens, and message IDs from briefing output.  
- Implemented **separated assemble → format → review → optional send** stages with audit manifests and mock-data validation paths for safe public demonstration.

---

## What remains private

| Never public | Reason |
|--------------|--------|
| `briefings/`, `todos/`, `memory.md` | Derived from live inbox and calendar context |
| `logs/`, `logs/audit/` | Operational traces tied to private runs |
| `video-workspace/` | May contain narration of private items |
| OAuth tokens, client secrets, `.env` | Credentials |
| VIP lists, personal contact identifiers | PII |
| Live audit hashes tied to real briefings | Fingerprinting private artifacts |

`.gitignore` excludes these paths — keep it that way for the public repository.

---

## Related reading in repo

- `docs/morning-assistant-safe-runner.md` — runner modes and gates  
- `docs/daily-briefing-quality-rubric.md` — triage standards  
- `prompts/safe-briefing-output-format.md` — output contract  
- `docs/patches/google-workspace-gmail-readonly/README.md`  
- `docs/patches/google-workspace-calendar-readonly/README.md`
