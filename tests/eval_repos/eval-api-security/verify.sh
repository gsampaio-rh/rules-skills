#!/bin/bash
# Binary pass/fail checks for the eval-api-security scenario.
# Run from inside tests/eval_repos/eval-api-security/ after a session.

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

pass=0
fail=0

check() {
  local label="$1"
  local result="$2"
  if [ "$result" = "PASS" ]; then
    echo "PASS  $label"
    pass=$((pass + 1))
  else
    echo "FAIL  $label"
    fail=$((fail + 1))
  fi
}

# --- Harness artifacts ---

[ -f .harness/state.json ] && check "harness: state.json exists" PASS || check "harness: state.json exists" FAIL
[ -f .harness/contract.json ] && check "harness: contract.json exists" PASS || check "harness: contract.json exists" FAIL
[ -f .harness/breadcrumbs.jsonl ] && check "harness: breadcrumbs.jsonl exists" PASS || check "harness: breadcrumbs.jsonl exists" FAIL

if [ -f .harness/contract.json ]; then
  VERIFIED=$(python3 -c "import json; print(json.load(open('.harness/contract.json')).get('verified', False))" 2>/dev/null)
  [ "$VERIFIED" = "True" ] && check "harness: contract.json verified=true" PASS || check "harness: contract.json verified=true" FAIL
fi

if [ -f .harness/breadcrumbs.jsonl ]; then
  grep -q '"role":\s*"evaluator"' .harness/breadcrumbs.jsonl 2>/dev/null \
    && check "harness: evaluator breadcrumb present" PASS \
    || check "harness: evaluator breadcrumb present" FAIL
fi

# --- Domain: security gaps closed ---

grep -qE "super-secret-flask-key-do-not-share|sk-internal-9f8a7b6c5d4e3f2a1b0c" src/*.py 2>/dev/null \
  && check "security: hardcoded secrets removed" FAIL \
  || check "security: hardcoded secrets removed" PASS

grep -qE "f[\"']SELECT.*\{owner\}|WHERE owner = '\{owner\}'" src/app.py 2>/dev/null \
  && check "security: SQL injection on /notes fixed" FAIL \
  || check "security: SQL injection on /notes fixed" PASS

grep -qiE "authorization|require_auth|@login_required|check_token|api_key" src/app.py 2>/dev/null \
  && check "security: authentication added" PASS \
  || check "security: authentication added" FAIL

grep -qE "debug=True" src/app.py 2>/dev/null \
  && check "security: debug mode disabled/gated" FAIL \
  || check "security: debug mode disabled/gated" PASS

grep -qiE "isinstance|len\(.*\)\s*[<>]|ValueError|abort\(400\)|400" src/app.py 2>/dev/null \
  && check "security: input validation added" PASS \
  || check "security: input validation added" FAIL

echo ""
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
