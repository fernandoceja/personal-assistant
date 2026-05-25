#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

status() {
  printf '%s\n' "$*"
}

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    status "ERROR: Missing required file: $path" >&2
    exit 1
  fi
}

latest_final() {
  find briefings -maxdepth 1 -type f -name '*-final.md' -print0 \
    | xargs -0 stat -f '%m %N' 2>/dev/null \
    | sort -nr \
    | head -n 1 \
    | sed 's/^[0-9]* //'
}

extract_draft_path() {
  awk -F': ' '/^Draft path:/ {print $2; exit}' "$1"
}

status "Daily briefing dry-run chain started."
status "Safety: local dry-run, no iMessage send, no Gmail/Calendar mutation, no cron."

require_file "scripts/run-live-morning-briefing.sh"
require_file "scripts/create-imessage-briefing-draft.py"
require_file "scripts/send-imessage-briefing-draft.py"
require_file "scripts/create-briefing-video.py"
require_file "scripts/write-briefing-audit-manifest.py"

status "Step 1: run live read-only briefing."
scripts/run-live-morning-briefing.sh
briefing_status="ready"

final_path="$(latest_final)"
if [[ -z "$final_path" ]]; then
  status "ERROR: No final briefing found under briefings/." >&2
  exit 1
fi
status "Step 2: final briefing found: $final_path"

for heading in "Executive Summary" "Priority Now" "Review With Me" "Calendar Watch" "Low Priority" "Ignore/Suspicious"; do
  if ! grep -Fq "## $heading" "$final_path"; then
    status "ERROR: Final briefing missing heading: $heading" >&2
    exit 1
  fi
done

draft_log="$(mktemp)"
preview_log="$(mktemp)"
video_log="$(mktemp)"
trap 'rm -f "$draft_log" "$preview_log" "$video_log"' EXIT

status "Step 3: refresh iMessage draft from latest final."
python3 scripts/create-imessage-briefing-draft.py "$final_path" >"$draft_log"
draft_path="$(extract_draft_path "$draft_log")"
if [[ -z "$draft_path" ]]; then
  status "ERROR: Could not parse draft path." >&2
  exit 1
fi
require_file "$draft_path"
status "Draft path: $draft_path"

status "Step 4: create sanitized HyperFrames video artifact."
python3 scripts/create-briefing-video.py "$final_path" >"$video_log"
video_summary_path="$(python3 - "$video_log" <<'PY'
import json
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
data = json.loads(text)
print(data.get("summary_path") or "")
PY
)"
video_status="$(python3 - "$video_log" <<'PY'
import json
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
data = json.loads(text)
print(data.get("status") or "partial")
PY
)"
video_output_path="$(python3 - "$video_log" <<'PY'
import json
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
data = json.loads(text)
print(data.get("video_output_path") or "")
PY
)"
status "Video status: $video_status"
if [[ -n "$video_output_path" ]]; then
  status "Video path: $video_output_path"
else
  status "Video path: not created; storyboard/project created."
fi

status "Step 5: run iMessage preview in dry-run mode."
python3 scripts/send-imessage-briefing-draft.py "$draft_path" >"$preview_log"
if grep -Fq "Mode: DRY RUN" "$preview_log" && grep -Fq "osascript/Messages was not called" "$preview_log"; then
  imessage_preview_status="dry-run-confirmed"
else
  status "ERROR: iMessage preview did not confirm dry-run/no Messages call." >&2
  exit 1
fi
status "iMessage preview: dry-run confirmed."

status "Step 6: write paths-only audit manifest."
audit_log="$(mktemp)"
python3 scripts/write-briefing-audit-manifest.py \
  --final-briefing "$final_path" \
  --imessage-draft "$draft_path" \
  --video-summary-json "$video_summary_path" \
  --briefing-status "$briefing_status" \
  --imessage-preview-status "$imessage_preview_status" >"$audit_log"
audit_path="$(awk -F': ' '/^Audit manifest:/ {print $2; exit}' "$audit_log")"
rm -f "$audit_log"

status "Daily briefing dry-run chain complete."
status "Final briefing: $final_path"
status "iMessage draft: $draft_path"
status "Video summary: $video_summary_path"
[[ -n "$video_output_path" ]] && status "Video output: $video_output_path"
status "Audit manifest: $audit_path"
status "Safety result: no send, no cron, no Google writes."

if [[ "$video_status" != "ready" ]]; then
  status "Partial: video render not ready; HyperFrames project/storyboard exists."
fi
