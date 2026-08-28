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

# --- Prerequisite check ---
if [ ! -d ".cursor/hooks" ]; then
  echo -e "${RED}Prerequisites missing:${RESET}"
  echo "  - .cursor/hooks/ directory not found"
  echo "  Run 'make setup' or 'make sync-local' to populate .cursor/ from library/cursor/."
  echo ""
  echo -e "${BOLD}Summary:${RESET} ${RED}Cannot run — missing prerequisites${RESET}"
  exit 1
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

# Preserve live harness contract so dogfood sessions aren't corrupted
_VH_CONTRACT_BAK=""
if [ -f .harness/contract.json ]; then
  _VH_CONTRACT_BAK=$(mktemp)
  cp .harness/contract.json "$_VH_CONTRACT_BAK"
fi
_VH_BC_BAK=""
if [ -f .harness/breadcrumbs.jsonl ]; then
  _VH_BC_BAK=$(mktemp)
  cp .harness/breadcrumbs.jsonl "$_VH_BC_BAK"
fi
_VH_STATS_BAK=""
if [ -f .harness/.session-stats.json ]; then
  _VH_STATS_BAK=$(mktemp)
  cp .harness/.session-stats.json "$_VH_STATS_BAK"
fi

# Test: source_writes=2, no breadcrumbs → PROGRESS BLOCKED
rm -f .harness/breadcrumbs.jsonl .harness/contract.json 2>/dev/null
mkdir -p .harness
echo '{"turns":0,"source_writes":2}' > .harness/.session-stats.json
OUTPUT=$(echo '{}' | .cursor/hooks/enforce-progress.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "PROGRESS BLOCKED"; then
  pass "enforce-progress blocks when source_writes=2 + no breadcrumbs"
else
  fail "enforce-progress should PROGRESS BLOCKED but returned: $(echo "$OUTPUT" | head -1)"
fi

# Test: quality breadcrumb (msg>=20 + result) → pass
echo '{"ts":"test","role":"builder","type":"build","feat":null,"msg":"validate-hooks quality breadcrumb ok","result":"pass"}' > .harness/breadcrumbs.jsonl
OUTPUT=$(echo '{}' | .cursor/hooks/enforce-progress.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "enforce-progress passes with quality breadcrumbs"
elif echo "$OUTPUT" | rg -q "HARNESS CHECK"; then
  pass "enforce-progress fires tier 2 (harness check) with quality breadcrumbs"
else
  fail "enforce-progress unexpected output with quality breadcrumbs: $(echo "$OUTPUT" | head -1)"
fi

# Restore harness artifacts; always remove fixture session-stats unless we had one
rm -f .harness/.session-stats.json 2>/dev/null
if [ -n "$_VH_STATS_BAK" ] && [ -f "$_VH_STATS_BAK" ]; then
  mv "$_VH_STATS_BAK" .harness/.session-stats.json
fi
if [ -n "$_VH_CONTRACT_BAK" ] && [ -f "$_VH_CONTRACT_BAK" ]; then
  mv "$_VH_CONTRACT_BAK" .harness/contract.json
fi
if [ -n "$_VH_BC_BAK" ] && [ -f "$_VH_BC_BAK" ]; then
  mv "$_VH_BC_BAK" .harness/breadcrumbs.jsonl
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

# Test: verified contract + evaluator PASS breadcrumb → pass
echo '{"feature":"test","verified":true,"phase":"evaluating"}' > .harness/contract.json
echo '{"ts":"2026-01-01T00:00:00Z","role":"evaluator","type":"evaluate","feat":"","msg":"PASS","result":"pass"}' > .harness/breadcrumbs.jsonl
OUTPUT=$(echo '{}' | .cursor/hooks/verify-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "verify-harness passes when contract is verified"
else
  fail "verify-harness should pass for verified contract"
fi

# --- chain-evaluator (subagentStop) tests ---

# Test: planner finished (state.json, no contract) → {} (plan gate prose removed)
rm -f .harness/contract.json 2>/dev/null
echo '{"tasks":[{"id":"feat-1"},{"id":"feat-2"}]}' > .harness/state.json
touch .harness/state.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "chain-evaluator passes when state exists without contract (no plan-gate prose)"
else
  fail "chain-evaluator should return {} without contract: $(echo "$OUTPUT" | head -1)"
fi

# Test: phase=negotiating → {} (build guidance is skill-owned)
echo '{"feature":"test","verified":false,"phase":"negotiating"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "chain-evaluator passes through negotiating phase"
else
  fail "chain-evaluator should return {} for negotiating: $(echo "$OUTPUT" | head -1)"
fi

# Test: phase=negotiated → {}
echo '{"feature":"test","verified":false,"phase":"negotiated"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "chain-evaluator passes through negotiated phase"
else
  fail "chain-evaluator should return {} for negotiated: $(echo "$OUTPUT" | head -1)"
fi

# Test: phase=building → BUILD COMPLETE (launch evaluator)
echo '{"feature":"test","verified":false,"phase":"building"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "BUILD COMPLETE"; then
  pass "chain-evaluator routes building → evaluator launch"
else
  fail "chain-evaluator should route building phase to evaluator: $(echo "$OUTPUT" | head -1)"
fi

# Test: phase=evaluating + unverified → {} (retry prose removed)
echo '{"feature":"test","verified":false,"phase":"evaluating"}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/chain-evaluator.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "chain-evaluator passes evaluating+unverified without EVAL FAIL prose"
else
  fail "chain-evaluator should return {} for evaluating+unverified: $(echo "$OUTPUT" | head -1)"
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

# Test: non-trivial prompt without harness → free default (NO routing-pending)
rm -f .harness/state.json .harness/contract.json .harness/.routing-pending 2>/dev/null
OUTPUT=$(echo '{"prompt":"implement a new authentication service with OAuth2 integration, database schema migrations, role-based access control, and session management across multiple microservices"}' | .cursor/hooks/harness-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$' && [ ! -f .harness/.routing-pending ]; then
  pass "harness-gate free default: long prompt does NOT arm routing-pending"
else
  fail "harness-gate should stay silent without opt-in: $(echo "$OUTPUT" | head -1)"
fi

# Test: explicit opt-in → set .routing-pending + followup
rm -f .harness/state.json .harness/contract.json .harness/.routing-pending 2>/dev/null
OUTPUT=$(echo '{"prompt":"use harness to implement OAuth2 auth"}' | .cursor/hooks/harness-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "HARNESS OPT-IN|followup_message" && [ -f .harness/.routing-pending ]; then
  pass "harness-gate arms on use harness opt-in"
else
  fail "harness-gate should arm on opt-in: $(echo "$OUTPUT" | head -1)"
fi
rm -f .harness/.routing-pending 2>/dev/null

# Test: "skip harness" opt-out → allow silently
rm -f .harness/state.json .harness/contract.json 2>/dev/null
OUTPUT=$(echo '{"prompt":"implement a new authentication service skip harness"}' | .cursor/hooks/harness-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "harness-gate allows when user says skip harness"
else
  fail "harness-gate should allow skip harness opt-out: $(echo "$OUTPUT" | head -1)"
fi

# --- pre-commit-harness (beforeShellExecution) tests ---

COMMIT_GATE=".cursor/hooks/.commit-approved"

# Test: non-git-commit command → allow silently (no flag needed)
OUTPUT=$(echo '{"command":"git status"}' | .cursor/hooks/pre-commit-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '"permission".*"allow"'; then
  pass "pre-commit allows non-commit git commands"
else
  fail "pre-commit should allow non-commit commands: $(echo "$OUTPUT" | head -1)"
fi

# Test: git commit without harness → allow + auto-breadcrumb
# Requires .commit-approved flag (commit gate workflow from feat-17)
rm -f .harness/contract.json .harness/state.json "$COMMIT_GATE" 2>/dev/null
BREADCRUMB_BEFORE=""
[ -f .harness/breadcrumbs.jsonl ] && BREADCRUMB_BEFORE=$(wc -l < .harness/breadcrumbs.jsonl | tr -d ' ')
mkdir -p "$(dirname "$COMMIT_GATE")" 2>/dev/null
echo "approved" > "$COMMIT_GATE"
OUTPUT=$(echo '{"command":"git commit -m \"test commit\""}' | .cursor/hooks/pre-commit-harness.sh 2>/dev/null)
rm -f "$COMMIT_GATE" 2>/dev/null
BREADCRUMB_AFTER=$(wc -l < .harness/breadcrumbs.jsonl 2>/dev/null | tr -d ' ')
if echo "$OUTPUT" | rg -q '"permission".*"allow"'; then
  pass "pre-commit allows git commit (with .commit-approved flag)"
else
  fail "pre-commit should allow git commit with flag: $(echo "$OUTPUT" | head -1)"
fi
if [ "${BREADCRUMB_AFTER:-0}" -gt "${BREADCRUMB_BEFORE:-0}" ]; then
  pass "pre-commit auto-records breadcrumb on commit"
else
  fail "pre-commit should auto-append breadcrumb"
fi

# Test: git commit WITHOUT .commit-approved → deny (commit gate enforcement)
rm -f "$COMMIT_GATE" 2>/dev/null
OUTPUT=$(echo '{"command":"git commit -m \"sneaky commit\""}' | .cursor/hooks/pre-commit-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '"permission".*"deny"'; then
  pass "pre-commit denies git commit without .commit-approved flag"
else
  fail "pre-commit should deny without flag: $(echo "$OUTPUT" | head -1)"
fi

# Test: git commit with active harness (unverified contract) → allow + warning
mkdir -p .harness "$(dirname "$COMMIT_GATE")" 2>/dev/null
rm -f "$COMMIT_GATE" 2>/dev/null
echo '{"feature":"auth","verified":false,"phase":"building"}' > .harness/contract.json
echo "approved" > "$COMMIT_GATE"
OUTPUT=$(echo '{"command":"git commit -m \"wip\""}' | .cursor/hooks/pre-commit-harness.sh 2>/dev/null)
rm -f "$COMMIT_GATE" 2>/dev/null
if echo "$OUTPUT" | rg -q '"permission".*"allow"' && echo "$OUTPUT" | rg -q "unverified|WARNING"; then
  pass "pre-commit warns when committing with unverified contract"
else
  fail "pre-commit should allow+warn about unverified contract: $(echo "$OUTPUT" | head -1)"
fi

# Test: git commit with verified contract → allow + next-feature guidance
rm -f "$COMMIT_GATE" 2>/dev/null
echo '{"feature":"auth","task_id":"feat-1","verified":true,"phase":"evaluating"}' > .harness/contract.json
echo '{"tasks":[{"id":"feat-1","status":"verified"}]}' > .harness/state.json
echo "approved" > "$COMMIT_GATE"
OUTPUT=$(echo '{"command":"git commit -m \"feat: auth done\""}' | .cursor/hooks/pre-commit-harness.sh 2>/dev/null)
rm -f "$COMMIT_GATE" 2>/dev/null
if echo "$OUTPUT" | rg -q '"permission".*"allow"' && echo "$OUTPUT" | rg -q 'committed|next'; then
  pass "pre-commit guides to next task after verified commit"
else
  fail "pre-commit should guide to next task: $(echo "$OUTPUT" | head -1)"
fi

rm -f .harness/contract.json .harness/state.json "$COMMIT_GATE" 2>/dev/null

# --- contract-gate (preToolUse) tests ---

# Test: no state, no routing-pending → allow
rm -f .harness/state.json .harness/contract.json .harness/.routing-pending 2>/dev/null
OUTPUT=$(echo '{"input":{"path":"/src/app.py"}}' | .cursor/hooks/contract-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "contract-gate allows when no harness active"
else
  fail "contract-gate should allow when no harness: $(echo "$OUTPUT" | head -1)"
fi

# Test: cold-start deny (routing-pending, no state)
mkdir -p .harness
echo "2026-01-01" > .harness/.routing-pending
OUTPUT=$(echo '{"input":{"path":"/src/app.py"}}' | .cursor/hooks/contract-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "permission.*deny"; then
  pass "contract-gate denies cold-start write"
else
  fail "contract-gate should deny cold-start write: $(echo "$OUTPUT" | head -1)"
fi

# Test: cold-start allows .harness/ writes
OUTPUT=$(echo '{"input":{"path":".harness/state.json"}}' | .cursor/hooks/contract-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "contract-gate allows .harness/ path in cold-start"
else
  fail "contract-gate should allow .harness/ in cold-start: $(echo "$OUTPUT" | head -1)"
fi
rm -f .harness/.routing-pending

# Test: state exists + contract exists → allow
echo '{"tasks":[{"id":"feat-1","name":"Auth","status":"building","type":"feature"}]}' > .harness/state.json
echo '{"feature":"Auth","phase":"building","verified":false}' > .harness/contract.json
OUTPUT=$(echo '{"input":{"path":"/src/app.py"}}' | .cursor/hooks/contract-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "contract-gate allows with contract present"
else
  fail "contract-gate should allow with contract: $(echo "$OUTPUT" | head -1)"
fi

# Test: state exists + no contract + gatable task → deny
rm -f .harness/contract.json
OUTPUT=$(echo '{"input":{"path":"/src/app.py"}}' | .cursor/hooks/contract-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "permission.*deny"; then
  pass "contract-gate denies impl write without contract (building feature)"
else
  fail "contract-gate should deny without contract: $(echo "$OUTPUT" | head -1)"
fi

# Test: spike/chore bypass — only non-gatable task pending
echo '{"tasks":[{"id":"chore-99","name":"Cleanup","status":"pending","type":"chore"}]}' > .harness/state.json
rm -f .harness/contract.json
OUTPUT=$(echo '{"input":{"path":"/src/app.py"}}' | .cursor/hooks/contract-gate.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "contract-gate bypasses for spike/chore task"
else
  fail "contract-gate should bypass for chore: $(echo "$OUTPUT" | head -1)"
fi

rm -f .harness/state.json .harness/contract.json 2>/dev/null

# --- harness-context (sessionStart) tests ---

# Test: no harness state → inject free-default / opt-in note
rm -f .harness/state.json .harness/contract.json 2>/dev/null
OUTPUT=$(echo '{}' | .cursor/hooks/harness-context.sh 2>/dev/null)
if echo "$OUTPUT" | rg -qi "No harness active|Work freely|opt in|use harness"; then
  pass "harness-context injects free-default note when no state"
else
  fail "harness-context should inject free-default note: $(echo "$OUTPUT" | head -1)"
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

# Test: BUG-1 — contract exists but no state.json → non-empty additional_context (not {})
rm -f .harness/state.json 2>/dev/null
echo '{"feature":"Auth","phase":"building","verified":false}' > .harness/contract.json
OUTPUT=$(echo '{}' | .cursor/hooks/harness-context.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "additional_context"; then
  pass "harness-context handles contract-without-state (BUG-1 fix)"
else
  fail "harness-context should inject context when contract exists without state (BUG-1)"
fi

# --- evaluator-guard (preToolUse) tests ---

# Test: evaluator not active → allow
rm -f .cursor/hooks/.evaluator-active 2>/dev/null
OUTPUT=$(echo '{"input":{"path":"/src/app.py"}}' | .cursor/hooks/evaluator-guard.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "evaluator-guard allows when not active"
else
  fail "evaluator-guard should allow when not active: $(echo "$OUTPUT" | head -1)"
fi

# Test: evaluator active + harness write → allow
touch .cursor/hooks/.evaluator-active
OUTPUT=$(echo '{"input":{"path":".harness/.archive/evals/eval-feat-1.json"}}' | .cursor/hooks/evaluator-guard.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "evaluator-guard allows .harness/ write"
else
  fail "evaluator-guard should allow .harness/ write: $(echo "$OUTPUT" | head -1)"
fi

# Test: evaluator active + impl write → deny
OUTPUT=$(echo '{"input":{"path":"/src/app.py"}}' | .cursor/hooks/evaluator-guard.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "permission.*deny"; then
  pass "evaluator-guard denies impl write when active"
else
  fail "evaluator-guard should deny impl write: $(echo "$OUTPUT" | head -1)"
fi

# Test: BUG-6 fix — toolInput.filePath extraction
OUTPUT=$(echo '{"toolInput":{"filePath":"/src/app.py"}}' | .cursor/hooks/evaluator-guard.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "permission.*deny"; then
  pass "evaluator-guard denies toolInput.filePath write (BUG-6 fix)"
else
  fail "evaluator-guard should deny toolInput.filePath (BUG-6): $(echo "$OUTPUT" | head -1)"
fi

# Test: stale flag removal (>30 min)
touch -t 202501010000 .cursor/hooks/.evaluator-active 2>/dev/null
OUTPUT=$(echo '{"input":{"path":"/src/app.py"}}' | .cursor/hooks/evaluator-guard.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "evaluator-guard removes stale flag"
else
  fail "evaluator-guard should remove stale flag: $(echo "$OUTPUT" | head -1)"
fi
rm -f .cursor/hooks/.evaluator-active 2>/dev/null

# --- dedup-server (beforeShellExecution) tests ---

# Test: non-server command → allow
OUTPUT=$(echo '{"command":"git status"}' | .cursor/hooks/dedup-server.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q "permission.*allow"; then
  pass "dedup-server allows non-server command"
else
  fail "dedup-server should allow non-server command: $(echo "$OUTPUT" | head -1)"
fi

# --- BUG-7 fixture: malformed contract → {} ---

echo '{not valid json' > .harness/contract.json
mkdir -p .harness
touch .harness/breadcrumbs.jsonl
OUTPUT=$(echo '{}' | .cursor/hooks/verify-harness.sh 2>/dev/null)
if echo "$OUTPUT" | rg -q '^\{\}$'; then
  pass "verify-harness handles malformed contract (BUG-7 fix)"
else
  fail "verify-harness should return {} for malformed contract (BUG-7): $(echo "$OUTPUT" | head -1)"
fi
# Verify it does NOT contain HARNESS GATE
if ! echo "$OUTPUT" | rg -q "HARNESS GATE"; then
  pass "verify-harness does not fire HARNESS GATE on malformed contract"
else
  fail "verify-harness should NOT fire HARNESS GATE on malformed contract (BUG-7)"
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
