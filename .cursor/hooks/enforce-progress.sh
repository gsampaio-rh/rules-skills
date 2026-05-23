#!/bin/bash
# Stop hook: forces progress tracking when the agent modifies multiple files.
# If 2+ files are changed and .cursor/breadcrumbs.jsonl wasn't updated recently, block.
# Skips when adversarial harness is active (it has its own enforcement).

input=$(cat)

CONTRACT=".cursor/harness/contract.json"
if [ -f "$CONTRACT" ]; then
  echo '{}'
  exit 0
fi

CHANGED=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
STAGED=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')
TOTAL=$((CHANGED + STAGED + UNTRACKED))

if [ "$TOTAL" -lt 2 ]; then
  echo '{}'
  exit 0
fi

BREADCRUMBS=".cursor/breadcrumbs.jsonl"

if [ -f "$BREADCRUMBS" ]; then
  NOW=$(date +%s)
  MTIME=$(stat -f %m "$BREADCRUMBS" 2>/dev/null || stat -c %Y "$BREADCRUMBS" 2>/dev/null || echo 0)
  AGE=$((NOW - MTIME))

  if [ "$AGE" -lt 180 ]; then
    echo '{}'
    exit 0
  fi
fi

CHANGED_LIST=$(git diff --name-only 2>/dev/null | head -10)
STAGED_LIST=$(git diff --cached --name-only 2>/dev/null | head -10)
UNTRACKED_LIST=$(git ls-files --others --exclude-standard 2>/dev/null | head -10)

ALL_FILES=$(printf "%s\n%s\n%s" "$CHANGED_LIST" "$STAGED_LIST" "$UNTRACKED_LIST" | sort -u | head -10)

cat <<EOF
{
  "followup_message": "PROGRESS CHECK: You modified $TOTAL files but .cursor/breadcrumbs.jsonl is missing or stale. Before ending your turn:\n1. Append a breadcrumb to .cursor/breadcrumbs.jsonl: {\"ts\":\"...\",\"role\":\"builder\",\"type\":\"build\",\"feat\":null,\"msg\":\"what you did\"}\n2. If you haven't used TodoWrite for this task, create a todo list now\n3. Files changed:\n$ALL_FILES\n\nDo NOT skip this — progress tracking is required for multi-file changes."
}
EOF
exit 0
