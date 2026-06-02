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

DEFAULT_MODEL = "composer-2.5"
DEFAULT_TIMEOUT = 300
LONG_DEFAULT_TIMEOUT = 900


class _Timeout(Exception):
    pass


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


def load_scenarios(filter_str: str | None = None, long: bool = False) -> list[dict]:
    source_dir = LONG_SCENARIOS_DIR if long else SCENARIOS_DIR
    scenarios = []
    for path in sorted(source_dir.glob("*.yaml")):
        scenario = yaml.safe_load(path.read_text())
        scenario["_path"] = str(path)
        scenarios.append(scenario)

    if filter_str:
        f = filter_str.lower()
        scenarios = [
            s for s in scenarios
            if f in s.get("id", "").lower()
            or f in s.get("name", "").lower()
        ]

    return scenarios


def run_scenario(scenario: dict, model: str, api_key: str, timeout: int) -> dict:
    """Run a scenario in an isolated workspace via dedicated bridge."""
    from cursor_sdk import CursorClient, LocalAgentOptions

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

        try:
            with CursorClient.launch_bridge(workspace=str(ws.path)) as client:
                with client.agents.create(
                    model=model,
                    api_key=api_key,
                    local=LocalAgentOptions(
                        cwd=str(ws.path),
                        setting_sources=["project"],
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
    args = parser.parse_args()

    if args.timeout is None:
        args.timeout = LONG_DEFAULT_TIMEOUT if args.long else DEFAULT_TIMEOUT

    api_key = os.environ.get("CURSOR_API_KEY", "")

    scenarios = load_scenarios(args.filter or args.scenario, long=args.long)

    if args.list:
        tier_label = "long" if args.long else "standard"
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
        print(f"Session run plan: {len(scenarios)} scenario(s)")
        print(f"  Model: {args.model}")
        print(f"  Timeout: {args.timeout}s")
        print(f"  Isolation: CursorClient.launch_bridge (temp dir)")
        for s in scenarios:
            prompts = 1 + len(s.get("follow_up_prompts", []))
            print(f"  - {s['id']}: {s['name']} ({prompts} prompt(s))")
        return 0

    if not api_key:
        print("Error: CURSOR_API_KEY not set")
        return 1

    run_dir = _make_run_dir()
    print(f"Session runner: {len(scenarios)} scenario(s)")
    print(f"  Run dir: {run_dir}")
    results = []

    for scenario in scenarios:
        if args.no_timeout:
            scenario_timeout = 0
        else:
            scenario_timeout = scenario.get("timeout_s", args.timeout)
        result = run_scenario(scenario, args.model, api_key, scenario_timeout)
        path = save_session(result, run_dir)
        print(f"  Saved: {path}")
        results.append(result)

    passed = sum(1 for r in results if r["status"] == "complete")
    print(f"\nCompleted {len(results)} scenario(s): {passed} complete, {len(results) - passed} other")
    print(f"Results: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
