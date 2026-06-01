#!/bin/bash
# Validates that all hooks are properly configured, executable, and functional.
# Run from project root: .cursor/hooks/validate-hooks.sh

set -euo pipefail

GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
BOLD="\033[1m"
RESET="\033[0m"

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); printf "  ${GREEN}✓${RESET} %s\n" "$1"; }
fail() { FAIL=$((FAIL + 1)); printf "  ${RED}✗${RESET} %s\n" "$1"; }
warn() { WARN=$((WARN + 1)); printf "  ${YELLOW}!${RESET} %s\n" "$1"; }

echo -e "${BOLD}Hook Validation${RESET}"
echo ""

# --- 1. Check hooks.json exists and is valid JSON ---
echo -e "${BOLD}1. hooks.json${RESET}"
if [ ! -f ".cursor/hooks.json" ]; then
  fail "hooks.json not found"
else
  pass "hooks.json exists"
  if python3 -c "import json; json.load(open('.cursor/hooks.json'))" 2>/dev/null; then
    pass "hooks.json is valid JSON"
  else
    fail "hooks.json is invalid JSON"
  fi
fi

# --- 2. Check all referenced hook scripts exist and are executable ---
echo ""
echo -e "${BOLD}2. Hook scripts${RESET}"
HOOK_SCRIPTS=$(python3 -c "
import json
with open('.cursor/hooks.json') as f:
    data = json.load(f)
for event, hooks in data.get('hooks', {}).items():
    for h in hooks:
        if 'command' in h:
            print(f\"{event}|{h['command']}\")
" 2>/dev/null)

while IFS='|' read -r event script; do
  if [ ! -f "$script" ]; then
    fail "$script (${event}) — file not found"
  elif [ ! -x "$script" ]; then
    fail "$script (${event}) — not executable (chmod +x needed)"
  else
    pass "$script (${event})"
  fi
done <<< "$HOOK_SCRIPTS"

# --- 3. Functional tests ---
echo ""
echo -e "${BOLD}3. Functional tests${RESET}"

# Save and clean harness state for testing
SAVED_CONTRACT=""
SAVED_STATE=""
SAVED_BREADCRUMBS=""
[ -f .harness/contract.json ] && SAVED_CONTRACT=$(cat .harness/contract.json)
[ -f .harness/state.json ] && SAVED_STATE=$(cat .harness/state.json)
[ -f .harness/breadcrumbs.jsonl ] && SAVED_BREADCRUMBS=$(cat .harness/breadcrumbs.jsonl)

mkdir -p .harness

# Create temp files at project root to simulate multi-file changes
TMPF1=$(mktemp ./.test-hook-XXXX)
TMPF2=$(mktemp ./.test-hook-XXXX)

# --- enforce-progress tests ---

# Test: no breadcrumbs, 2+ untracked files → should fire
rm -f .harness/breadcrumbs.jsonl .harness/contract.json 2>/dev/null
OUTPUT=$(echo '{}' | .cursor/hooks/enforce-progress.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "PROGRESS CHECK|HARNESS CHECK"; then
  pass "enforce-progress fires when files changed + no breadcrumbs"
else
  fail "enforce-progress should fire but returned: $(echo "$OUTPUT" | head -1)"
fi

# Test: fresh breadcrumbs → pass (or tier 2 if 4+ files)
echo '{"ts":"test","role":"builder","type":"build","feat":null,"msg":"test"}' > .harness/breadcrumbs.jsonl
OUTPUT=$(echo '{}' | .cursor/hooks/enforce-progress.sh 2>/dev/null)
TOTAL_FILES=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
UNTRACKED_FILES=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')
SUM=$((TOTAL_FILES + STAGED_FILES + UNTRACKED_FILES))
if [ "$SUM" -ge 4 ]; then
  if echo "$OUTPUT" | rg -q "HARNESS CHECK"; then
    pass "enforce-progress fires tier 2 (harness check) with $SUM files + fresh breadcrumbs"
  elif echo "$OUTPUT" | rg -q '^\{\}$'; then
    pass "enforce-progress passes with fresh breadcrumbs"
  else
    fail "enforce-progress unexpected output with fresh breadcrumbs"
  fi
else
  if echo "$OUTPUT" | rg -q '^\{\}$'; then
    pass "enforce-progress passes with fresh breadcrumbs"
  else
    fail "enforce-progress should pass with fresh breadcrumbs"
  fi
fi

rm -f "$TMPF1" "$TMPF2"

# --- verify-harness tests ---

# Test: no contract → pass
rm -f .harness/contract.json 2>/dev/null
OUTPUT=$(echo '{}' | .cursor/hooks/verify-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "verify-harness passes when no contract exists"
else
  fail "verify-harness should pass without contract"
fi

# Test: unverified contract → fire
echo '{"feature":"test","verified":false,"phase":"evaluating"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/verify-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "HARNESS GATE"; then
  pass "verify-harness fires when contract is unverified"
else
  fail "verify-harness should fire for unverified contract"
fi

# Test: verified contract → pass
echo '{"feature":"test","verified":true,"phase":"evaluating"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/verify-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "verify-harness passes when contract is verified"
else
  fail "verify-harness should pass for verified contract"
fi

# --- chain-evaluator (subagentStop) tests ---

# Test: planner just finished (state.json, no contract) → PLAN GATE
rm -f .harness/contract.json 2>/dev/null
echo '{"tasks":[{"id":"feat-1"},{"id":"feat-2"}]}' > .harness/state.json
touch .harness/state.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "PLAN GATE"; then
  pass "chain-evaluator fires PLAN GATE after planner finishes"
else
  fail "chain-evaluator should fire PLAN GATE when state.json exists without contract"
fi

# Test: phase=negotiating → CONTRACT NEGOTIATED (builder should build)
echo '{"feature":"test","verified":false,"phase":"negotiating"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "CONTRACT NEGOTIATED"; then
  pass "chain-evaluator routes negotiating → build instruction"
else
  fail "chain-evaluator should route negotiating phase to build: $(echo "$OUTPUT" | head -1)"
fi

# Test: phase=negotiated → CONTRACT NEGOTIATED (builder should build)
echo '{"feature":"test","verified":false,"phase":"negotiated"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "CONTRACT NEGOTIATED"; then
  pass "chain-evaluator routes negotiated → build instruction"
else
  fail "chain-evaluator should route negotiated phase to build: $(echo "$OUTPUT" | head -1)"
fi

# Test: phase=building → BUILD COMPLETE (launch evaluator)
echo '{"feature":"test","verified":false,"phase":"building"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "BUILD COMPLETE"; then
  pass "chain-evaluator routes building → evaluator launch"
else
  fail "chain-evaluator should route building phase to evaluator: $(echo "$OUTPUT" | head -1)"
fi

# Test: phase=evaluating + unverified → EVAL INCOMPLETE (re-launch)
echo '{"feature":"test","verified":false,"phase":"evaluating"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "EVAL INCOMPLETE"; then
  pass "chain-evaluator routes evaluating+unverified → re-launch"
else
  fail "chain-evaluator should fire EVAL INCOMPLETE for unverified evaluating: $(echo "$OUTPUT" | head -1)"
fi

# Test: phase=evaluating + verified → pass
echo '{"feature":"test","verified":true,"phase":"evaluating"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "chain-evaluator passes when evaluating + verified"
else
  fail "chain-evaluator should pass for verified evaluating: $(echo "$OUTPUT" | head -1)"
fi

# --- harness-gate (beforeSubmitPrompt) tests ---

# Test: harness active (state.json exists) → allow silently
rm -f .harness/contract.json 2>/dev/null
echo '{"tasks":[]}' > .harness/state.json
OUTPUT=$(echo '{"prompt":"implement a new authentication system with OAuth2"}' | .cursor/hooks/harness-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "harness-gate allows silently when harness is active"
else
  fail "harness-gate should allow when state.json exists: $(echo "$OUTPUT" | head -1)"
fi

# Test: glue message → allow silently
rm -f .harness/state.json .harness/contract.json 2>/dev/null
OUTPUT=$(echo '{"prompt":"ok next"}' | .cursor/hooks/harness-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "harness-gate allows glue messages"
else
  fail "harness-gate should allow short glue messages: $(echo "$OUTPUT" | head -1)"
fi

# Test: non-trivial prompt without harness → allow + inject routing
rm -f .harness/state.json .harness/contract.json 2>/dev/null
OUTPUT=$(echo '{"prompt":"implement a new authentication service with OAuth2 integration and database schema"}' | .cursor/hooks/harness-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "agent_message.*planner|HARNESS ROUTING"; then
  pass "harness-gate injects planner routing for non-trivial prompt (does NOT block)"
else
  fail "harness-gate should inject routing instructions for non-trivial prompt: $(echo "$OUTPUT" | head -1)"
fi

# Test: "skip harness" opt-out → allow silently
rm -f .harness/state.json .harness/contract.json 2>/dev/null
OUTPUT=$(echo '{"prompt":"implement a new authentication service skip harness"}' | .cursor/hooks/harness-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "harness-gate allows when user says skip harness"
else
  fail "harness-gate should allow skip harness opt-out: $(echo "$OUTPUT" | head -1)"
fi

# --- pre-commit-harness (beforeShellExecution) tests ---

# Test: non-git-commit command → allow silently
OUTPUT=$(echo '{"command":"git status"}' | .cursor/hooks/pre-commit-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '"permission".*"allow"'; then
  pass "pre-commit allows non-commit git commands"
else
  fail "pre-commit should allow non-commit commands: $(echo "$OUTPUT" | head -1)"
fi

# Test: git commit without harness → allow + auto-breadcrumb
rm -f .harness/contract.json .harness/state.json 2>/dev/null
BREADCRUMB_BEFORE=""
[ -f .harness/breadcrumbs.jsonl ] && BREADCRUMB_BEFORE=$(wc -l < .harness/breadcrumbs.jsonl | tr -d ' ')
OUTPUT=$(echo '{"command":"git commit -m \"test commit\""}' | .cursor/hooks/pre-commit-harness.sh 2>/dev/null)
BREADCRUMB_AFTER=$(wc -l < .harness/breadcrumbs.jsonl 2>/dev/null | tr -d ' ')
if echo "$OUTPUT" | rg -q '"permission".*"allow"'; then
  pass "pre-commit allows git commit"
else
  fail "pre-commit should allow git commit: $(echo "$OUTPUT" | head -1)"
fi
if [ "${BREADCRUMB_AFTER:-0}" -gt "${BREADCRUMB_BEFORE:-0}" ]; then
  pass "pre-commit auto-records breadcrumb on commit"
else
  fail "pre-commit should auto-append breadcrumb"
fi

# Test: git commit with active harness (unverified contract) → allow + warning
mkdir -p .harness 2>/dev/null
echo '{"feature":"auth","verified":false,"phase":"building"}' > .harness/contract.json
OUTPUT=$(echo '{"command":"git commit -m \"wip\""}' | .cursor/hooks/pre-commit-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "agent_message.*unverified|WARNING"; then
  pass "pre-commit warns when committing with unverified contract"
else
  fail "pre-commit should warn about unverified contract: $(echo "$OUTPUT" | head -1)"
fi

# Test: git commit with verified contract → allow + next-feature guidance
echo '{"feature":"auth","task_id":"feat-1","verified":true,"phase":"evaluating"}' > .harness/contract.json
echo '{"tasks":[{"id":"feat-1","status":"verified"}]}' > .harness/state.json
OUTPUT=$(echo '{"command":"git commit -m \"feat: auth done\""}' | .cursor/hooks/pre-commit-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "agent_message.*committed|next"; then
  pass "pre-commit guides to next task after verified commit"
else
  fail "pre-commit should guide to next task: $(echo "$OUTPUT" | head -1)"
fi

rm -f .harness/contract.json .harness/state.json 2>/dev/null

# --- context-health (stop) tests ---

# Test: few breadcrumbs → healthy, pass through
rm -f .harness/breadcrumbs.jsonl 2>/dev/null
echo '{"ts":"2026-05-24T10:00","role":"builder","type":"build","feat":null,"msg":"step 1"}' > .harness/breadcrumbs.jsonl
echo '{"ts":"2026-05-24T10:01","role":"builder","type":"build","feat":null,"msg":"step 2"}' >> .harness/breadcrumbs.jsonl
OUTPUT=$(echo '{}' | .cursor/hooks/context-health.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "context-health passes with few breadcrumbs (healthy)"
else
  fail "context-health should pass with only 2 breadcrumbs: $(echo "$OUTPUT" | head -1)"
fi

# Test: many breadcrumbs (>25) → fatigue signal
rm -f .harness/breadcrumbs.jsonl 2>/dev/null
for i in $(seq 1 30); do
  echo "{\"ts\":\"2026-05-24T10:$(printf '%02d' $i)\",\"role\":\"builder\",\"type\":\"build\",\"feat\":null,\"msg\":\"step $i\"}" >> .harness/breadcrumbs.jsonl
done
OUTPUT=$(echo '{}' | .cursor/hooks/context-health.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "CONTEXT HEALTH|breadcrumb"; then
  pass "context-health detects breadcrumb volume fatigue (>25 entries)"
else
  fail "context-health should detect volume fatigue: $(echo "$OUTPUT" | head -1)"
fi

# Test: consecutive failures → fatigue signal
rm -f .harness/breadcrumbs.jsonl 2>/dev/null
for i in $(seq 1 3); do
  echo "{\"ts\":\"2026-05-24T10:0$i\",\"role\":\"builder\",\"type\":\"build\",\"feat\":\"feat-1\",\"msg\":\"attempt $i\"}" >> .harness/breadcrumbs.jsonl
done
for i in $(seq 4 8); do
  echo "{\"ts\":\"2026-05-24T10:0$i\",\"role\":\"evaluator\",\"type\":\"eval\",\"feat\":\"feat-1\",\"msg\":\"eval $i\",\"result\":\"fail\"}" >> .harness/breadcrumbs.jsonl
done
OUTPUT=$(echo '{}' | .cursor/hooks/context-health.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "CONTEXT HEALTH|consecutive|circles"; then
  pass "context-health detects consecutive failure fatigue"
else
  fail "context-health should detect consecutive failures: $(echo "$OUTPUT" | head -1)"
fi

# Test: scrap-and-restart exhaustion → fatigue signal
rm -f .harness/breadcrumbs.jsonl 2>/dev/null
for i in $(seq 1 6); do
  echo "{\"ts\":\"2026-05-24T10:0$i\",\"role\":\"builder\",\"type\":\"build\",\"feat\":\"feat-1\",\"msg\":\"build $i\"}" >> .harness/breadcrumbs.jsonl
done
echo '{"ts":"2026-05-24T10:07","role":"evaluator","type":"scrap","feat":"feat-1","msg":"scrap 1"}' >> .harness/breadcrumbs.jsonl
echo '{"ts":"2026-05-24T10:08","role":"evaluator","type":"scrap","feat":"feat-1","msg":"scrap 2"}' >> .harness/breadcrumbs.jsonl
OUTPUT=$(echo '{}' | .cursor/hooks/context-health.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "CONTEXT HEALTH|scrap|exhaustion"; then
  pass "context-health detects scrap-and-restart exhaustion"
else
  fail "context-health should detect scrap exhaustion: $(echo "$OUTPUT" | head -1)"
fi

rm -f .harness/breadcrumbs.jsonl 2>/dev/null

# --- harness-context (sessionStart) tests ---

# Test: no harness state → pass
rm -f .harness/state.json .harness/contract.json 2>/dev/null
OUTPUT=$(echo '{}' | .cursor/hooks/harness-context.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "harness-context passes when no harness state"
else
  fail "harness-context should pass without state: $(echo "$OUTPUT" | head -1)"
fi

# Test: state.json exists → inject context
echo '{"project":"test-proj","tasks":[{"id":"feat-1","name":"Auth","status":"building","type":"feature"},{"id":"feat-2","name":"UI","status":"pending","type":"feature"}]}' > .harness/state.json
echo '{"feature":"Auth","phase":"building","verified":false}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/harness-context.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "additional_context"; then
  pass "harness-context injects context when harness is active"
else
  fail "harness-context should inject context: $(echo "$OUTPUT" | head -1)"
fi

# --- Cleanup ---
rm -f .harness/contract.json .harness/state.json 2>/dev/null
rm -f .harness/breadcrumbs.jsonl 2>/dev/null

# Restore original state
if [ -n "$SAVED_CONTRACT" ]; then echo "$SAVED_CONTRACT" > .harness/contract.json; fi
if [ -n "$SAVED_STATE" ]; then echo "$SAVED_STATE" > .harness/state.json; fi
if [ -n "$SAVED_BREADCRUMBS" ]; then echo "$SAVED_BREADCRUMBS" > .harness/breadcrumbs.jsonl; fi

rmdir .harness 2>/dev/null || true

# --- 4. Check hooks.log for recent activity ---
echo ""
echo -e "${BOLD}4. Recent hook activity${RESET}"
if [ -f ".cursor/hooks.log" ]; then
  LINES=$(wc -l < .cursor/hooks.log | tr -d ' ')
  LAST=$(tail -1 .cursor/hooks.log)
  pass "hooks.log exists ($LINES entries)"
  printf "  ${YELLOW}Last: %s${RESET}\n" "$LAST"
else
  warn "hooks.log not found — hooks haven't run yet in this project"
fi

# --- Summary ---
echo ""
echo -e "${BOLD}Summary:${RESET} ${GREEN}$PASS passed${RESET}, ${RED}$FAIL failed${RESET}, ${YELLOW}$WARN warnings${RESET}"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
