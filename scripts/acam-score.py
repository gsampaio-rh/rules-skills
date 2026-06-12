#!/usr/bin/env python3
"""
Static ACAM (Agent Configuration Assessment Model) scorer.

Inspects observable repo artifacts against acam-worksheet.md criteria
and produces a machine-readable JSON scorecard. No API key required.

Usage:
    python scripts/acam-score.py [--root PATH] [--format json|markdown]

Exit codes:
    0  scoring succeeded (even if levels are low)
    2  --root path does not exist
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

ACAM_VERSION = "1.0"
LEVEL_SCORE = {"none": 0, "basic": 1, "intermediate": 2, "advanced": 3}


@dataclass
class Check:
    id: str
    criterion: str
    result: bool
    evidence: str


def _find(root: Path, *patterns: str) -> tuple[bool, str]:
    """Return (found, first_relative_path_or_'not found')."""
    for pat in patterns:
        matches = sorted(root.glob(pat))
        if matches:
            return True, str(matches[0].relative_to(root))
    return False, "not found"


def _read_text(root: Path, rel_path: str) -> str:
    try:
        return (root / rel_path).read_text(errors="ignore")
    except OSError:
        return ""


def _ladder_level(checks: list[Check]) -> tuple[str, int]:
    """
    Apply worksheet ladder: advanced > intermediate > basic > none.
    A single failing check at level N caps the dimension below N.
    """
    def _all_pass(prefix: str) -> bool:
        relevant = [c for c in checks if c.id.startswith(prefix)]
        return bool(relevant) and all(c.result for c in relevant)

    if _all_pass("") and not checks:
        return "none", 0
    has_basic = any(c.id.endswith(".basic") or ".basic." in c.id for c in checks)
    basic_ok = _all_pass_level(checks, "basic")
    if not basic_ok:
        return "none", 0
    inter_ok = _all_pass_level(checks, "intermediate")
    if not inter_ok:
        return "basic", 1
    adv_checks = [c for c in checks if ".advanced." in c.id]
    if not adv_checks:
        return "intermediate", 2
    if all(c.result for c in adv_checks):
        return "advanced", 3
    return "intermediate", 2


def _all_pass_level(checks: list[Check], level: str) -> bool:
    relevant = [c for c in checks if f".{level}." in c.id]
    return bool(relevant) and all(c.result for c in relevant)


# ---------------------------------------------------------------------------
# Dimension scorers
# ---------------------------------------------------------------------------

def score_configuration(root: Path) -> tuple[str, int, list[Check]]:
    checks: list[Check] = []

    # Basic: any AI config file
    found, path = _find(root,
        ".cursorrules", "CLAUDE.md", ".windsurfrules",
        ".cursor/rules/*.mdc", "library/cursor/rules/*.mdc")
    checks.append(Check(
        id="configuration.basic.has_ai_config",
        criterion="Does the repo have any AI configuration file? (.cursorrules, CLAUDE.md, .windsurfrules, or any .mdc rule file)",
        result=found,
        evidence=path,
    ))

    if not found:
        return "none", 0, checks

    # Intermediate: ≥2 distinct scope types (alwaysApply:true AND alwaysApply:false)
    has_always = False
    has_conditional = False
    scope_paths: list[str] = []
    for rules_dir in ("library/cursor/rules", ".cursor/rules"):
        p = root / rules_dir
        if not p.exists():
            continue
        for mdc in sorted(p.glob("*.mdc")):
            text = mdc.read_text(errors="ignore")
            if "alwaysApply: true" in text:
                has_always = True
                scope_paths.append(str(mdc.relative_to(root)))
            elif "alwaysApply: false" in text:
                has_conditional = True
                scope_paths.append(str(mdc.relative_to(root)))
    distinct_scopes = has_always and has_conditional
    checks.append(Check(
        id="configuration.intermediate.distinct_scopes",
        criterion="Are there ≥2 distinct rule scope types (alwaysApply:true AND alwaysApply:false)?",
        result=distinct_scopes,
        evidence=(f"Both scope types found; e.g. {scope_paths[:2]}"
                  if distinct_scopes else "Only one scope type found"),
    ))

    # Intermediate: documented rationale for when rules fire
    rationale_found, rationale_path = _find(root,
        "AGENTS.md", "docs/RULES_STANDARD.md",
        "library/cursor/rules/RULES_CHANGELOG.md")
    checks.append(Check(
        id="configuration.intermediate.documented_rationale",
        criterion="Is there a documented rationale for WHEN each rule fires? (AGENTS.md rules section or RULES_STANDARD.md)",
        result=rationale_found,
        evidence=rationale_path,
    ))

    if not _all_pass_level(checks, "intermediate"):
        return "basic", 1, checks

    # Advanced: per-rule effectiveness data (ablation scores keyed by rule name)
    # Must be a fixture/data file with per_rule or rule_scores keys — not a generic eval report.
    ablation_ok = False
    ablation_evidence = "not found"
    for pat in ("tests/eval/fixtures/ablation_baseline.json",
                ".harness/docs/ablation_scores.json",
                ".harness/docs/per_rule_effectiveness.json"):
        candidate = root / pat
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text())
                if "per_rule" in data or "rule_scores" in data or "ablation_scores" in data:
                    ablation_ok = True
                    ablation_evidence = str(candidate.relative_to(root))
                    break
            except (json.JSONDecodeError, OSError):
                pass
    checks.append(Check(
        id="configuration.advanced.per_rule_effectiveness",
        criterion="Is there per-rule effectiveness data (ablation or eval score per rule)?",
        result=ablation_ok,
        evidence=ablation_evidence,
    ))

    # Advanced: cross-tool portability documented
    portability_found, portability_path = _find(root, "AGENTS.md")
    checks.append(Check(
        id="configuration.advanced.cross_tool_portability",
        criterion="Is cross-tool portability documented? (AGENTS.md or equivalent)",
        result=portability_found,
        evidence=portability_path,
    ))

    level, score = _ladder_level(checks)
    return level, score, checks


def score_workflows(root: Path) -> tuple[str, int, list[Check]]:
    checks: list[Check] = []

    # Basic: any structured task lifecycle
    lifecycle_found, lifecycle_path = _find(root,
        ".harness/state.json",
        ".github/ISSUE_TEMPLATE/*.md",
        ".github/ISSUE_TEMPLATE/*.yaml",
        ".github/pull_request_template.md")
    checks.append(Check(
        id="workflows.basic.task_lifecycle",
        criterion="Does the repo have any structured task lifecycle? (state.json, issue template, PR checklist, or equivalent)",
        result=lifecycle_found,
        evidence=lifecycle_path,
    ))

    if not lifecycle_found:
        return "none", 0, checks

    # Intermediate: structural gate blocking writes without contract
    gate_found, gate_path = _find(root,
        "library/cursor/hooks/contract-gate.sh",
        ".cursor/hooks/contract-gate.sh")
    checks.append(Check(
        id="workflows.intermediate.structural_gate",
        criterion="Is there a hook or structural gate that blocks implementation writes until a contract or spec exists?",
        result=gate_found,
        evidence=gate_path,
    ))

    # Intermediate: append-only audit log
    log_found, log_path = _find(root, ".harness/breadcrumbs.jsonl")
    checks.append(Check(
        id="workflows.intermediate.audit_log",
        criterion="Is there an append-only audit log? (breadcrumbs.jsonl or equivalent)",
        result=log_found,
        evidence=log_path,
    ))

    if not _all_pass_level(checks, "intermediate"):
        return "basic", 1, checks

    # Advanced: machine-readable acceptance criteria (contract.json with non-empty AC list)
    contract_path_obj = root / ".harness/contract.json"
    contract_ac_ok = False
    contract_evidence = "not found"
    if contract_path_obj.exists():
        try:
            contract = json.loads(contract_path_obj.read_text())
            has_ac = isinstance(contract.get("acceptance_criteria"), list) and len(contract["acceptance_criteria"]) > 0
            contract_ac_ok = has_ac
            contract_evidence = (
                ".harness/contract.json (acceptance_criteria present)"
                if has_ac
                else ".harness/contract.json exists but acceptance_criteria missing or empty"
            )
        except (json.JSONDecodeError, OSError):
            contract_evidence = ".harness/contract.json found but not parseable"
    checks.append(Check(
        id="workflows.advanced.machine_readable_criteria",
        criterion="Does machine-readable acceptance-criteria-gated implementation exist — criteria negotiated before any write?",
        result=contract_ac_ok,
        evidence=contract_evidence,
    ))

    # Advanced: automated eval regression suite (CI workflow + seeded baseline)
    ci_found, ci_path = _find(root,
        ".github/workflows/eval-regression-pr.yml",
        ".github/workflows/eval-regression*.yml",
        ".github/workflows/eval-fast.yml")
    baseline_seeded = False
    baseline_note = "not found"
    baseline_obj = root / "tests/eval/fixtures/eval_baseline.json"
    if baseline_obj.exists():
        try:
            b = json.loads(baseline_obj.read_text())
            pr_score = b.get("pr", {}).get("aggregate_score")
            baseline_seeded = pr_score is not None
            baseline_note = (
                "tests/eval/fixtures/eval_baseline.json (seeded)"
                if baseline_seeded
                else "tests/eval/fixtures/eval_baseline.json (aggregate_score=null — unseeded)"
            )
        except (json.JSONDecodeError, OSError):
            baseline_note = "tests/eval/fixtures/eval_baseline.json (parse error)"
    regression_ok = ci_found and baseline_seeded
    checks.append(Check(
        id="workflows.advanced.eval_regression_suite",
        criterion="Is there an automated eval regression suite (CI-integrated, not manual runs, with seeded baseline)?",
        result=regression_ok,
        evidence=f"CI: {ci_path}; baseline: {baseline_note}",
    ))

    level, score = _ladder_level(checks)
    return level, score, checks


def score_multi_agent(root: Path) -> tuple[str, int, list[Check]]:
    checks: list[Check] = []

    # Basic: ≥2 named agents
    agent_files: list[Path] = []
    for agents_dir in ("library/cursor/agents", ".cursor/agents"):
        p = root / agents_dir
        if p.exists():
            agent_files.extend(sorted(p.glob("*.md")))
    has_agents = len(agent_files) >= 2
    agent_rel = [str(a.relative_to(root)) for a in agent_files[:3]]
    checks.append(Check(
        id="multi_agent.basic.named_agents",
        criterion="Is there more than one named agent or persona? (≥2 agent definition files)",
        result=has_agents,
        evidence=(f"{len(agent_files)} agents: {agent_rel}"
                  if agent_files else "not found"),
    ))

    if not has_agents:
        return "none", 0, checks

    # Intermediate: separate system prompts with distinct role identity
    roles: set[str] = set()
    for af in agent_files:
        text = af.read_text(errors="ignore").lower()
        for role in ("planner", "evaluator", "builder", "reviewer", "coder", "tester"):
            if f"you are" in text and role in text:
                roles.add(role)
    has_roles = len(roles) >= 2
    checks.append(Check(
        id="multi_agent.intermediate.role_separation",
        criterion="Are agent roles defined with separate system prompts encoding distinct role identity and output format?",
        result=has_roles,
        evidence=(f"Distinct roles found: {sorted(roles)}"
                  if roles else "distinct role identity not found in agent prompts"),
    ))

    # Intermediate: mechanism limiting agent writes
    guard_found, guard_path = _find(root,
        "library/cursor/hooks/evaluator-guard.sh",
        ".cursor/hooks/evaluator-guard.sh")
    checks.append(Check(
        id="multi_agent.intermediate.write_restriction",
        criterion="Is there any mechanism limiting what each agent can modify?",
        result=guard_found,
        evidence=guard_path,
    ))

    if not _all_pass_level(checks, "intermediate"):
        return "basic", 1, checks

    # Advanced: trust boundary deny hook (evaluator structurally blocked from source)
    trust_ok = False
    trust_evidence = "not found"
    if guard_found:
        guard_text = _read_text(root, guard_path)
        trust_ok = '"deny"' in guard_text or "'deny'" in guard_text or "\"permission\": \"deny\"" in guard_text
        trust_evidence = (
            f"{guard_path} (deny permission confirmed)"
            if trust_ok
            else f"{guard_path} found but no deny permission pattern"
        )
    checks.append(Check(
        id="multi_agent.advanced.trust_boundary",
        criterion="Is there trust boundary enforcement — evaluating agent structurally blocked (deny hook) from modifying source files?",
        result=trust_ok,
        evidence=trust_evidence,
    ))

    # Advanced: programmatic orchestration (SDK-based, not manual /evaluator invocation)
    # chain-evaluator.sh is a phase-advance hook; final evaluator launch is still manual.
    # feat-13 (SDK orchestration) was cancelled. No programmatic orchestration exists.
    chain_found, chain_path = _find(root,
        "library/cursor/hooks/chain-evaluator.sh",
        ".cursor/hooks/chain-evaluator.sh")
    programmatic = False
    if chain_found:
        chain_text = _read_text(root, chain_path)
        # True programmatic = SDK Agent.create() / Agent.prompt() calls, not shell phase-advance
        programmatic = "Agent.create" in chain_text or "Agent.prompt" in chain_text or "cursor_sdk" in chain_text
        orch_evidence = (
            f"{chain_path} (SDK orchestration found)"
            if programmatic
            else f"{chain_path} exists but is phase-advance hook, not SDK-based orchestration"
        )
    else:
        orch_evidence = "not found"
    checks.append(Check(
        id="multi_agent.advanced.programmatic_orchestration",
        criterion="Is orchestration programmatic (SDK-based multi-agent launch, not manual /evaluator invocation)?",
        result=programmatic,
        evidence=orch_evidence,
    ))

    # Advanced: context packages (structured state bundles between agents)
    ctx_found, ctx_path = _find(root,
        "library/cursor/hooks/context-package.py",
        ".cursor/hooks/context-package.py",
        "scripts/context-package.py")
    checks.append(Check(
        id="multi_agent.advanced.context_packages",
        criterion="Are context packages (structured state bundles) passed between agents rather than full history inheritance?",
        result=ctx_found,
        evidence=ctx_path,
    ))

    level, score = _ladder_level(checks)
    return level, score, checks


def score_interaction(root: Path) -> tuple[str, int, list[Check]]:
    checks: list[Check] = []

    # Basic: any user-facing guidance on how to prompt
    guidance_found, guidance_path = _find(root, "AGENTS.md", "README.md", "docs/HARNESS_ESSENCE.md")
    checks.append(Check(
        id="interaction.basic.user_guidance",
        criterion="Is there any user-facing guidance on how to prompt the AI? (README, AGENTS.md, example prompts)",
        result=guidance_found,
        evidence=guidance_path,
    ))

    if not guidance_found:
        return "none", 0, checks

    # Intermediate: prompt coaching rule or skill
    coaching_found, coaching_path = _find(root,
        "library/cursor/rules/prompt_coaching.mdc",
        ".cursor/rules/prompt_coaching.mdc",
        "library/cursor/skills/prompt-coaching/SKILL.md",
        ".cursor/skills/prompt-coaching/SKILL.md")
    checks.append(Check(
        id="interaction.intermediate.prompt_coaching",
        criterion="Is there a prompt coaching rule or skill that detects underspecified inputs?",
        result=coaching_found,
        evidence=coaching_path,
    ))

    # Intermediate: mechanism loading task context before first agent turn
    ctx_hook_found, ctx_hook_path = _find(root,
        "library/cursor/hooks/harness-context.sh",
        ".cursor/hooks/harness-context.sh")
    checks.append(Check(
        id="interaction.intermediate.context_loading",
        criterion="Is there any mechanism that loads current task context before the first agent turn?",
        result=ctx_hook_found,
        evidence=ctx_hook_path,
    ))

    if not _all_pass_level(checks, "intermediate"):
        return "basic", 1, checks

    # Advanced: structured context delivery (sessionStart injecting task + contract + trace)
    structured_ok = False
    structured_evidence = "not found"
    if ctx_hook_found:
        hook_text = _read_text(root, ctx_hook_path)
        structured_ok = "sessionStart" in hook_text and (
            "contract" in hook_text.lower() or "breadcrumb" in hook_text.lower()
        )
        structured_evidence = (
            f"{ctx_hook_path} (sessionStart + contract/breadcrumb injection)"
            if structured_ok
            else f"{ctx_hook_path} found but missing sessionStart or contract injection"
        )
    checks.append(Check(
        id="interaction.advanced.structured_context_delivery",
        criterion="Is structured context delivery implemented — sessionStart hook injecting current task, open contracts, and recent trace?",
        result=structured_ok,
        evidence=structured_evidence,
    ))

    # Advanced: interaction patterns measured across sessions (turns to completion, prompt clarity)
    # Must produce actual metrics with those keys — docstring claims don't count.
    metrics_found, metrics_path = _find(root,
        "scripts/session-metrics.py", "scripts/session_metrics.py")
    interaction_measured = False
    metrics_evidence = "not found"
    if metrics_found:
        metrics_text = _read_text(root, metrics_path)
        # Require the script to define or output the specific keys, not just mention them in docs
        interaction_measured = (
            "turns_to_completion" in metrics_text.replace(" ", "_").replace("-", "_")
            or "prompt_clarity" in metrics_text
        ) and "def " in metrics_text  # must be actual implementation, not just comments
        # Disambiguate: also check the metric is actually returned/printed
        if interaction_measured:
            interaction_measured = (
                "\"turns_to_completion\"" in metrics_text
                or "'turns_to_completion'" in metrics_text
                or "\"prompt_clarity\"" in metrics_text
            )
        metrics_evidence = (
            f"{metrics_path} (turns-to-completion / prompt-clarity output confirmed)"
            if interaction_measured
            else (f"{metrics_path} exists but output keys are task/breadcrumb counts;"
                  " turns_to_completion and prompt_clarity not implemented")
        )
    checks.append(Check(
        id="interaction.advanced.measured_patterns",
        criterion="Are interaction patterns measured across sessions? (prompt clarity, turns to completion)",
        result=interaction_measured,
        evidence=metrics_evidence,
    ))

    # Advanced: prompt versioning with changelog and per-change hypothesis
    changelog_found, changelog_path = _find(root,
        "library/cursor/rules/RULES_CHANGELOG.md",
        ".cursor/rules/RULES_CHANGELOG.md",
        "docs/RULES_CHANGELOG.md")
    versioned_ok = False
    changelog_evidence = "not found"
    if changelog_found:
        changelog_text = _read_text(root, changelog_path)
        versioned_ok = "hypothesis" in changelog_text.lower() and "evidence" in changelog_text.lower()
        changelog_evidence = (
            f"{changelog_path} (Hypothesis + Evidence format confirmed)"
            if versioned_ok
            else f"{changelog_path} exists but missing Hypothesis/Evidence format"
        )
    checks.append(Check(
        id="interaction.advanced.prompt_versioning",
        criterion="Is there prompt versioning with a changelog and per-change hypothesis?",
        result=versioned_ok,
        evidence=changelog_evidence,
    ))

    level, score = _ladder_level(checks)
    return level, score, checks


# ---------------------------------------------------------------------------
# Scorecard assembly and output
# ---------------------------------------------------------------------------

def build_scorecard(root: Path) -> dict:
    dim_results: dict[str, tuple[str, int, list[Check]]] = {
        "configuration": score_configuration(root),
        "workflows": score_workflows(root),
        "multi_agent": score_multi_agent(root),
        "interaction": score_interaction(root),
    }

    levels = [r[0] for r in dim_results.values()]
    if all(l == "advanced" for l in levels):
        overall = "advanced"
    elif all(l in ("intermediate", "advanced") for l in levels):
        overall = "intermediate"
    elif all(l in ("basic", "intermediate", "advanced") for l in levels):
        overall = "basic"
    else:
        overall = "none"

    dimensions = {}
    for dim, (level, score, checks) in dim_results.items():
        dimensions[dim] = {
            "level": level,
            "score": score,
            "checks": [asdict(c) for c in checks],
        }

    return {
        "repo": str(root.resolve()),
        "assessed": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "acam_version": ACAM_VERSION,
        "dimensions": dimensions,
        "summary": {"overall_acam": overall},
    }


def print_markdown(scorecard: dict) -> None:
    print("| Dimension | Level | Key Gap |")
    print("|---|---|---|")
    for dim_name, dim in scorecard["dimensions"].items():
        key_gap = "—"
        for c in dim["checks"]:
            if not c["result"]:
                key_gap = c["criterion"]
                break
        label = dim_name.replace("_", " ").title()
        print(f"| {label} | {dim['level']} | {key_gap} |")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Static ACAM scorer — inspects repo artifacts, no API key required"
    )
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(),
        help="Repo root to score (default: current directory)",
    )
    parser.add_argument(
        "--format", choices=["json", "markdown"], default="json",
        help="Output format (default: json)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.exists():
        print(f"error: --root path does not exist: {root}", file=sys.stderr)
        sys.exit(2)

    scorecard = build_scorecard(root)

    if args.format == "markdown":
        print_markdown(scorecard)
    else:
        print(json.dumps(scorecard, indent=2))


if __name__ == "__main__":
    main()
