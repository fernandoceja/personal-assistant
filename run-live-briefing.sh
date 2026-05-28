#!/usr/bin/env bash
set -euo pipefail

# General manual run-on-demand wrapper for safe live read-only briefings.
# Usage: ./run-live-briefing.sh [morning|midday|evening] (default: morning)

SLOT="${1:-morning}"

exec bash run-briefing.sh \
  --slot "$SLOT" \
  --mode full-safe \
  --allow-live-google-calendar \
  --allow-live-gmail-readonly
