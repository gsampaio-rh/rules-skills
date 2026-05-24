#!/bin/bash
# beforeSubmitPrompt hook: blocks non-trivial prompts when no harness is active.
#
# Logic:
#   1. Harness already active (contract.json or state.json exists) → allow
#   2. Glue message (under 20 chars) → allow
#   3. User explicitly opts out ("skip harness") → allow
#   4. Complexity signals detected → block with harness suggestion
#   5. Default → allow

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: triggered" >> "$HOOK_LOG" 2>/dev/null

CONTRACT=".cursor/harness/contract.json"
STATE=".cursor/harness/state.json"

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

if [ "$length" -lt 20 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: glue message ($length chars), allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

prompt_lower=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

if echo "$prompt_lower" | grep -q "skip harness"; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: user opted out, allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

COMPLEX=$(echo "$prompt_lower" | python3 -c "
import re, sys

prompt = sys.stdin.read()

# Maintenance/fix prompts are not spec-worthy — allow them through
maintenance = r'\b(fix|bug|verify|review|check|update|rename|delete|remove|commit|sync|clean|lint|format|typo|patch|hotfix|tweak|adjust|correct)\b'
if re.search(maintenance, prompt):
    print('simple')
    sys.exit(0)

# Only flag prompts that are clearly about building NEW things
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
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: BLOCKED — non-trivial prompt without harness" >> "$HOOK_LOG" 2>/dev/null
  cat <<'EOF'
{
  "continue": false,
  "user_message": "This looks like non-trivial work. Start with /planner to create a spec, then use the adversarial harness for contract negotiation and verification. If this is actually simple, add 'skip harness' to your prompt."
}
EOF
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: simple prompt, allowing" >> "$HOOK_LOG" 2>/dev/null
echo '{}'
exit 0
