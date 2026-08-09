#!/usr/bin/env python3
"""Tier 3: Session scenario runner.

Runs real tasks against a Cursor agent in an isolated temp workspace
(via CursorClient.launch_bridge). Captures transcript + artifacts for
post-hoc judging.

Usage:
    python tests/eval/session_runner.py                           # run all scenarios
    python tests/eval/session_runner.py --filter todo              # matching scenarios
    python tests/eval/session_runner.py --scenario build_cli_tool  # specific scenario
    python tests/eval/session_runner.py --dry-run                  # show plan only
    python tests/eval/session_runner.py --list                     # list available scenarios
    python tests/eval/session_runner.py --timeout 600              # custom timeout (seconds)
    python tests/eval/session_runner.py --long                     # run long scenarios (~10-15 min each)
    python tests/eval/session_runner.py --long --no-timeout        # long scenarios, no timeout cap
    python tests/eval/session_runner.py --ablate-rule adversarial_harness.mdc  # A/B ablation

Ablation mode (--ablate-rule):
    Each scenario runs twice: once with full .cursor/rules/ (control) and once with the
    target rule removed (ablated). Both sessions are judged. Results go to:
      run_dir/ablation/<rule_stem>/sessions/{control,ablated}/<scenario_id>.json
      run_dir/ablation/<rule_stem>/judgments/{control,ablated}/<scenario_id>.json
      run_dir/ablation/<rule_stem>/report.json  (Wilcoxon + Cohen's d summary)
    Priority rules: adversarial_harness.mdc, autonomous_execution.mdc,
                    planning_discipline.mdc

Environment:
    CURSOR_API_KEY    - Required
    CAPTURE_MODEL     - Subject model (default: composer-2.5)
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).parent
SCENARIOS_DIR = EVAL_DIR / "scenarios"
LONG_SCENARIOS_DIR = SCENARIOS_DIR / "long"
EVAL_RESULTS_DIR = EVAL_DIR.parent / "eval_results"
REPO_ROOT = EVAL_DIR.parent.parent
LIBRARY_RULES_DIR = REPO_ROOT / "library" / "cursor" / "rules"
CI_SUITES_PATH = EVAL_DIR / "fixtures" / "ci_suites.json"

DEFAULT_MODEL = "composer-2.5"
DEFAULT_TIMEOUT = 300
LONG_DEFAULT_TIMEOUT = 900

SENSITIVE_ENV_VARS = [
    "CURSOR_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "AWS_SECRET_ACCESS_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
]


class _Timeout(Exception):
    pass


def _strip_sensitive_env() -> dict[str, str]:
    """Remove secrets from os.environ so child processes don't inherit them.

    Returns stashed values for restoration via _restore_sensitive_env().
    The API key is passed explicitly to agents.create(), so the bridge
    process itself doesn't need it — but without this, any server the
    agent starts inside the sandbox exposes secrets via os.environ.
    """
    stashed: dict[str, str] = {}
    for var in SENSITIVE_ENV_VARS:
        val = os.environ.pop(var, None)
        if val is not None:
            stashed[var] = val
    return stashed


def _restore_sensitive_env(stashed: dict[str, str]) -> None:
    """Restore previously stripped environment variables."""
    os.environ.update(stashed)


def _wait_with_timeout(run, timeout_s: int):
    """Wait for a run to complete, raising _Timeout if it exceeds timeout_s.

    If timeout_s <= 0, waits indefinitely (no alarm).
    """
    if timeout_s <= 0:
        return run.wait()

    def _handler(signum, frame):
        raise _Timeout(f"Run exceeded {timeout_s}s timeout")

    prev = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_s)
    try:
        return run.wait()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prev)


def _load_ci_tier(tier: str) -> list[str]:
    """Load scenario id list for a CI tier from ci_suites.json.

    Raises SystemExit with a clear message for unknown tier values (EC1).
    """
    if not CI_SUITES_PATH.exists():
        print(f"Error: ci_suites.json not found at {CI_SUITES_PATH}", file=sys.stderr)
        sys.exit(1)

    import json as _json
    suites = _json.loads(CI_SUITES_PATH.read_text())
    if tier not in suites:
        known = sorted(k for k in suites if not k.startswith("_"))
        print(
            f"Error: unknown --ci-tier '{tier}'. Known tiers: {', '.join(known)}",
            file=sys.stderr,
        )
        sys.exit(1)
    return suites[tier]


def load_scenarios(filter_str: str | None = None, long: bool = False,
                   ci_tier: str | None = None) -> list[dict]:
    """Load scenario definitions from YAML files.

    When ci_tier is set, loads only the scenarios listed in ci_suites.json
    for that tier. The tier may include long scenarios; both directories
    are searched. --filter and --ci-tier are mutually exclusive.
    """
    if ci_tier is not None:
        return _load_ci_tier_scenarios(ci_tier)

    source_dir = LONG_SCENARIOS_DIR if long else SCENARIOS_DIR
    scenarios = []
    for path in sorted(source_dir.glob("*.yaml")):
        scenario = yaml.safe_load(path.read_text())
        scenario["_path"] = str(path)
        scenarios.append(scenario)

    if filter_str:
        # Support comma-separated filters: any token that matches id or name is included
        tokens = [t.strip().lower() for t in filter_str.split(",") if t.strip()]
        scenarios = [
            s for s in scenarios
            if any(
                tok in s.get("id", "").lower() or tok in s.get("name", "").lower()
                for tok in tokens
            )
        ]

    return scenarios


def _load_ci_tier_scenarios(tier: str) -> list[dict]:
    """Load scenarios for a CI tier, searching both standard and long directories."""
    tier_ids = _load_ci_tier(tier)
    id_set = set(tier_ids)

    all_paths = sorted(SCENARIOS_DIR.glob("*.yaml")) + sorted(LONG_SCENARIOS_DIR.glob("*.yaml"))
    by_id: dict[str, dict] = {}
    for path in all_paths:
        try:
            s = yaml.safe_load(path.read_text())
            sid = s.get("id", "")
            if sid in id_set:
                s["_path"] = str(path)
                by_id[sid] = s
        except Exception:
            continue

    missing = id_set - set(by_id)
    if missing:
        print(
            f"Warning: ci-tier '{tier}' references scenario ids not found as YAML files: "
            + ", ".join(sorted(missing)),
            file=sys.stderr,
        )

    return [by_id[sid] for sid in tier_ids if sid in by_id]


def run_scenario(scenario: dict, model: str, api_key: str, timeout: int,
                  *, sandbox: bool = True) -> dict:
    """Run a scenario in an isolated workspace via dedicated bridge."""
    from cursor_sdk import CursorClient, LocalAgentOptions, SandboxOptions

    sys.path.insert(0, str(EVAL_DIR))
    from sandbox import CaptureWorkspace

    scenario_id = scenario["id"]
    start_time = time.time()
    transcript: list[dict] = []

    print(f"\n  Running: {scenario['name']} ({scenario_id})")
    print(f"  Model: {model}, Timeout: {timeout}s")

    status = "complete"
    completed_prompts = 0
    artifacts: dict = {}

    seed_files = scenario.get("seed_files") or {}
    with CaptureWorkspace(prefix=f"eval-{scenario_id}-", seed_files=seed_files) as ws:
        print(f"  Workspace: {ws.path}")

        stashed = _strip_sensitive_env()
        try:
            with CursorClient.launch_bridge(workspace=str(ws.path)) as client:
                with client.agents.create(
                    model=model,
                    api_key=api_key,
                    local=LocalAgentOptions(
                        cwd=str(ws.path),
                        setting_sources=["project"],
                        sandbox_options=SandboxOptions(enabled=sandbox),
                    ),
                ) as agent:
                    completed_prompts, status, transcript = _drive_conversation(
                        agent, scenario, timeout, start_time,
                    )
        except _Timeout as e:
            status = "timeout"
            transcript.append({"role": "system", "content": str(e)})
        except Exception as e:
            status = "error"
            transcript.append({"role": "system", "content": f"Error: {e}"})
        finally:
            _restore_sensitive_env(stashed)

        verify_commands = scenario.get("verify", [])
        artifacts = ws.collect_artifacts(verify_commands or None)

    elapsed = time.time() - start_time
    print(f"  Completed in {elapsed:.0f}s (status: {status})")

    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario["name"],
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(elapsed, 1),
        "timeout_s": timeout,
        "status": status,
        "completed_prompts": completed_prompts,
        "transcript": transcript,
        "artifacts": artifacts,
    }


def _collect_conversation(run) -> list[dict]:
    """Extract the full conversation trace from a completed run.

    Returns a list of step dicts with type, and type-specific fields:
    - assistantMessage: {text}
    - toolCall: {name, args, result, status, ...}
    - thinkingMessage: {text, thinking_duration_ms}
    - shellConversationTurn: {command, working_directory, stdout, stderr, exit_code}
    """
    try:
        raw = run.conversation_json()
        if not raw:
            return []
        turns = json.loads(raw)
        if not isinstance(turns, list):
            return []
    except Exception:
        return []

    steps: list[dict] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        turn_type = turn.get("type", "")
        turn_data = turn.get("turn") or {}

        if turn_type == "agentConversationTurn":
            for step_wrapper in turn_data.get("steps", []):
                step = step_wrapper.get("step", step_wrapper)
                step_type = step.get("type", "")
                msg = step.get("message", {}) or {}

                if step_type == "assistantMessage":
                    steps.append({"type": "assistantMessage", "text": msg.get("text", "")})
                elif step_type == "toolCall":
                    steps.append({"type": "toolCall", **msg})
                elif step_type == "thinkingMessage":
                    steps.append({
                        "type": "thinkingMessage",
                        "text": msg.get("text", ""),
                        "thinking_duration_ms": msg.get("thinkingDurationMs"),
                    })
                else:
                    steps.append({"type": step_type, **msg})

        elif turn_type == "shellConversationTurn":
            cmd = turn_data.get("shellCommand", {}) or {}
            out = turn_data.get("shellOutput", {}) or {}
            steps.append({
                "type": "shellConversationTurn",
                "command": cmd.get("command", ""),
                "working_directory": cmd.get("workingDirectory", ""),
                "stdout": out.get("stdout", ""),
                "stderr": out.get("stderr", ""),
                "exit_code": out.get("exitCode", -1),
            })

    return steps


def _drive_conversation(agent, scenario: dict, timeout: int, start_time: float):
    """Send initial + follow-up prompts, return (completed_prompts, status, transcript)."""
    transcript: list[dict] = []
    status = "complete"
    completed_prompts = 0

    initial = scenario["initial_prompt"]
    print(f"  Sending initial prompt...")
    run = agent.send(initial)
    _wait_with_timeout(run, timeout)

    conversation = _collect_conversation(run)
    tool_calls = [s for s in conversation if s.get("type") == "toolCall"]
    print(f"  Trace: {len(conversation)} steps, {len(tool_calls)} tool calls")

    transcript.append({
        "role": "user",
        "content": initial,
        "response": run.text(),
        "conversation": conversation,
        "elapsed_s": time.time() - start_time,
    })
    completed_prompts += 1

    for i, follow_up in enumerate(scenario.get("follow_up_prompts", [])):
        if timeout > 0:
            remaining = timeout - (time.time() - start_time)
            if remaining <= 0:
                status = "timeout"
                transcript.append({
                    "role": "system",
                    "content": f"Timeout: skipped follow-up {i + 1}",
                })
                break
        else:
            remaining = 0

        print(f"  Sending follow-up {i + 1}...")
        run = agent.send(follow_up)
        _wait_with_timeout(run, int(remaining))

        conversation = _collect_conversation(run)
        tool_calls = [s for s in conversation if s.get("type") == "toolCall"]
        print(f"  Trace: {len(conversation)} steps, {len(tool_calls)} tool calls")

        transcript.append({
            "role": "user",
            "content": follow_up,
            "response": run.text(),
            "conversation": conversation,
            "elapsed_s": time.time() - start_time,
        })
        completed_prompts += 1

    return completed_prompts, status, transcript


def _make_run_dir() -> Path:
    """Create a timestamped run directory for this eval session."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    run_dir = EVAL_RESULTS_DIR / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_session(result: dict, run_dir: Path) -> Path:
    model = result["model"]
    scenario_id = result["scenario_id"]
    out_dir = run_dir / "sessions" / model
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{scenario_id}.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    return path


def _validate_ablate_rule(rule_name: str) -> str:
    """Validate that rule_name exists in library/cursor/rules/. Returns basename.

    Raises SystemExit with a descriptive message listing available rules if not found.
    """
    if not rule_name.endswith(".mdc"):
        rule_name = rule_name + ".mdc"
    rule_path = LIBRARY_RULES_DIR / rule_name
    if not rule_path.exists():
        available = sorted(p.name for p in LIBRARY_RULES_DIR.glob("*.mdc"))
        print(f"Error: Rule not found: {rule_name}", file=sys.stderr)
        print(f"Available rules: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)
    return rule_name


def _save_ablation_session(result: dict, run_dir: Path, rule_stem: str, arm: str) -> Path:
    """Save a session result under ablation/<rule_stem>/sessions/<arm>/."""
    scenario_id = result["scenario_id"]
    out_dir = run_dir / "ablation" / rule_stem / "sessions" / arm
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{scenario_id}.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    return path


def _save_ablation_judgment(judgment: dict, run_dir: Path, rule_stem: str, arm: str) -> Path:
    """Save a judgment under ablation/<rule_stem>/judgments/<arm>/."""
    scenario_id = judgment.get("scenario_id", "unknown")
    out_dir = run_dir / "ablation" / rule_stem / "judgments" / arm
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{scenario_id}.json"
    path.write_text(json.dumps(judgment, indent=2) + "\n")
    return path


def _run_ablation(
    scenarios: list[dict],
    model: str,
    api_key: str,
    run_dir: Path,
    rule_name: str,
    timeout: int,
    sandbox: bool,
) -> None:
    """Run each scenario twice (control + ablated), judge both, write report.json."""
    sys.path.insert(0, str(EVAL_DIR))
    from session_judge import judge_session, load_scenario
    from ablation_report import compute_report, print_summary

    rule_stem = rule_name.removesuffix(".mdc")
    print(f"\nAblation mode: removing '{rule_name}' from ablated workspace")
    print(f"Scenarios: {len(scenarios)}, each runs 2x (control + ablated)")

    for scenario in scenarios:
        scenario_id = scenario["id"]
        scenario_timeout = scenario.get("timeout_s", timeout)
        seed_files = scenario.get("seed_files") or {}
        rubric_data = load_scenario(scenario_id) or {}

        print(f"\n  [{scenario_id}] control run...")
        control_result = run_scenario(
            scenario, model, api_key, scenario_timeout, sandbox=sandbox,
        )
        control_path = _save_ablation_session(control_result, run_dir, rule_stem, "control")
        control_judgment = judge_session(control_result, rubric_data, {"computational", "structural"}, api_key)
        _save_ablation_judgment(control_judgment, run_dir, rule_stem, "control")
        print(f"    control score: {control_judgment['summary']['score']:.2f} — saved {control_path.name}")

        print(f"  [{scenario_id}] ablated run (no {rule_name})...")
        ablated_result = _run_scenario_ablated(
            scenario, model, api_key, scenario_timeout, rule_name, sandbox=sandbox,
        )
        ablated_path = _save_ablation_session(ablated_result, run_dir, rule_stem, "ablated")
        ablated_judgment = judge_session(ablated_result, rubric_data, {"computational", "structural"}, api_key)
        _save_ablation_judgment(ablated_judgment, run_dir, rule_stem, "ablated")
        print(f"    ablated score: {ablated_judgment['summary']['score']:.2f} — saved {ablated_path.name}")

    report = compute_report(run_dir, rule_stem)
    report_path = run_dir / "ablation" / rule_stem / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nReport saved: {report_path}")
    print_summary(report)


def _run_scenario_ablated(
    scenario: dict,
    model: str,
    api_key: str,
    timeout: int,
    rule_name: str,
    *,
    sandbox: bool = True,
) -> dict:
    """Run a scenario with the target rule excluded from the sandbox workspace."""
    from cursor_sdk import CursorClient, LocalAgentOptions, SandboxOptions
    sys.path.insert(0, str(EVAL_DIR))
    from sandbox import CaptureWorkspace

    scenario_id = scenario["id"]
    start_time = time.time()
    transcript: list[dict] = []
    status = "complete"
    completed_prompts = 0

    print(f"  Workspace (ablated): temp dir, rule={rule_name} excluded")

    seed_files = scenario.get("seed_files") or {}
    with CaptureWorkspace(
        prefix=f"eval-ablated-{scenario_id}-",
        seed_files=seed_files,
        excluded_rules={rule_name},
    ) as ws:
        stashed = _strip_sensitive_env()
        try:
            with CursorClient.launch_bridge(workspace=str(ws.path)) as client:
                with client.agents.create(
                    model=model,
                    api_key=api_key,
                    local=LocalAgentOptions(
                        cwd=str(ws.path),
                        setting_sources=["project"],
                        sandbox_options=SandboxOptions(enabled=sandbox),
                    ),
                ) as agent:
                    completed_prompts, status, transcript = _drive_conversation(
                        agent, scenario, timeout, start_time,
                    )
        except _Timeout as e:
            status = "timeout"
            transcript.append({"role": "system", "content": str(e)})
        except Exception as e:
            status = "error"
            transcript.append({"role": "system", "content": f"Error: {e}"})
        finally:
            _restore_sensitive_env(stashed)

        verify_commands = scenario.get("verify", [])
        artifacts = ws.collect_artifacts(verify_commands or None)

    elapsed = time.time() - start_time
    print(f"  Ablated completed in {elapsed:.0f}s (status: {status})")

    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario["name"],
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(elapsed, 1),
        "timeout_s": timeout,
        "status": status,
        "completed_prompts": completed_prompts,
        "transcript": transcript,
        "artifacts": artifacts,
        "ablation": {"rule_removed": rule_name},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run session scenarios (isolated workspace)")
    parser.add_argument("--filter", help="Filter scenarios by id/name")
    parser.add_argument("--scenario", help="Run a specific scenario by id")
    parser.add_argument("--model", default=os.environ.get("CAPTURE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--no-timeout", action="store_true", help="Disable timeout entirely")
    parser.add_argument("--long", action="store_true", help="Run long scenarios from scenarios/long/")
    parser.add_argument("--dry-run", action="store_true", help="Show plan only")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--run-dir", help="Reuse an existing run directory instead of creating a new one")
    parser.add_argument("--no-sandbox", action="store_true", help="Disable agent sandbox (NOT recommended — leaks env vars)")
    parser.add_argument(
        "--ablate-rule",
        metavar="RULE.MDC",
        help=(
            "Ablation mode: run each scenario 2x (control + ablated). "
            "The named rule file is removed from .cursor/rules/ in the ablated workspace. "
            "Priority rules: adversarial_harness.mdc, autonomous_execution.mdc, "
            "planning_discipline.mdc"
        ),
    )
    parser.add_argument(
        "--ci-tier",
        metavar="TIER",
        help=(
            "CI tier to run: 'pr' (11 protocol scenarios) or 'nightly' (31 scenarios). "
            "Loads scenario list from tests/eval/fixtures/ci_suites.json. "
            "Takes precedence over --filter and --long when set."
        ),
    )
    args = parser.parse_args()

    if args.timeout is None:
        args.timeout = LONG_DEFAULT_TIMEOUT if args.long else DEFAULT_TIMEOUT

    # Validate --ablate-rule before loading scenarios or API key
    ablate_rule: str | None = None
    if args.ablate_rule:
        ablate_rule = _validate_ablate_rule(args.ablate_rule)

    api_key = os.environ.get("CURSOR_API_KEY", "")

    ci_tier: str | None = args.ci_tier
    scenarios = load_scenarios(
        filter_str=args.filter or args.scenario,
        long=args.long,
        ci_tier=ci_tier,
    )

    if args.list:
        if ci_tier:
            tier_label = f"ci-tier:{ci_tier}"
        elif args.long:
            tier_label = "long"
        else:
            tier_label = "standard"
        print(f"Available {tier_label} scenarios ({len(scenarios)}):")
        for s in scenarios:
            dur = s.get("estimated_duration", "?")
            diff = s.get("difficulty", "?")
            print(f"  {s['id']:30s} [{diff:6s}] ~{dur:5s}  {s['name']}")
        return 0

    if not scenarios:
        source = "tests/eval/scenarios/long/" if args.long else "tests/eval/scenarios/"
        print(f"No scenarios found. Add YAML files to {source}")
        return 1

    if args.dry_run:
        tier_info = f"ci-tier:{ci_tier}" if ci_tier else ("long" if args.long else "standard")
        print(f"Session run plan: {len(scenarios)} scenario(s) [{tier_info}]")
        print(f"  Model: {args.model}")
        print(f"  Timeout: {args.timeout}s")
        sandbox_label = "DISABLED ⚠️" if args.no_sandbox else "enabled (seatbelt/bubblewrap)"
        print(f"  Sandbox: {sandbox_label}")
        print(f"  Isolation: CursorClient.launch_bridge (temp dir)")
        if ablate_rule:
            print(f"  Ablation rule: {ablate_rule}")
            print(f"  Mode: each scenario runs 2x (control + ablated)")
        for s in scenarios:
            prompts = 1 + len(s.get("follow_up_prompts", []))
            runs = "2x" if ablate_rule else "1x"
            print(f"  - {s['id']}: {s['name']} ({prompts} prompt(s), {runs})")
        return 0

    if not api_key:
        print("Error: CURSOR_API_KEY not set")
        return 1

    run_dir = Path(args.run_dir) if args.run_dir else _make_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)

    if ablate_rule:
        _run_ablation(
            scenarios,
            model=args.model,
            api_key=api_key,
            run_dir=run_dir,
            rule_name=ablate_rule,
            timeout=args.timeout if not args.no_timeout else 0,
            sandbox=not args.no_sandbox,
        )
        return 0

    print(f"Session runner: {len(scenarios)} scenario(s)")
    print(f"  Run dir: {run_dir}")
    results = []

    for scenario in scenarios:
        if args.no_timeout:
            scenario_timeout = 0
        else:
            scenario_timeout = scenario.get("timeout_s", args.timeout)
        result = run_scenario(scenario, args.model, api_key, scenario_timeout,
                              sandbox=not args.no_sandbox)
        path = save_session(result, run_dir)
        print(f"  Saved: {path}")
        results.append(result)

    passed = sum(1 for r in results if r["status"] == "complete")
    print(f"\nCompleted {len(results)} scenario(s): {passed} complete, {len(results) - passed} other")
    print(f"Results: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
