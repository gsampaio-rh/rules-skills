"""Unit tests for tests/eval/fixtures/ci_suites.json.

Asserts tier sizes, subset relationship, and YAML file existence (AC10).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).parent
CI_SUITES_PATH = EVAL_DIR / "fixtures" / "ci_suites.json"
SCENARIOS_DIR = EVAL_DIR / "scenarios"
LONG_SCENARIOS_DIR = SCENARIOS_DIR / "long"

PR_EXPECTED_COUNT = 11
NIGHTLY_EXPECTED_COUNT = 31


@pytest.fixture(scope="module")
def suites():
    return json.loads(CI_SUITES_PATH.read_text())


def test_ci_suites_file_exists():
    assert CI_SUITES_PATH.exists(), "ci_suites.json not found"


def test_pr_tier_has_expected_count(suites):
    """AC10: pr list has exactly 11 ids."""
    assert len(suites["pr"]) == PR_EXPECTED_COUNT, (
        f"pr tier has {len(suites['pr'])} scenarios, expected {PR_EXPECTED_COUNT}: {suites['pr']}"
    )


def test_nightly_tier_has_expected_count(suites):
    """AC10: nightly list has exactly 31 ids."""
    assert len(suites["nightly"]) == NIGHTLY_EXPECTED_COUNT, (
        f"nightly tier has {len(suites['nightly'])} scenarios, expected {NIGHTLY_EXPECTED_COUNT}"
    )


def test_pr_is_subset_of_nightly(suites):
    """AC10: pr is a subset of nightly (all pr scenarios also run nightly)."""
    pr_set = set(suites["pr"])
    nightly_set = set(suites["nightly"])
    extra = pr_set - nightly_set
    assert not extra, f"pr scenarios not in nightly: {sorted(extra)}"


def test_no_duplicates_within_pr(suites):
    pr = suites["pr"]
    assert len(pr) == len(set(pr)), f"Duplicate ids in pr tier: {pr}"


def test_no_duplicates_within_nightly(suites):
    nightly = suites["nightly"]
    assert len(nightly) == len(set(nightly)), f"Duplicate ids in nightly tier: {nightly}"


def test_all_pr_ids_have_yaml_file(suites):
    """AC10: all pr scenario ids exist as YAML files in tests/eval/scenarios/."""
    all_yaml_ids = {
        p.stem.replace("-", "_")  # normalize hyphens if any
        for p in list(SCENARIOS_DIR.glob("*.yaml")) + list(LONG_SCENARIOS_DIR.glob("*.yaml"))
    }
    # Also collect by raw 'id' field from YAML content
    yaml_file_ids: set[str] = set()
    for path in list(SCENARIOS_DIR.glob("*.yaml")) + list(LONG_SCENARIOS_DIR.glob("*.yaml")):
        try:
            import yaml
            s = yaml.safe_load(path.read_text())
            if isinstance(s, dict) and "id" in s:
                yaml_file_ids.add(s["id"])
        except Exception:
            pass

    missing = [sid for sid in suites["pr"] if sid not in yaml_file_ids]
    assert not missing, (
        f"pr scenario ids without YAML files: {missing}\n"
        f"Available scenario ids: {sorted(yaml_file_ids)}"
    )


def test_all_pr_ids_are_protocol_prefixed(suites):
    """PR tier should only contain protocol_* scenarios (by design)."""
    non_protocol = [sid for sid in suites["pr"] if not sid.startswith("protocol_")]
    assert not non_protocol, f"Non-protocol ids in pr tier: {non_protocol}"


def test_slow_scenarios_not_in_pr_tier(suites):
    """The 3 slow edge-case scenarios should be nightly-only."""
    slow = {
        "protocol_replan_mid_build",
        "protocol_eval_fail_retest",
        "protocol_contract_gate_denied_recovery",
    }
    in_pr = slow & set(suites["pr"])
    assert not in_pr, f"Slow scenarios should be nightly-only but found in pr: {in_pr}"


def test_slow_scenarios_in_nightly(suites):
    """The 3 slow scenarios should be included in nightly."""
    slow = {
        "protocol_replan_mid_build",
        "protocol_eval_fail_retest",
        "protocol_contract_gate_denied_recovery",
    }
    missing = slow - set(suites["nightly"])
    assert not missing, f"Slow scenarios missing from nightly: {missing}"
