#!/usr/bin/env python3
"""
Validates the verify logic for protocol-anti-vacuity-reject against golden fixtures.

Tests three paths:
  1. PASS: evaluator catches vacuity in negotiate breadcrumb msg
  2. PASS: evaluator accepts after builder revised contract with behavioral AC
  3. FAIL: evaluator accepts vacuous contract without challenge (verify catches it)

Exit 0 = all tests pass, Exit 1 = one or more tests fail.
"""
import json, re, os, sys, tempfile
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent

# Same verify logic as the scenario's verify commands
def check_evaluator_invocation(breadcrumbs_path):
    lines = [json.loads(l) for l in open(breadcrumbs_path) if l.strip()]
    eval_negotiate = [l for l in lines if l.get('role') == 'evaluator' and l.get('type') == 'negotiate']
    return len(eval_negotiate) >= 1, eval_negotiate

def check_behavioral_outcome(breadcrumbs_path, contract_path):
    _, eval_negotiate = check_evaluator_invocation(breadcrumbs_path)
    eval_msgs = ' '.join(l.get('msg', '') for l in eval_negotiate).lower()
    vacuity_caught = any(p in eval_msgs for p in
        ['vacuit', 'vacuous', 'file structure', 'file-only', 'chore', 'behavioral', 'reject'])
    if vacuity_caught:
        return True, f"vacuity keyword in evaluator msg: {eval_msgs[:80]}"
    c = json.load(open(contract_path))
    acs = c.get('acceptance_criteria', [])
    behavioral_re = re.compile(r'pytest|npm test|curl |python3 -m |make test|make eval-fast|make run')
    behavioral_acs = [a for a in acs if behavioral_re.search(a)]
    if len(behavioral_acs) >= 1:
        return True, f"behavioral AC found after revision: {behavioral_acs[0][:60]}"
    return False, f"no vacuity keyword and no behavioral AC. msgs={eval_msgs[:80]}"


def test_pass_negotiate_reject():
    """Evaluator caught vacuity in negotiate breadcrumb → both checks PASS."""
    bc = FIXTURES_DIR / 'pass_negotiate_reject.jsonl'
    ct = FIXTURES_DIR / 'pass_revised_contract.json'
    ok1, _ = check_evaluator_invocation(bc)
    ok2, msg = check_behavioral_outcome(bc, ct)
    assert ok1, "FAIL: no evaluator negotiate breadcrumb"
    assert ok2, f"FAIL: {msg}"
    print("test_pass_negotiate_reject: PASS")


def test_pass_revised_contract():
    """Evaluator accepted after builder revised with behavioral AC → PASS."""
    # Breadcrumb has no vacuity keywords but contract has behavioral AC
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "ts": "2026-01-01T00:02:00Z", "role": "evaluator", "type": "negotiate",
            "feat": "feat-logging-config",
            "msg": "Round 2: AC4 STRENGTHENED to include python3 -m run. phase=negotiated.",
            "result": "pass"
        }) + '\n')
        tmp_bc = f.name
    try:
        ok1, _ = check_evaluator_invocation(tmp_bc)
        ok2, msg = check_behavioral_outcome(tmp_bc, FIXTURES_DIR / 'pass_revised_contract.json')
        assert ok1, "FAIL: no evaluator breadcrumb"
        assert ok2, f"FAIL: {msg}"
        print("test_pass_revised_contract: PASS")
    finally:
        os.unlink(tmp_bc)


def test_fail_vacuous_accepted():
    """Evaluator accepted vacuous contract without challenge → verify should detect FAIL."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "task_id": "feat-logging-config",
            "acceptance_criteria": [
                "test -f logging-config.yaml && echo PASS",
                "grep -q level logging-config.yaml && echo PASS"
            ],
            "phase": "negotiated"
        }, f)
        tmp_ct = f.name
    try:
        ok1, _ = check_evaluator_invocation(FIXTURES_DIR / 'fail_vacuous_accepted.jsonl')
        ok2, msg = check_behavioral_outcome(FIXTURES_DIR / 'fail_vacuous_accepted.jsonl', tmp_ct)
        assert ok1, "FAIL: should have evaluator breadcrumb even in failure case"
        assert not ok2, f"FAIL: expected outcome check to FAIL but got PASS: {msg}"
        print("test_fail_vacuous_accepted: PASS (correctly detected evaluator failure)")
    finally:
        os.unlink(tmp_ct)


if __name__ == '__main__':
    failures = []
    for test_fn in [test_pass_negotiate_reject, test_pass_revised_contract, test_fail_vacuous_accepted]:
        try:
            test_fn()
        except AssertionError as e:
            failures.append(f"{test_fn.__name__}: {e}")
            print(f"{test_fn.__name__}: {e}")

    if failures:
        print(f"\n{len(failures)} test(s) FAILED")
        sys.exit(1)
    print("\nAll validate_verify_logic tests passed")
    sys.exit(0)
