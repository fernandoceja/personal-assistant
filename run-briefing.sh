#!/bin/bash
# Personal Assistant — Daily Briefing Runner
# Invoked by launchd at 8 AM, 1 PM, and 6 PM PST.
# Runs the Claude Code CLI non-interactively against the daily-briefing prompt.

PROJECT_DIR="/Users/fernandoceja/Documents/AI-Projects/personal-assistant"
CLAUDE_BIN="/Users/fernandoceja/.local/bin/claude"
LOG_FILE="$PROJECT_DIR/logs/briefing-$(date '+%Y-%m-%d').log"

cd "$PROJECT_DIR"

echo "=== Briefing run started: $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG_FILE"

echo "Read CLAUDE.md and memory.md in the current directory. Then read prompts/daily-briefing.md and follow it exactly. Today is $(date '+%Y-%m-%d') and the current time is $(date '+%H:%M %Z'). Use Gmail MCP for email and Google Calendar MCP for events. Write the briefing to briefings/ using YYYY-MM-DD-HH.md format. Send iMessage to fceja9864@icloud.com via osascript. Update memory.md." \
  | "$CLAUDE_BIN" \
      --print \
      --permission-mode bypassPermissions \
      --allowedTools "Bash,Read,Write,Edit,Glob,Grep" \
  2>&1 >> "$LOG_FILE"

echo "=== Briefing run finished: $(date '+%Y-%m-%d %H:%M:%S %Z') ===" >> "$LOG_FILE"
