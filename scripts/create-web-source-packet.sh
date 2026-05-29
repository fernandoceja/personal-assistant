#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_AGENT_DIR="${HERMES_AGENT_DIR:-$HOME/Projects/hermes-agent-test/hermes-agent}"
HERMES_TEST_HOME="${HOME_OVERRIDE:-${HERMES_TEST_HOME:-$HOME/Projects/hermes-agent-test/home}}"
HERMES_TEST_HOME_DIR="${HERMES_HOME_OVERRIDE:-${HERMES_HOME:-$HOME/Projects/hermes-agent-test/home/.hermes}}"
OUTPUT_DIR="$ROOT_DIR/source-packets/web"

QUERY=""
LABEL=""
MAX_RESULTS="5"

usage() {
  cat <<'USAGE'
Usage:
  scripts/create-web-source-packet.sh --query "public query" --label "safe label" [--max-results N]

Creates local source-packets/web/*.md from an explicitly approved public web query.
Public-only: routes through Hermes web_search after plugin discovery.
Does not print Tavily API keys or send private source-packet/Gmail/Calendar/Drive/Docs/Sheets data.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --query)
      [[ $# -ge 2 ]] || { echo "ERROR: --query requires a value." >&2; exit 2; }
      QUERY="$2"
      shift 2
      ;;
    --label)
      [[ $# -ge 2 ]] || { echo "ERROR: --label requires a value." >&2; exit 2; }
      LABEL="$2"
      shift 2
      ;;
    --max-results)
      [[ $# -ge 2 ]] || { echo "ERROR: --max-results requires a value." >&2; exit 2; }
      MAX_RESULTS="$2"
      shift 2
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

if [[ -z "$QUERY" ]]; then
  echo "ERROR: --query is required." >&2
  usage >&2
  exit 2
fi

if [[ -z "$LABEL" ]]; then
  echo "ERROR: --label is required." >&2
  usage >&2
  exit 2
fi

if ! [[ "$MAX_RESULTS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: --max-results must be a positive integer." >&2
  exit 2
fi

if (( MAX_RESULTS < 1 || MAX_RESULTS > 20 )); then
  echo "ERROR: --max-results must be between 1 and 20." >&2
  exit 2
fi

private_pattern='gmail|email[[:space:]-]*body|bank[[:space:]-]*account|password|token|oauth|uscis[[:space:]-]*receipt[[:space:]-]*number|ssn|social[[:space:]-]*security|private[[:space:]-]*doc|source-packets/docs|/Users/'
if printf '%s\n%s\n' "$QUERY" "$LABEL" | LC_ALL=C grep -Eiq "$private_pattern"; then
  echo "ERROR: refused likely-private query or label. Use public-only search terms." >&2
  exit 2
fi

if [[ ! -d "$HERMES_AGENT_DIR" ]]; then
  echo "ERROR: Hermes agent directory not found: $HERMES_AGENT_DIR" >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"

HOME="$HERMES_TEST_HOME" \
HERMES_HOME="$HERMES_TEST_HOME_DIR" \
PACKET_OUTPUT_DIR="$OUTPUT_DIR" \
uv run --python 3.11 --directory "$HERMES_AGENT_DIR" python - "$QUERY" "$LABEL" "$MAX_RESULTS" <<'PY'
import json
import os
import re
import sys
import time
from pathlib import Path

query = sys.argv[1]
label = sys.argv[2]
max_results = int(sys.argv[3])

hermes_home = Path(os.environ["HERMES_HOME"])
env_path = hermes_home / ".env"
output_dir = Path(os.environ["PACKET_OUTPUT_DIR"])

for raw in env_path.read_text(errors="ignore").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if key and key not in os.environ:
        os.environ[key] = value

from hermes_cli.plugins import discover_plugins
discover_plugins()

from agent.web_search_registry import get_provider, list_providers
from tools.web_tools import _get_search_backend, web_search_tool

def redact(value: str) -> str:
    value = re.sub(r"tvly-[A-Za-z0-9_-]+", "[REDACTED_TAVILY_KEY]", value)
    value = re.sub(r"api_key", "API key parameter", value)
    return value

def clean_text(value: object, limit: int = 500) -> str:
    text = redact(str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text

def safe_label(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return cleaned[:70] or "public-web"

backend = _get_search_backend()
provider = get_provider(backend) if backend else None
provider_name = provider.display_name if provider else ""
provider_class = type(provider).__name__ if provider else ""
registered = [p.name for p in list_providers()]

raw_result = web_search_tool(query, limit=max_results)
result = json.loads(redact(raw_result))
web_results = (result.get("data") or {}).get("web") or result.get("results") or []
success = bool(result.get("success", bool(web_results)))

created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
output_path = output_dir / f"{stamp}-{safe_label(label)}.md"

lines = [
    f"# Public Web Source Packet - {label}",
    "",
    "## Metadata",
    f"- Query: {query}",
    f"- Label: {label}",
    f"- Created: {created}",
    f"- Backend: {backend or 'unknown'}",
    f"- Provider: {provider_name or 'unknown'} ({provider_class or 'unknown'})",
    "- Tool path: Hermes `tools.web_tools.web_search_tool` after plugin discovery.",
    "- Safety note: public web only; no private Gmail, Calendar, Drive, Docs, Sheets, source-packet, credential, token, financial, legal, immigration, or account-security content sent.",
    "",
    "## Public Results",
]

for idx, item in enumerate(web_results[:max_results], 1):
    title = clean_text(item.get("title") or item.get("name"), limit=180)
    url = clean_text(item.get("url"), limit=260)
    snippet = clean_text(
        item.get("description") or item.get("content") or item.get("snippet"),
        limit=500,
    )
    lines.extend(
        [
            f"{idx}. {title or '[untitled result]'}",
            f"   - URL: {url or '[no URL returned]'}",
            f"   - Snippet: {snippet or '[no snippet returned]'}",
        ]
    )

lines.extend(
    [
        "",
        "## Validation",
        f"- Hermes web_search success: {success}",
        f"- Result count: {len(web_results)}",
        f"- Tavily registered: {'tavily' in registered}",
        "",
        "## Unknowns / Needs Verification",
        "- Verify official sources directly before relying on pricing, limits, dates, or API behavior.",
        "",
        "## Recommended Use",
        "- Use this packet as public-source context only. Keep generated packets out of git.",
    ]
)

output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

print(f"PACKET_PATH={output_path}")
print(f"BACKEND={backend}")
print(f"PROVIDER={provider_name or 'unknown'}")
print(f"RESULT_COUNT={len(web_results)}")
print(f"SUCCESS={'yes' if success else 'no'}")
print("SAFETY=public-only query; no private content sent")
PY
