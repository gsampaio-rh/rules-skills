#!/bin/bash
# beforeSubmitPrompt hook: fast-path handler for obvious cases.
#
# Deterministic cases (no LLM needed):
#   1. Harness active (state.json or contract.json exists) → skip planner routing, continue to skill-suggest
#   2. Glue message (length < 10 AND word_count ≤ 2) → allow silently
#   3. User explicitly opts out ("skip harness") → allow silently
#   4. Cold start: no state.json + non-trivial prompt (> 10 chars) → inject planner routing
#   5. Skill-suggest: for all non-glue prompts, inject relevant skill hints via followup_message

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "harness-gate"
input="$HOOK_INPUT"

CONTRACT=".harness/contract.json"
STATE=".harness/state.json"

# Case 1: Harness already active — skip planner routing but continue to skill-suggest (Case 5).
# P5: leftover contract.json must NOT inject HARNESS GATE / HARNESS ROUTING on Q&A prompts;
# this branch only suppresses cold-start routing (never emits HARNESS GATE).
harness_active=false
if [ -f "$CONTRACT" ] || [ -f "$STATE" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: harness active, skipping planner routing" >> "$HOOK_LOG" 2>/dev/null
  harness_active=true
fi

# Extract prompt text
prompt=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('prompt', data.get('content', '')))
except Exception:
    print('')
" 2>/dev/null)

length=${#prompt}
word_count=$(echo "$prompt" | wc -w | tr -d '[:space:]')

# Case 2: Glue messages — short conversational responses (< 10 chars AND ≤ 2 words).
# This heuristic keeps "ok", "yes", "got it", "proceed" silent while letting
# short imperative feature prompts like "refatora tudo" or "migra o banco" through.
if [ "$length" -lt 10 ] && [ "$word_count" -le 2 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: glue message ($length chars, $word_count words), allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# P6: count non-glue user turns for session handoff advisory (context-health).
hooks_session_stats_inc turns

prompt_lower=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

# Case 3: Explicit opt-out
if echo "$prompt_lower" | grep -q "skip harness"; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: user opted out, allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Case 4: Cold start — no harness + non-trivial prompt → advise planner routing.
# Only fires when harness is NOT active; active-harness prompts fall through to Case 5.
# Threshold at 10 chars catches short multilingual feature prompts (e.g. "migra o banco").
if [ "$harness_active" = false ] && [ "$length" -gt 10 ]; then
  SIMPLE_PATTERNS="review|audit|check|what|how|why|where|explain|debug|fix this|rename|add comment|update readme"
  if ! echo "$prompt_lower" | grep -qE "$SIMPLE_PATTERNS"; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: cold start routing ($length chars, non-trivial)" >> "$HOOK_LOG" 2>/dev/null
    mkdir -p .harness
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > .harness/.routing-pending
    cat <<EOF
{
  "followup_message": "HARNESS ROUTING: No .harness/state.json found and this looks like non-trivial work. Before implementing, launch the /planner subagent to create state.json with tasks. Implementation writes are BLOCKED until state.json exists. If this is actually simple (1-2 files, no architecture), say 'skip harness' to proceed directly."
}
EOF
    exit 0
  fi
fi

# Case 5: Skill suggestions — fire for all non-glue, non-routing prompts.
# Fires for both harness-active prompts (mid-session) and cold-start simple/short prompts.
#
# SKILLS_DIR resolution (first match wins):
#   1. SKILLS_DIR env var (for tests and explicit overrides)
#   2. .cursor/skills relative to CWD (production — populated by make sync-local)
_skills_dir="${SKILLS_DIR:-}"
if [ -z "$_skills_dir" ] && [ -d ".cursor/skills" ]; then
  _skills_dir=".cursor/skills"
fi

SKILL_SUGGEST="$SCRIPT_DIR/skill-suggest.py"
if [ -f "$SKILL_SUGGEST" ] && [ -d "$_skills_dir" ]; then
  TMP_SKILLS=$(mktemp)
  trap 'rm -f "$TMP_SKILLS"' EXIT
  python3 "$SKILL_SUGGEST" --skills-dir "$_skills_dir" --prompt "$prompt" --format text > "$TMP_SKILLS" 2>/dev/null
  if [ -s "$TMP_SKILLS" ]; then
    python3 - "$TMP_SKILLS" <<'PYEOF'
import json, sys
text = open(sys.argv[1]).read().strip()
if text:
    print(json.dumps({"followup_message": text}))
else:
    print('{}')
PYEOF
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: skill suggestions injected" >> "$HOOK_LOG" 2>/dev/null
    exit 0
  fi
fi

# All other cases: allow silently
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: allowing (no skill match)" >> "$HOOK_LOG" 2>/dev/null
echo '{}'
exit 0
