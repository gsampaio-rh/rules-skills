#!/bin/bash
# beforeSubmitPrompt hook: routes non-trivial prompts through the planner.
#
# Key principle from Anthropic's long-running agent harness:
# Don't block prompts — route them. The planner auto-decomposes complex work
# into a spec + feature list. The agent should do this automatically, not
# wait for the user to invoke /planner manually.
#
# Logic:
#   1. Harness already active (contract.json or state.json exists) → allow silently
#   2. Glue message (under 20 chars) → allow silently
#   3. User explicitly opts out ("skip harness") → allow silently
#   4. Complexity signals detected → ALLOW + inject agent_message to route through planner
#   5. Default → allow silently

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: triggered" >> "$HOOK_LOG" 2>/dev/null

CONTRACT=".cursor/harness/contract.json"
STATE=".cursor/harness/state.json"

# Harness already active — no routing needed
if [ -f "$CONTRACT" ] || [ -f "$STATE" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: harness active, allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

prompt=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('prompt', data.get('content', '')))
except Exception:
    print('')
" 2>/dev/null)

length=${#prompt}

# Glue messages pass through silently
if [ "$length" -lt 20 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: glue message ($length chars), allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

prompt_lower=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

# Explicit opt-out
if echo "$prompt_lower" | grep -q "skip harness"; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: user opted out, allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Detect complexity — same heuristics, but now we ROUTE instead of BLOCK
COMPLEX=$(echo "$prompt_lower" | python3 -c "
import re, sys

prompt = sys.stdin.read()

# Maintenance/fix prompts don't need planning
maintenance = r'\b(fix|bug|verify|review|check|update|rename|delete|remove|commit|sync|clean|lint|format|typo|patch|hotfix|tweak|adjust|correct)\b'
if re.search(maintenance, prompt):
    print('simple')
    sys.exit(0)

# Detect prompts about building NEW things
build_verbs = r'\b(implement|build|create|develop|refactor|migrate|redesign|architect|integrate|overhaul|rewrite)\b'
scope_words = r'\b(feature|module|service|component|system|api|endpoint|database|schema|pipeline|workflow|authentication|authorization)\b'

verb_hits = len(re.findall(build_verbs, prompt))
scope_hits = len(re.findall(scope_words, prompt))
at_refs = prompt.count('@')

score = verb_hits + scope_hits + at_refs

if score >= 3:
    print('complex')
else:
    print('simple')
" 2>/dev/null)

if [ "$COMPLEX" = "complex" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: ROUTING — non-trivial prompt, injecting planner instructions" >> "$HOOK_LOG" 2>/dev/null
  cat <<'EOF'
{
  "agent_message": "HARNESS ROUTING: This prompt describes non-trivial work. Before implementing anything, you MUST launch the /planner subagent to decompose this into a spec and feature list. Do NOT start coding directly. The flow is: (1) launch /planner with the user's full request, (2) present the spec to the user for confirmation, (3) then begin contract negotiation for the first feature. If the user says 'skip harness', proceed without the planner."
}
EOF
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: simple prompt, allowing" >> "$HOOK_LOG" 2>/dev/null
echo '{}'
exit 0
