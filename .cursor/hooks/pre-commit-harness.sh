#!/bin/bash
# beforeShellExecution hook: fires on git commit commands.
#
# Automatically:
#   1. Records a checkpoint breadcrumb with commit context
#   2. Checks if harness contract is unverified (warns but doesn't block)
#   3. Injects agent_message with post-commit instructions:
#      - Update state.json if harness is active
#      - Review changed files for doc/changelog updates
#      - Pick next feature if current one is verified
#
# Never blocks the commit. Always allows. Guides the agent on follow-up work.

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: triggered" >> "$HOOK_LOG" 2>/dev/null

BREADCRUMBS=".cursor/breadcrumbs.jsonl"
CONTRACT=".cursor/harness/contract.json"
STATE=".cursor/harness/state.json"

command=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

# Only act on actual git commit commands (not git add, git status, etc.)
if ! echo "$command" | grep -q "git commit"; then
  echo '{"permission":"allow"}'
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: git commit detected" >> "$HOOK_LOG" 2>/dev/null

# --- 1. Auto-record breadcrumb ---

TS=$(date -u +%Y-%m-%dT%H:%M:%S)

# Extract commit message from the command if available
COMMIT_MSG=$(echo "$command" | python3 -c "
import sys, re
cmd = sys.stdin.read()
# Match -m 'msg', -m \"msg\", or heredoc patterns
match = re.search(r'-m\s+[\"'\''](.*?)[\"'\''']', cmd)
if match:
    print(match.group(1)[:120])
else:
    # Try heredoc pattern: -m \"\$(cat <<'EOF' ... EOF)\"
    match = re.search(r'<<.*?EOF.*?\n(.*?)\nEOF', cmd, re.DOTALL)
    if match:
        print(match.group(1).strip()[:120])
    else:
        print('(commit message not extracted)')
" 2>/dev/null)

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null | head -10)
STAGED_COUNT=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')

# Determine the breadcrumb feature context
FEAT="null"
if [ -f "$CONTRACT" ]; then
  FEAT=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    fid = data.get('feature_id', data.get('feature', ''))
    print(f'\"{fid}\"' if fid else 'null')
except Exception:
    print('null')
" 2>/dev/null)
fi

# Append breadcrumb
mkdir -p "$(dirname "$BREADCRUMBS")" 2>/dev/null
echo "{\"ts\":\"$TS\",\"role\":\"builder\",\"type\":\"checkpoint\",\"feat\":$FEAT,\"msg\":\"Commit: $COMMIT_MSG ($STAGED_COUNT files)\"}" >> "$BREADCRUMBS" 2>/dev/null

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: breadcrumb recorded" >> "$HOOK_LOG" 2>/dev/null

# --- 2. Build post-commit guidance ---

GUIDANCE=""

# Check harness state
if [ -f "$CONTRACT" ]; then
  CONTRACT_STATE=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    feature = data.get('feature', 'unknown')
    verified = data.get('verified', False)
    phase = data.get('phase', 'unknown')
    print(f'{feature}|{verified}|{phase}')
except Exception:
    print('unknown|False|unknown')
" 2>/dev/null)

  FEATURE=$(echo "$CONTRACT_STATE" | cut -d'|' -f1)
  VERIFIED=$(echo "$CONTRACT_STATE" | cut -d'|' -f2)
  PHASE=$(echo "$CONTRACT_STATE" | cut -d'|' -f3)

  if [ "$VERIFIED" = "True" ]; then
    GUIDANCE="POST-COMMIT (harness active): Feature \"$FEATURE\" is verified. After this commit: (1) Update .cursor/harness/state.json — set feature status to 'committed'. (2) Pick the next pending feature from state.json and start contract negotiation."
  else
    GUIDANCE="POST-COMMIT WARNING: Committing while contract for \"$FEATURE\" is unverified (phase=$PHASE). If this is a partial checkpoint, that's fine. But don't mark the feature as done until the /evaluator passes."
  fi
elif [ -f "$STATE" ]; then
  GUIDANCE="POST-COMMIT (harness active): Commit recorded. Check .cursor/harness/state.json for the next pending feature."
fi

# Check for doc-worthy changes
DOC_CHANGES=""
if echo "$STAGED_FILES" | grep -qE '\.(md|rst|txt)$'; then
  DOC_CHANGES="Documentation files were included in this commit."
fi

HAS_API_CHANGES=""
if echo "$STAGED_FILES" | grep -qiE '(route|endpoint|api|schema|migration|model)'; then
  HAS_API_CHANGES="API/schema/model files changed — verify that related documentation (README, API docs, migration notes) is up to date."
fi

HAS_CONFIG_CHANGES=""
if echo "$STAGED_FILES" | grep -qiE '(config|\.env|settings|manifest|package\.json|pyproject)'; then
  HAS_CONFIG_CHANGES="Configuration files changed — verify that setup instructions or environment docs reflect these changes."
fi

# --- 3. Compose agent_message ---

PARTS=""
if [ -n "$GUIDANCE" ]; then
  PARTS="$GUIDANCE"
fi
if [ -n "$HAS_API_CHANGES" ]; then
  PARTS="$PARTS\n$HAS_API_CHANGES"
fi
if [ -n "$HAS_CONFIG_CHANGES" ]; then
  PARTS="$PARTS\n$HAS_CONFIG_CHANGES"
fi

# If there's nothing noteworthy, just allow silently
if [ -z "$PARTS" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: no guidance needed, allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{"permission":"allow"}'
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: injecting post-commit guidance" >> "$HOOK_LOG" 2>/dev/null

# Escape for JSON
ESCAPED_PARTS=$(echo -e "$PARTS" | python3 -c "
import sys, json
text = sys.stdin.read().strip()
print(json.dumps(text))
" 2>/dev/null)

cat <<EOF
{
  "permission": "allow",
  "agent_message": $ESCAPED_PARTS
}
EOF
exit 0
