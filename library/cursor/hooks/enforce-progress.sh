#!/bin/bash
# Stop hook: two-tier enforcement for progress tracking and harness usage.
# Tier 1: 2+ files changed without fresh breadcrumbs → ask for breadcrumbs
# Tier 2: 4+ files changed without a contract → ask why harness isn't being used
# Skips when adversarial harness is active (it has its own enforcement).

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "enforce-progress"

CONTRACT=".harness/contract.json"
if [ -f "$CONTRACT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: contract exists, skipping" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

TOTAL=$(hooks_git_total_count)

if [ "$TOTAL" -lt 2 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: $TOTAL files changed, below threshold" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

BREADCRUMBS=".harness/breadcrumbs.jsonl"
BREADCRUMBS_FRESH=false

if [ -f "$BREADCRUMBS" ]; then
  AGE=$(hooks_file_age "$BREADCRUMBS")

  if [ "$AGE" -lt 180 ]; then
    BREADCRUMBS_FRESH=true
  fi
fi

# Tier 2: 4+ files without a contract → harness enforcement
# Skip in lean profile (meta-work repos don't need harness nag)
PROFILE=$(cat .cursor/.hooks-profile 2>/dev/null || echo "lean")
if [ "$PROFILE" = "lean" ]; then
  if [ "$BREADCRUMBS_FRESH" = false ] && [ "$TOTAL" -ge 2 ]; then
    : # fall through to Tier 1
  else
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: lean profile, skipping tier 2" >> "$HOOK_LOG" 2>/dev/null
    echo '{}'
    exit 0
  fi
fi

if [ "$TOTAL" -ge 4 ] && [ "$BREADCRUMBS_FRESH" = true ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: $TOTAL files, breadcrumbs fresh, but no contract — harness warning" >> "$HOOK_LOG" 2>/dev/null

  CHANGED_LIST=$(git diff --name-only 2>/dev/null | head -10)
  STAGED_LIST=$(git diff --cached --name-only 2>/dev/null | head -10)
  UNTRACKED_LIST=$(git ls-files --others --exclude-standard 2>/dev/null | head -10)
  ALL_FILES=$(printf "%s\n%s\n%s" "$CHANGED_LIST" "$STAGED_LIST" "$UNTRACKED_LIST" | sort -u | head -10)

  cat <<EOF
{
  "followup_message": "HARNESS CHECK: You modified $TOTAL files without an active harness contract. For non-trivial work (3+ files, user-facing behavior, architectural changes), the adversarial harness should be used: /planner → contract negotiation → /evaluator.\n\nIf this IS simple work, add a breadcrumb explaining why harness was skipped:\n{\"ts\":\"...\",\"role\":\"builder\",\"type\":\"decision\",\"feat\":null,\"msg\":\"Skipped harness: <reason>\"}\n\nFiles changed:\n$ALL_FILES"
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
  "followup_message": "PROGRESS CHECK: You modified $TOTAL files but .harness/breadcrumbs.jsonl is missing or stale. Before ending your turn:\n1. Append a breadcrumb to .harness/breadcrumbs.jsonl: {\"ts\":\"...\",\"role\":\"builder\",\"type\":\"build\",\"feat\":null,\"msg\":\"what you did\"}\n2. If you haven't used TodoWrite for this task, create a todo list now\n3. Files changed:\n$ALL_FILES\n\nDo NOT skip this — progress tracking is required for multi-file changes."
}
EOF
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: passed ($TOTAL files, breadcrumbs fresh)" >> "$HOOK_LOG" 2>/dev/null
echo '{}'
exit 0
