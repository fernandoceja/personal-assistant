#!/usr/bin/env bash
set -euo pipefail

# Manual/run-on-demand wrapper for the approved live read-only morning briefing.
# Safety scope:
# - Calls only run-briefing.sh in full-safe mode.
# - Opts in only to Google Calendar readonly and Gmail readonly safe-list access.
# - Does not send iMessage, update memory.md, write calendar events, or run Gmail legacy commands.
# - Scheduling/cron/LaunchAgents are intentionally not configured here.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

exec bash run-briefing.sh \
  --slot morning \
  --mode full-safe \
  --allow-live-google-calendar \
  --allow-live-gmail-readonly
