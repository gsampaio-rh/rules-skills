#!/bin/bash
# Stop hook: enforces adversarial verification when a harness is active.
#
# Two enforcement paths:
#   1. Contract exists + verified != true → force evaluator launch
#   2. State.json has building feature + impl files changed + no contract/eval → force workflow
#
# No state.json and no contract = simple task = pass through silently.

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: triggered" >> "$HOOK_LOG" 2>/dev/null

CONTRACT=".harness/contract.json"
STATE=".harness/state.json"
BREADCRUMBS=".harness/breadcrumbs.jsonl"
EVALS_DIR=".harness/evals"

# ─── Path 1: Contract exists but unverified ───────────────────────────────────

if [ -f "$CONTRACT" ]; then
  if [ ! -f "$BREADCRUMBS" ]; then
    cat <<EOF
{
  "followup_message": "HARNESS WARNING: A contract exists but no breadcrumbs.jsonl was found. Create .harness/breadcrumbs.jsonl before continuing — the trace log is required for the adversarial harness workflow."
}
EOF
    exit 0
  fi

  VERIFIED=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    print(str(data.get('verified', False)))
except Exception:
    print('False')
" 2>/dev/null)

  if [ "$VERIFIED" = "True" ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: contract verified, passing" >> "$HOOK_LOG" 2>/dev/null
    echo '{}'
    exit 0
  fi

  FEATURE=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    print(data.get('feature', 'unknown feature'))
except Exception:
    print('unknown feature')
" 2>/dev/null)

  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: BLOCKED — contract unverified for '$FEATURE'" >> "$HOOK_LOG" 2>/dev/null

  cat <<EOF
{
  "followup_message": "HARNESS GATE: A contract exists for \"$FEATURE\" but verification is incomplete. You must:\n1. Create the evaluator flag: touch .cursor/hooks/.evaluator-active\n2. Launch an evaluator subagent (Task tool) to test the implementation against .harness/contract.json\n3. After the evaluator passes, set verified to true in the contract\n\nDo not skip this step — the harness requires adversarial verification before completion."
}
EOF
  exit 0
fi

# ─── Path 2: State.json exists but no contract — check if work was done ───────

if [ ! -f "$STATE" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: no harness state, skipping" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Check if state.json has a feature in "building" status
BUILDING_FEATURE=$(python3 -c "
import json
try:
    with open('$STATE') as f:
        data = json.load(f)
    for feat in data.get('features', []):
        if feat.get('status') == 'building':
            print(feat.get('name', feat.get('id', 'unknown')))
            break
    else:
        print('')
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$BUILDING_FEATURE" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: no building feature, passing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Check if a recent "Skipped harness" breadcrumb exists (within last 5 min)
BREADCRUMBS=".harness/breadcrumbs.jsonl"
if [ -f "$BREADCRUMBS" ]; then
  SKIP_FOUND=$(tail -5 "$BREADCRUMBS" | grep -c "Skipped harness" || echo "0")
  if [ "$SKIP_FOUND" -gt 0 ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: skip breadcrumb found, passing" >> "$HOOK_LOG" 2>/dev/null
    echo '{}'
    exit 0
  fi
fi

# A feature is marked as building — check if implementation files were modified
IMPL_CHANGES=$(git diff --name-only 2>/dev/null | grep -vE '\.cursor/|breadcrumbs|\.md$|\.json$|\.yaml$' | wc -l | tr -d ' ')
IMPL_STAGED=$(git diff --cached --name-only 2>/dev/null | grep -vE '\.cursor/|breadcrumbs|\.md$|\.json$|\.yaml$' | wc -l | tr -d ' ')
IMPL_UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null | grep -vE '\.cursor/|breadcrumbs|\.md$|\.json$|\.yaml$' | wc -l | tr -d ' ')
TOTAL_IMPL=$((${IMPL_CHANGES:-0} + ${IMPL_STAGED:-0} + ${IMPL_UNTRACKED:-0}))

if [ "$TOTAL_IMPL" -lt 1 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: building feature but no impl changes, passing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Implementation files changed while a feature is building — enforce workflow
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: BLOCKED — $TOTAL_IMPL impl files changed, feature '$BUILDING_FEATURE' building, no contract" >> "$HOOK_LOG" 2>/dev/null

cat <<EOF
{
  "followup_message": "HARNESS ENFORCEMENT: Feature \"$BUILDING_FEATURE\" is in 'building' status and $TOTAL_IMPL implementation file(s) were modified, but no contract exists. The adversarial harness requires:\n\n1. Propose a contract for this feature (write .harness/contract.json with acceptance_criteria, edge_cases, verification_method)\n2. Launch the evaluator subagent for contract negotiation\n3. After negotiation, implement against the agreed contract\n4. Launch the evaluator again for verification\n\nIf you've already completed the work and need to skip the harness, write a breadcrumb explaining why: {\"ts\":\"...\",\"role\":\"builder\",\"type\":\"decision\",\"msg\":\"Skipped harness: <reason>\"}"
}
EOF
exit 0
