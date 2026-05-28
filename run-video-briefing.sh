#!/usr/bin/env bash
set -euo pipefail

# Full workflow wrapper for daily video briefings.
# Usage: ./run-video-briefing.sh [morning|midday|evening] [--voice VOICE] [--no-open]

SLOT="morning"
VOICE="Daniel"
OPEN_VIDEO=true

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    morning|midday|evening)
      SLOT="$1"
      shift
      ;;
    --voice)
      if [[ -z "${2:-}" ]]; then
        echo "ERROR: --voice requires an argument" >&2
        exit 1
      fi
      VOICE="$2"
      shift 2
      ;;
    --no-open)
      OPEN_VIDEO=false
      shift
      ;;
    *)
      echo "Usage: $0 [morning|midday|evening] [--voice VOICE] [--no-open]" >&2
      exit 1
      ;;
  esac
done

echo "=== Running Live Safe Briefing ($SLOT) ==="
./run-live-briefing.sh "$SLOT"

echo "=== Creating Local Video Briefing (voice: $VOICE) ==="
./scripts/create-local-video-briefing.sh --voice "$VOICE"

# Find newest generated MP4 under video-workspace/*/renders/*-briefing.mp4
LATEST_VIDEO=$(find video-workspace -name "*-briefing.mp4" -type f -exec stat -f "%m %N" {} + 2>/dev/null | sort -rn | head -n 1 | sed 's/^[0-9]* //')

if [[ -z "$LATEST_VIDEO" ]]; then
  echo "ERROR: Generated video briefing not found." >&2
  exit 1
fi

echo "=== Briefing Complete ==="
# Try to find corresponding final markdown briefing file
# The workspace is video-workspace/<stem>, and the briefing is briefings/<stem>-final.md
STEM=$(basename "$(dirname "$(dirname "$LATEST_VIDEO")")")
FINAL_MD="briefings/${STEM}-final.md"

if [[ -f "$FINAL_MD" ]]; then
  echo "Final briefing path: $FINAL_MD"
else
  echo "Final briefing path: (unknown/not found)"
fi

echo "Generated video path: $LATEST_VIDEO"

SRT_FILE="${LATEST_VIDEO%.mp4}.srt"
if [[ -f "$SRT_FILE" ]]; then
  echo "Generated SRT path: $SRT_FILE"
fi

if [ "$OPEN_VIDEO" = true ]; then
  echo "Opening generated briefing video..."
  open "$LATEST_VIDEO"
fi
