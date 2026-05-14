# Google Workspace Calendar Read-Only Safety Patch

## Why this patch exists

This backup preserves the Phase 2 Calendar safety patch for the Hermes Google Workspace skill. The patch exists so assistant calendar workflows can support read-only Morning Assistant review without granting or using calendar write access.

The goal is to keep Phase 2 calendar handling narrow, auditable, and safe:

- No calendar event creation.
- No calendar event deletion.
- No broad calendar OAuth scope for the Morning Assistant workflow.
- No legacy calendar commands for Morning Assistant calendar reads.
- Only a safe calendar read path with a strict fields mask.

## Required OAuth scope

Calendar OAuth for this workflow must use only:

https://www.googleapis.com/auth/calendar.readonly

Do not use the full calendar scope for Phase 2 assistant calendar workflows.

## Approved Phase 2 assistant calendar command

Phase 2 assistant workflows must use:

calendar safe-list

This command is intended as the approved safe calendar read path for the Morning Assistant workflow.

## Commands not approved for Morning Assistant

The legacy calendar commands are not approved for the Morning Assistant workflow:

- calendar list
- calendar create
- calendar delete

These may exist for other/manual Google Workspace use cases, but they are not approved for Phase 2 Morning Assistant calendar reads.

## Safe fields mask

The approved safe fields mask is:

items(summary,start,end,location)

This limits returned calendar event data to the minimum fields needed for assistant briefing review.

## Files preserved here

This folder contains backup/documentation copies of the patched installed skill files:

- setup.py
- google_api.py

Original installed skill location:

/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts/

Backup location:

/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/patches/google-workspace-calendar-readonly/

## Validation commands

Run the following from any directory:

```bash
DEST="/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/patches/google-workspace-calendar-readonly"
SRC="/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts"

# Confirm backup files exist
ls -l "$DEST/setup.py" "$DEST/google_api.py" "$DEST/README.md"

# Confirm backup copies match the installed patched files
cmp -s "$SRC/setup.py" "$DEST/setup.py" && echo "setup.py backup matches installed file"
cmp -s "$SRC/google_api.py" "$DEST/google_api.py" && echo "google_api.py backup matches installed file"

# Confirm read-only calendar scope is present
grep -n "https://www.googleapis.com/auth/calendar.readonly" "$DEST/setup.py" "$DEST/google_api.py"

# Confirm safe command and safe fields mask are present
grep -n "safe-list" "$DEST/google_api.py"
grep -n "items(summary,start,end,location)" "$DEST/google_api.py"

# Confirm Python syntax without authenticating or reading Calendar data
python3 -m py_compile "$DEST/setup.py" "$DEST/google_api.py"
```

These commands do not authenticate, open OAuth, read calendar data, create schedules, or access private accounts.

## Rollback / reapply notes

If the installed Google Workspace skill is overwritten by an update, restore the Phase 2 safety patch by copying these backup files back into the installed skill scripts folder:

```bash
DEST="/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/patches/google-workspace-calendar-readonly"
SRC="/Users/fernandoceja/Documents/AI-Projects/hermes-agent-test/home/.hermes/skills/productivity/google-workspace/scripts"

cp "$DEST/setup.py" "$SRC/setup.py"
cp "$DEST/google_api.py" "$SRC/google_api.py"

python3 -m py_compile "$SRC/setup.py" "$SRC/google_api.py"
grep -n "https://www.googleapis.com/auth/calendar.readonly" "$SRC/setup.py" "$SRC/google_api.py"
grep -n "safe-list" "$SRC/google_api.py"
grep -n "items(summary,start,end,location)" "$SRC/google_api.py"
```

After reapplying, keep Morning Assistant calendar workflows limited to `calendar safe-list` and the `calendar.readonly` OAuth scope.
