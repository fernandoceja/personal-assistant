#!/usr/bin/env bash
set -euo pipefail

# General manual run-on-demand wrapper for approved live read-only briefings.
# Usage: ./run-live-briefing.sh [morning|midday|evening] (default: morning)
#
# Safety scope (same as scripts/run-live-morning-briefing.sh):
# - Calls only run-briefing.sh in full-safe mode (dry-run safe packet assembly).
# - Opts in only to Google Calendar readonly and Gmail readonly safe-list access.
# - Does not send iMessage, update memory.md, write calendar events, or run Gmail legacy commands.

SLOT="${1:-morning}"

exec bash run-briefing.sh \
  --slot "$SLOT" \
  --mode full-safe \
  --allow-live-google-calendar \
  --allow-live-gmail-readonly
