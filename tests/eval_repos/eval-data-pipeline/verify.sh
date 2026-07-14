#!/bin/bash
# Binary pass/fail checks for the eval-data-pipeline scenario.
# Run from inside tests/eval_repos/eval-data-pipeline/ after a session.

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

# --- Domain: pipeline hardening ---

PIPELINE=$(find . -name "pipeline*.py" -not -path "./.cursor/*" | head -1)
if [ -z "$PIPELINE" ]; then
  check "domain: pipeline source found" FAIL
else
  check "domain: pipeline source found" PASS

  python3 "$PIPELINE" >/tmp/eval-data-pipeline-run.log 2>&1
  [ $? -eq 0 ] \
    && check "domain: pipeline survives malformed row in data/orders.csv" PASS \
    || check "domain: pipeline survives malformed row in data/orders.csv" FAIL

  grep -qE "^import logging|^from logging|logging\.(getLogger|basicConfig)" "$PIPELINE" \
    && check "domain: structured logging used" PASS \
    || check "domain: structured logging used" FAIL

  grep -qE "try:|except " "$PIPELINE" \
    && check "domain: error handling added" PASS \
    || check "domain: error handling added" FAIL
fi

TEST_FILE=$(find . -name "test_*.py" -o -name "*_test.py" 2>/dev/null | grep -v "^./.cursor/" | head -1)
if [ -n "$TEST_FILE" ]; then
  check "domain: test file exists" PASS
  (python3 -m pytest "$TEST_FILE" -q >/tmp/eval-data-pipeline-test.log 2>&1) \
    && check "domain: tests pass" PASS \
    || check "domain: tests pass" FAIL
else
  check "domain: test file exists" FAIL
  check "domain: tests pass" FAIL
fi

echo ""
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
