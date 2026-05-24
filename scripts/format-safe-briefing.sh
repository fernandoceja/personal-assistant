#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORMAT_CONTRACT="$ROOT_DIR/prompts/safe-briefing-output-format.md"

INPUT_PATH=""
OUTPUT_PATH=""
EXECUTE_REQUESTED=0

usage() {
  cat <<'USAGE'
Usage: scripts/format-safe-briefing.sh --input PATH [--output PATH] [--execute]

Default behavior:
  Creates a formatter-ready prompt sidecar and a deterministic local final
  briefing. Does not call Codex, Hermes, Gmail, Calendar, or any live data source.
  Can distinguish Gmail not approved from mock and live Gmail safe-list source packets.

Output:
  If --output is omitted, the final briefing path is derived by replacing
  -safe.md with -final.md in the input path.

Execution:
  --execute explicitly calls Codex CLI and writes final output to the final
  briefing path. It never appends final output to the source packet. Omit
  --execute for fully local non-live validation.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --input requires a value." >&2
        usage >&2
        exit 2
      fi
      INPUT_PATH="$2"
      shift 2
      ;;
    --output)
      if [[ $# -lt 2 ]]; then
        echo "ERROR: --output requires a value." >&2
        usage >&2
        exit 2
      fi
      OUTPUT_PATH="$2"
      shift 2
      ;;
    --execute)
      EXECUTE_REQUESTED=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$INPUT_PATH" ]]; then
  echo "ERROR: --input is required." >&2
  usage >&2
  exit 2
fi

if [[ ! -f "$INPUT_PATH" ]]; then
  echo "ERROR: Input source packet not found: $INPUT_PATH" >&2
  exit 1
fi

if [[ ! -f "$FORMAT_CONTRACT" ]]; then
  echo "ERROR: Format contract not found: $FORMAT_CONTRACT" >&2
  exit 1
fi

if [[ -z "$OUTPUT_PATH" ]]; then
  if [[ "$INPUT_PATH" != *-safe.md ]]; then
    echo "ERROR: --output is required when input does not end with -safe.md." >&2
    exit 2
  fi
  OUTPUT_PATH="${INPUT_PATH%-safe.md}-final.md"
fi

output_dir="$(dirname "$OUTPUT_PATH")"
mkdir -p "$output_dir"

prompt_path="${OUTPUT_PATH%.md}-formatter-prompt.md"

{
  echo "# Safe Briefing Formatter Prompt"
  echo
  echo "Goal: Convert the source packet below into a final personal-assistant briefing."
  echo
  echo "Return only the final briefing. Always include exactly these six top-level headings as ## headings, in this exact order:"
  echo
  echo "1. Executive Summary"
  echo "2. Priority Now"
  echo "3. Review With Me"
  echo "4. Calendar Watch"
  echo "5. Low Priority"
  echo "6. Ignore/Suspicious"
  echo
  echo "Required empty-section placeholders:"
  echo "- If a section has no source-backed items, write: No source-backed items in this packet."
  echo "- For Ignore/Suspicious with no approved email or message source, write: No email or message source was approved for this packet."
  echo
  echo "Safety and privacy rules:"
  echo "- Do not invent missing source data."
  echo "- Do not omit any of the six required headings."
  echo "- Treat legal, immigration, money, work, school, and deadline uncertainty as Review With Me."
  echo "- Keep output short and scannable."
  echo "- Do not include secrets, tokens, credentials, OAuth artifacts, or raw debug blocks."
  echo "- Do not expose more private calendar detail than needed."
  echo "- Do not create, modify, send, schedule, archive, delete, or persist anything beyond the requested output file."
  echo
  echo "## Format Contract"
  echo
  cat "$FORMAT_CONTRACT"
  echo
  echo "## Source Packet"
  echo
  cat "$INPUT_PATH"
} > "$prompt_path"

source_has() {
  grep -Fq "$1" "$INPUT_PATH"
}

calendar_state_summary() {
  local local_state="not_checked"
  local google_state="not_checked"

  if source_has "## Local Apple Calendar Diagnostics"; then
    if source_has "Result: events found successfully."; then
      local_state="items_found"
    elif source_has "Result: preferred calendars found, but no events were found for today/tomorrow."; then
      local_state="checked_no_items"
    elif source_has "Permission/status: granted — Calendar.app read completed."; then
      local_state="checked_no_items"
    fi
  fi

  if source_has "## Google Calendar Readonly Diagnostics"; then
    if source_has "Result: success — Google Calendar readonly safe-list completed."; then
      if awk '
        /^## Google Calendar Readonly Diagnostics$/ { in_section=1; next }
        in_section && /^## / { in_section=0 }
        in_section && /^\[\]$/ { found_empty=1 }
        END { exit(found_empty ? 0 : 1) }
      ' "$INPUT_PATH"; then
        google_state="checked_no_items"
      else
        google_state="items_found"
      fi
    fi
  elif source_has "Google Calendar live data not accessed. Run with --allow-live-google-calendar to include readonly Google Calendar."; then
    google_state="not_checked"
  fi

  printf '%s|%s\n' "$local_state" "$google_state"
}

gmail_state_summary() {
  local gmail_state="not_checked"

  if source_has "GMAIL_SAFE_LIST_JSON_BEGIN"; then
    gmail_state="live_checked"
  elif source_has "GMAIL_MOCK_SAFE_LIST_JSON_BEGIN"; then
    gmail_state="mock_checked"
  elif source_has "Gmail readonly support is gated but live Gmail is not implemented yet. No Gmail access performed." || source_has "Gmail readonly support is gated but not implemented yet. No Gmail access performed."; then
    gmail_state="planned_not_implemented"
  elif source_has "Gmail live data not accessed. Run with --allow-live-gmail-readonly to include readonly Gmail diagnostics."; then
    gmail_state="not_approved"
  elif source_has "Gmail checked; no source-backed items found."; then
    gmail_state="checked_no_items"
  fi

  printf '%s\n' "$gmail_state"
}

gmail_ignore_text() {
  local gmail_state="$1"

  case "$gmail_state" in
    planned_not_implemented)
      echo "Gmail readonly was explicitly gated for this run, but Gmail support is not implemented yet. No email source was accessed."
      ;;
    live_checked)
      echo "Live Gmail readonly safe-list source was included; suspicious records are summarized below."
      ;;
    mock_checked)
      echo "Mock Gmail safe-list source was included; suspicious mock records are summarized below."
      ;;
    checked_no_items)
      echo "Gmail readonly source was checked and returned no source-backed items."
      ;;
    not_approved|not_checked|*)
      echo "No email or message source was approved for this packet."
      ;;
  esac
}

calendar_watch_text() {
  local local_state="$1"
  local google_state="$2"

  if [[ "$local_state" == "items_found" || "$google_state" == "items_found" ]]; then
    if [[ "$local_state" == "items_found" && "$google_state" == "items_found" ]]; then
      echo "Local calendar and Google Calendar readonly sources were checked; today/tomorrow items were found. Review the source packet for safe event details."
    elif [[ "$local_state" == "items_found" ]]; then
      if [[ "$google_state" == "checked_no_items" ]]; then
        echo "Local calendar was checked and returned today/tomorrow items; Google Calendar readonly was checked and returned no events."
      else
        echo "Local calendar was checked and returned today/tomorrow items; Google Calendar readonly was not checked."
      fi
    else
      if [[ "$local_state" == "checked_no_items" ]]; then
        echo "Local calendar was checked and returned no today/tomorrow events; Google Calendar readonly was checked and returned items."
      else
        echo "Google Calendar readonly was checked and returned today/tomorrow items; local calendar was not checked."
      fi
    fi
  elif [[ "$local_state" == "checked_no_items" && "$google_state" == "checked_no_items" ]]; then
    echo "Local calendar and Google Calendar readonly sources were checked; no today/tomorrow events were found."
  elif [[ "$local_state" == "checked_no_items" ]]; then
    echo "Local calendar was checked; no today/tomorrow events were found. Google Calendar readonly was not checked."
  elif [[ "$google_state" == "checked_no_items" ]]; then
    echo "Google Calendar readonly was checked; no today/tomorrow events were found. Local calendar was not checked."
  else
    echo "Calendar sources were not checked in this packet."
  fi
}

executive_summary_text() {
  local local_state="$1"
  local google_state="$2"

  if [[ "$local_state" == "items_found" || "$google_state" == "items_found" ]]; then
    echo "Calendar sources were checked and returned today/tomorrow items; review Calendar Watch."
  elif [[ "$local_state" == "checked_no_items" || "$google_state" == "checked_no_items" ]]; then
    echo "No urgent or calendar-backed items found for today/tomorrow."
  else
    echo "No source-backed items in this packet."
  fi
}

write_gmail_safe_list_final() {
  local marker_prefix="$1"
  local source_label="$2"
  INPUT_PATH="$INPUT_PATH" OUTPUT_PATH="$OUTPUT_PATH" MARKER_PREFIX="$marker_prefix" SOURCE_LABEL="$source_label" python3 <<'PY'
import json
import os
import re
from datetime import date
from pathlib import Path

input_path = Path(os.environ["INPUT_PATH"])
output_path = Path(os.environ["OUTPUT_PATH"])
marker_prefix = os.environ["MARKER_PREFIX"]
source_label = os.environ["SOURCE_LABEL"]
text = input_path.read_text()
start_marker = f"{marker_prefix}_JSON_BEGIN"
end_marker = f"{marker_prefix}_JSON_END"
start = text.index(start_marker) + len(start_marker)
end = text.index(end_marker, start)
raw_records = json.loads(text[start:end].strip() or "[]")
if isinstance(raw_records, dict):
    raw_records = raw_records.get("records", [])
if not isinstance(raw_records, list):
    raw_records = []

allowed_fields = {
    "source", "category", "sender_display", "sender_domain", "subject", "received_at",
    "snippet", "labels", "has_attachment", "matched_filter", "triage_hint", "safety_notes",
}
allowed_sections = ["Priority Now", "Review With Me", "Calendar Watch", "Low Priority", "Ignore/Suspicious"]
records = []

def sanitize_visible(value):
    text = str(value or "")
    text = re.sub(r"https?://\S+", "[redacted-url]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(access|refresh)?_?token\b\s*[:=]\s*[\w.\-/]+", "[redacted-token]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(client_secret|credential|oauth|auth code)\b\s*[:=]?\s*[\w.\-/]*", "[redacted-credential]", text, flags=re.IGNORECASE)
    text = re.sub(r"\bya29\.[\w.\-/]+", "[redacted-token]", text)
    text = re.sub(r"\b4/[A-Za-z0-9_\-]+", "[redacted-auth-code]", text)
    return " ".join(text.split())[:180]

for record in raw_records:
    if not isinstance(record, dict):
        continue
    item = {k: v for k, v in record.items() if k in allowed_fields}
    for field in ("sender_display", "sender_domain", "subject", "category", "received_at", "matched_filter", "triage_hint"):
        if field in item:
            item[field] = sanitize_visible(item[field])
    if item.get("triage_hint") not in allowed_sections:
        item["triage_hint"] = "Review With Me"
    records.append(item)

groups = {name: [] for name in allowed_sections}
for record in records:
    subject = str(record.get("subject", ""))
    category = str(record.get("category", ""))
    sender = str(record.get("sender_display", ""))
    domain = str(record.get("sender_domain", ""))
    snippet = str(record.get("snippet", ""))
    blob = " ".join([subject, category, sender, domain, snippet]).lower()
    hint = record.get("triage_hint", "Review With Me")

    unknown_sender = (
        not sender.strip()
        or sender.strip().lower() in {"unknown", "unknown sender"}
        or not domain.strip()
        or domain.strip().lower() in {"unknown", "unknown domain"}
    )
    billing_security = any(word in blob for word in ["bill", "billing", "payment", "security", "verify", "suspended", "account", "bank"])
    urgent = any(word in blob for word in ["today", "tomorrow", "due", "deadline", "past due", "failed", "locked", "fraud", "urgent", "action required"])
    suspicious = any(word in blob for word in ["phishing", "fake", "suspicious", "credential", "verify your account", "suspended"])
    school = any(word in blob for word in ["umgc", "tuition", "statement", "drop", "withdrawal", "fafsa", "financial aid", "student account"])
    money = any(word in blob for word in ["bank", "payment", "balance", "bofa", "fidelity", "ibkr", "e*trade", "rocket money", "ihss", "statement"])
    legal = any(word in blob for word in ["uscis", "legal", "immigration"])
    work = any(word in blob for word in ["apple", "work", "schedule", "shift", "hr"])
    security = any(word in blob for word in ["security", "fraud", "login", "password", "account locked", "new device"])

    if unknown_sender and billing_security:
        hint = "Ignore/Suspicious"
    elif suspicious and unknown_sender:
        hint = "Ignore/Suspicious"
    elif urgent and (legal or work or school or money or security):
        hint = "Priority Now"
    elif legal or school or money or security or work:
        hint = "Review With Me"
    elif hint not in allowed_sections:
        hint = "Review With Me"

    record["_section"] = hint
    groups.setdefault(hint, []).append(record)

def review_category(record):
    blob = " ".join(str(record.get(k, "")) for k in ("subject", "category", "sender_display", "sender_domain", "snippet")).lower()
    if any(word in blob for word in ["uscis", "legal", "immigration"]):
        return "legal/immigration"
    if any(word in blob for word in ["umgc", "tuition", "statement", "drop", "withdrawal", "fafsa", "financial aid", "student account"]):
        return "school"
    if any(word in blob for word in ["apple", "work", "schedule", "shift", "hr"]):
        return "work"
    if any(word in blob for word in ["security", "fraud", "login", "password", "new device", "locked"]):
        return "account security"
    if any(word in blob for word in ["bank", "payment", "balance", "bofa", "fidelity", "ibkr", "e*trade", "rocket money", "ihss", "bill"]):
        return "money"
    if "routine" in blob:
        return "routine"
    return "uncertain"

def timing_text(record):
    received = record.get("received_at", "") or ""
    blob = " ".join(str(record.get(k, "")) for k in ("subject", "snippet", "category")).lower()
    if any(word in blob for word in ["today", "tomorrow", "due", "deadline", "past due"]):
        return received or "Source indicates timing; verify exact deadline."
    return "Timing unclear - verify."

def priority_line(record):
    sender = sanitize_visible(record.get("sender_display", "Unknown sender") or "Unknown sender")
    domain = sanitize_visible(record.get("sender_domain", "unknown domain") or "unknown domain")
    subject = sanitize_visible(record.get("subject", "(no subject)") or "(no subject)")
    category = sanitize_visible(record.get("category", "uncategorized") or "uncategorized")
    timing = timing_text(record)
    return (
        f"- Source: {source_label}. Sender/Event: {sender} ({domain}). "
        f"Subject: {subject}. Timing: {timing}. Importance: {category}; urgent or deadline-sensitive source signal. "
        "Next Action: Review source directly before acting."
    )

def review_line(record):
    sender = sanitize_visible(record.get("sender_display", "Unknown sender") or "Unknown sender")
    domain = sanitize_visible(record.get("sender_domain", "unknown domain") or "unknown domain")
    subject = sanitize_visible(record.get("subject", "(no subject)") or "(no subject)")
    category = review_category(record)
    return (
        f"- {sender} ({domain}) — {subject}. Why this matters: source suggests {category} review. "
        f"What to verify: confirm details in the original source. Category: {category}. "
        "Conservative next action: Review with Fernando before any action."
    )

def compact_line(record):
    sender = sanitize_visible(record.get("sender_display", "Unknown sender") or "Unknown sender")
    domain = sanitize_visible(record.get("sender_domain", "unknown domain") or "unknown domain")
    subject = sanitize_visible(record.get("subject", "(no subject)") or "(no subject)")
    category = sanitize_visible(record.get("category", "uncategorized") or "uncategorized")
    return f"- {source_label} — {sender} ({domain}) — {subject} — {category}. Safe-list metadata only; raw Gmail details omitted."

summary = []
priority_count = len(groups.get("Priority Now", []))
review_count = len(groups.get("Review With Me", []))
suspicious_count = len(groups.get("Ignore/Suspicious", []))
low_count = len(groups.get("Low Priority", []))
calendar_count = len(groups.get("Calendar Watch", []))
if priority_count:
    summary.append(f"- {priority_count} Gmail safe-list item(s) need Priority Now handling.")
if review_count:
    summary.append(f"- {review_count} Gmail safe-list item(s) need Review With Me handling for money/security/legal/work uncertainty.")
if suspicious_count:
    summary.append(f"- {suspicious_count} Gmail safe-list item(s) were routed to Ignore/Suspicious.")
if not summary and (low_count or calendar_count):
    summary.append(f"- Gmail safe-list returned {len(records)} source-backed item(s), with no Priority Now or Review With Me items.")
if not summary:
    summary.append("- Gmail safe-list returned no source-backed items.")
summary = summary[:3]

with output_path.open("w") as fh:
    fh.write(f"# Safe Briefing — {date.today().isoformat()}\n\n")
    fh.write("## Executive Summary\n")
    fh.write("\n".join(summary) + "\n\n")

    for section in allowed_sections:
        fh.write(f"## {section}\n")
        items = groups.get(section, [])
        if section == "Calendar Watch" and not items:
            fh.write("No clear date/time commitments from Gmail safe-list records. No events created.\n\n")
        elif items:
            for record in items:
                if section == "Priority Now":
                    fh.write(priority_line(record) + "\n")
                elif section == "Review With Me":
                    fh.write(review_line(record) + "\n")
                else:
                    fh.write(compact_line(record) + "\n")
            fh.write("\n")
        else:
            fh.write("No source-backed items in this packet.\n\n")
PY
}
write_local_final() {
  local states local_state google_state gmail_state executive_summary calendar_note ignore_note
  states="$(calendar_state_summary)"
  local_state="${states%%|*}"
  google_state="${states#*|}"
  gmail_state="$(gmail_state_summary)"
  if [[ "$gmail_state" == "live_checked" ]]; then
    write_gmail_safe_list_final "GMAIL_SAFE_LIST" "Gmail readonly"
    return 0
  fi
  if [[ "$gmail_state" == "mock_checked" ]]; then
    write_gmail_safe_list_final "GMAIL_MOCK_SAFE_LIST" "Gmail mock"
    return 0
  fi
  executive_summary="$(executive_summary_text "$local_state" "$google_state")"
  calendar_note="$(calendar_watch_text "$local_state" "$google_state")"
  ignore_note="$(gmail_ignore_text "$gmail_state")"

  cat > "$OUTPUT_PATH" <<FINAL
# Safe Briefing — $(date +%Y-%m-%d)

## Executive Summary
$executive_summary

## Priority Now
No source-backed items in this packet.

## Review With Me
No source-backed items in this packet.

## Calendar Watch
$calendar_note

## Low Priority
No source-backed items in this packet.

## Ignore/Suspicious
$ignore_note
FINAL
}

if [[ $EXECUTE_REQUESTED -eq 0 ]]; then
  write_local_final
  cat <<SUMMARY
Safe briefing formatter local formatting complete.
Input source packet: $INPUT_PATH
Formatter prompt: $prompt_path
Final output: $OUTPUT_PATH
Execution backend: not called
SUMMARY
  exit 0
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: --execute requested, but Codex CLI was not found." >&2
  exit 1
fi

codex exec - --output-last-message "$OUTPUT_PATH" < "$prompt_path"

cat <<SUMMARY
Safe briefing formatter execution complete.
Input source packet: $INPUT_PATH
Formatter prompt: $prompt_path
Final output: $OUTPUT_PATH
Execution backend: Codex CLI
SUMMARY
