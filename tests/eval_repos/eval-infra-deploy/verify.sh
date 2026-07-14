#!/bin/bash
# Binary pass/fail checks for the eval-infra-deploy scenario.
# Run from inside tests/eval_repos/eval-infra-deploy/ after a session.

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

DEPLOYMENT=$(find manifests -iname "deployment*.yaml" -o -iname "deployment*.yml" 2>/dev/null | head -1)

# --- Harness artifacts ---

[ -f .harness/state.json ] && check "harness: state.json exists" PASS || check "harness: state.json exists" FAIL
[ -f .harness/contract.json ] && check "harness: contract.json exists" PASS || check "harness: contract.json exists" FAIL
[ -f .harness/breadcrumbs.jsonl ] && check "harness: breadcrumbs.jsonl exists" PASS || check "harness: breadcrumbs.jsonl exists" FAIL

if [ -f .harness/contract.json ]; then
  VERIFIED=$(python3 -c "import json; print(json.load(open('.harness/contract.json')).get('verified', False))" 2>/dev/null)
  [ "$VERIFIED" = "True" ] && check "harness: contract.json verified=true" PASS || check "harness: contract.json verified=true" FAIL
fi

# --- Domain: deploy safety gates ---

if [ -z "$DEPLOYMENT" ]; then
  check "domain: deployment manifest found" FAIL
else
  check "domain: deployment manifest found" PASS

  grep -qE "resources:" "$DEPLOYMENT" && grep -qE "limits:" "$DEPLOYMENT" && grep -qE "requests:" "$DEPLOYMENT" \
    && check "domain: resource requests/limits set" PASS \
    || check "domain: resource requests/limits set" FAIL

  grep -qE "readinessProbe:" "$DEPLOYMENT" \
    && check "domain: readiness probe added" PASS \
    || check "domain: readiness probe added" FAIL

  grep -qE "livenessProbe:" "$DEPLOYMENT" \
    && check "domain: liveness probe added" PASS \
    || check "domain: liveness probe added" FAIL

  grep -qE "image:.*:latest" "$DEPLOYMENT" \
    && check "domain: image tag pinned (not :latest)" FAIL \
    || check "domain: image tag pinned (not :latest)" PASS
fi

# Excludes this repo's own meta-docs (README.md, PROMPT.md) which mention
# "rollback" as a checklist item, not as an actual documented plan.
grep -riq "rollback" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.sh" \
  --exclude-dir=".cursor" --exclude-dir=".git" --exclude-dir=".harness" \
  --exclude="README.md" --exclude="PROMPT.md" --exclude="verify.sh" . \
  && check "domain: rollback plan documented" PASS \
  || check "domain: rollback plan documented" FAIL

echo ""
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
