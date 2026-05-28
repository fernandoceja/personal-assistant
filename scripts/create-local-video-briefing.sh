#!/usr/bin/env bash
set -euo pipefail

# Safely create a local HyperFrames video briefing from the latest final briefing.
# Usage: ./scripts/create-local-video-briefing.sh [--skip-render]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Find latest final briefing file
LATEST_FINAL="$(find briefings -maxdepth 1 -type f -name '*-final.md' -print0 \
  | xargs -0 stat -f '%m %N' 2>/dev/null \
  | sort -nr \
  | head -n 1 \
  | sed 's/^[0-9]* //')"

if [[ -z "$LATEST_FINAL" ]]; then
  echo "ERROR: No final briefing found in briefings/." >&2
  exit 1
fi

echo "Found latest final briefing: $LATEST_FINAL"
echo "Creating video briefing..."

python3 scripts/create-briefing-video.py "$LATEST_FINAL" "$@"
