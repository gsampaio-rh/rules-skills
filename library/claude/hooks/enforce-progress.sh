#!/bin/bash
# Stop hook: two-tier enforcement for progress tracking and harness usage.
# Tier 1: 2+ files changed without fresh breadcrumbs → ask for breadcrumbs
# Tier 2: 4+ files changed without a contract → ask why harness isn't being used
# Skips when adversarial harness is active (it has its own enforcement).
# Output: decision "block" with reason for Stop event

input=$(cat)

HOOK_LOG=".claude/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: triggered" >> "$HOOK_LOG" 2>/dev/null

# Check stop_hook_active to prevent infinite loops
STOP_HOOK_ACTIVE=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(str(data.get('stop_hook_active', False)))
except Exception:
    print('False')
" 2>/dev/null)

if [ "$STOP_HOOK_ACTIVE" = "True" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: stop_hook_active, skipping" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

CONTRACT=".claude/harness/contract.json"
if [ -f "$CONTRACT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: contract exists, skipping" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

CHANGED=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
STAGED=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')
TOTAL=$((CHANGED + STAGED + UNTRACKED))

if [ "$TOTAL" -lt 2 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: $TOTAL files changed, below threshold" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

BREADCRUMBS=".claude/breadcrumbs.jsonl"
BREADCRUMBS_FRESH=false

if [ -f "$BREADCRUMBS" ]; then
  NOW=$(date +%s)
  MTIME=$(stat -f %m "$BREADCRUMBS" 2>/dev/null || stat -c %Y "$BREADCRUMBS" 2>/dev/null || echo 0)
  AGE=$((NOW - MTIME))

  if [ "$AGE" -lt 180 ]; then
    BREADCRUMBS_FRESH=true
  fi
fi

# Tier 2: 4+ files without a contract → harness enforcement
if [ "$TOTAL" -ge 4 ] && [ "$BREADCRUMBS_FRESH" = true ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: $TOTAL files, breadcrumbs fresh, but no contract — harness warning" >> "$HOOK_LOG" 2>/dev/null

  CHANGED_LIST=$(git diff --name-only 2>/dev/null | head -10)
  STAGED_LIST=$(git diff --cached --name-only 2>/dev/null | head -10)
  UNTRACKED_LIST=$(git ls-files --others --exclude-standard 2>/dev/null | head -10)
  ALL_FILES=$(printf "%s\n%s\n%s" "$CHANGED_LIST" "$STAGED_LIST" "$UNTRACKED_LIST" | sort -u | head -10)

  cat <<EOF
{
  "decision": "block",
  "reason": "HARNESS CHECK: You modified $TOTAL files without an active harness contract. For non-trivial work (3+ files, user-facing behavior, architectural changes), the adversarial harness should be used: /planner → contract negotiation → /evaluator.\n\nIf this IS simple work, add a breadcrumb explaining why harness was skipped:\n{\"ts\":\"...\",\"role\":\"builder\",\"type\":\"decision\",\"feat\":null,\"msg\":\"Skipped harness: <reason>\"}\n\nFiles changed:\n$ALL_FILES"
}
EOF
  exit 0
fi

# Tier 1: 2+ files without fresh breadcrumbs → breadcrumbs enforcement
if [ "$BREADCRUMBS_FRESH" = false ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: $TOTAL files, no fresh breadcrumbs — breadcrumbs required" >> "$HOOK_LOG" 2>/dev/null

  CHANGED_LIST=$(git diff --name-only 2>/dev/null | head -10)
  STAGED_LIST=$(git diff --cached --name-only 2>/dev/null | head -10)
  UNTRACKED_LIST=$(git ls-files --others --exclude-standard 2>/dev/null | head -10)
  ALL_FILES=$(printf "%s\n%s\n%s" "$CHANGED_LIST" "$STAGED_LIST" "$UNTRACKED_LIST" | sort -u | head -10)

  cat <<EOF
{
  "decision": "block",
  "reason": "PROGRESS CHECK: You modified $TOTAL files but .claude/breadcrumbs.jsonl is missing or stale. Before ending your turn:\n1. Append a breadcrumb to .claude/breadcrumbs.jsonl: {\"ts\":\"...\",\"role\":\"builder\",\"type\":\"build\",\"feat\":null,\"msg\":\"what you did\"}\n2. Files changed:\n$ALL_FILES\n\nDo NOT skip this — progress tracking is required for multi-file changes."
}
EOF
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: passed ($TOTAL files, breadcrumbs fresh)" >> "$HOOK_LOG" 2>/dev/null
exit 0
