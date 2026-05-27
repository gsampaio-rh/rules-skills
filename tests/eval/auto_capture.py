#!/usr/bin/env python3
"""Automated response capture via Cursor SDK.

Sends each test case's prompt to a local Cursor agent and saves the response.
The agent runs against this repo's workspace so .cursor/rules/ are active.

Context injection: Simulates what Cursor hooks inject in interactive sessions.
Each prompt is prepended with:
  1. Harness context (what sessionStart hook would inject)
  2. Routing context (what beforeSubmitPrompt would inject for complex prompts)
This makes SDK captures behave more like actual Cursor interactions.

Usage:
    python tests/eval/auto_capture.py                          # capture all missing responses
    python tests/eval/auto_capture.py --filter security        # only tests matching 'security'
    python tests/eval/auto_capture.py --model auto             # use a specific model
    python tests/eval/auto_capture.py --force                  # re-capture even if response exists
    python tests/eval/auto_capture.py --dry-run                # show what would be captured
    python tests/eval/auto_capture.py --no-context             # skip context injection (raw prompts)

Environment variables:
    CURSOR_API_KEY  - Cursor API key (required)
    CAPTURE_MODEL   - model override (default: composer-2.5)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.yaml"
REPO_ROOT = EVAL_DIR.parent.parent


def load_dataset() -> list[dict]:
    with open(DATASET_PATH) as f:
        return yaml.safe_load(f)


def responses_dir(model: str) -> Path:
    return EVAL_DIR / "responses" / model


def has_response(test_id: str, model: str) -> bool:
    path = responses_dir(model) / f"{test_id}.md"
    if not path.exists():
        return False
    text = path.read_text().strip()
    return bool(text) and not text.startswith("<!-- Response for:")


def save_response(test_id: str, model: str, response: str) -> Path:
    out_dir = responses_dir(model)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{test_id}.md"
    path.write_text(response)
    return path


# ─── Context Injection ────────────────────────────────────────────────────────


def build_session_context() -> str:
    """Simulate what harness-context.sh sessionStart hook would inject."""
    state_path = REPO_ROOT / ".harness" / "state.json"
    contract_path = REPO_ROOT / ".harness" / "contract.json"
    breadcrumbs_path = REPO_ROOT / ".harness" / "breadcrumbs.jsonl"

    parts = []

    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
            project = state.get("project", "unknown")
            features = state.get("features", [])
            total = len(features)
            done = sum(1 for f in features if f.get("status") in ("verified", "committed"))
            building = [f for f in features if f.get("status") == "building"]
            pending = [f for f in features if f.get("status") == "pending"]

            parts.append(f'Harness active for "{project}": {done}/{total} features done.')
            if building:
                b = building[0]
                parts.append(f'Currently building: {b.get("id", "?")} ({b.get("name", "unnamed")}).')
            elif pending:
                p = pending[0]
                parts.append(f'Next pending: {p.get("id", "?")} ({p.get("name", "unnamed")}).')
        except Exception:
            pass

    if contract_path.exists():
        try:
            contract = json.loads(contract_path.read_text())
            feat = contract.get("feature", "unknown")
            phase = contract.get("phase", "unknown")
            verified = contract.get("verified", False)
            parts.append(f'Contract for "{feat}": phase={phase}, verified={verified}.')
        except Exception:
            pass

    if breadcrumbs_path.exists():
        try:
            lines = breadcrumbs_path.read_text().strip().split("\n")
            recent = lines[-3:] if len(lines) >= 3 else lines
            msgs = []
            for line in recent:
                try:
                    entry = json.loads(line.strip())
                    msgs.append(f' [{entry.get("role", "?")}] {entry.get("msg", "?")}')
                except Exception:
                    pass
            if msgs:
                parts.append("Recent breadcrumbs:")
                parts.extend(msgs)
        except Exception:
            pass

    return "\n".join(parts) if parts else ""


def classify_complexity(prompt: str) -> bool:
    """Replicate the harness-gate.sh complexity classification logic.

    Returns True if the prompt would be classified as complex (non-trivial).
    Uses a generous threshold — in real Cursor, the LLM prompt hook refines
    ambiguous cases; here we inject routing for anything clearly multi-feature.
    """
    prompt_lower = prompt.lower()

    if len(prompt) < 40:
        return False

    if "skip harness" in prompt_lower:
        return False

    maintenance_pattern = r"\b(fix|bug|verify|review|check|update|rename|delete|remove|commit|sync|clean|lint|format|typo|patch|hotfix|tweak|adjust|correct)\b"
    if re.search(maintenance_pattern, prompt_lower) and len(prompt) < 120:
        return False

    build_verbs = r"\b(implement|build|create|develop|refactor|migrate|redesign|architect|integrate|overhaul|rewrite|add)\b"
    scope_words = r"\b(feature|module|service|component|system|api|endpoint|database|schema|pipeline|workflow|authentication|authorization|notification|payment|dashboard|analytics|webhook|real-?time|streaming)\b"

    verb_hits = len(re.findall(build_verbs, prompt_lower))
    scope_hits = len(re.findall(scope_words, prompt_lower))

    if verb_hits >= 1 and scope_hits >= 2:
        return True

    multi_feature_signals = [" and ", ", and ", "support ", "with "]
    signal_hits = sum(1 for s in multi_feature_signals if s in prompt_lower)
    return (verb_hits + scope_hits) >= 2 and signal_hits >= 2 and len(prompt) > 80


ROUTING_MESSAGE = (
    "HARNESS ROUTING: This prompt describes non-trivial work. Before implementing "
    "anything, you MUST launch the /planner subagent to decompose this into a spec "
    "and feature list. Do NOT start coding directly. The flow is: (1) launch /planner "
    "with the user's full request, (2) present the spec to the user for confirmation, "
    "(3) then begin contract negotiation for the first feature. If the user says "
    "'skip harness', proceed without the planner."
)


def build_injected_prompt(test_case: dict, inject_context: bool) -> str:
    """Build the full prompt with context injection simulating Cursor hooks.

    In Cursor, the agent sees:
      1. Session context (from sessionStart hook)
      2. Routing message (from beforeSubmitPrompt hook, if complex)
      3. The actual user prompt
      4. Test context (scenario description)

    For test cases with scenario_type=hook_response, the prompt already includes
    the hook message — no additional injection needed.
    """
    prompt = test_case["prompt"]

    if not inject_context:
        return prompt

    if test_case.get("scenario_type") == "hook_response":
        return prompt

    parts = []

    session_ctx = build_session_context()
    if session_ctx:
        parts.append(f"<hooks_context>\n{session_ctx}\n</hooks_context>")

    is_complex = classify_complexity(prompt)
    if is_complex and test_case.get("category") not in ("adversarial",):
        parts.append(f"<system_notification>\n{ROUTING_MESSAGE}\n</system_notification>")

    parts.append(prompt)

    context = test_case.get("context", "")
    if context:
        parts.append(f"\n[Test scenario context: {context.strip()}]")

    return "\n\n".join(parts)


# ─── Capture Logic ────────────────────────────────────────────────────────────


def capture_one(prompt: str, model: str, api_key: str) -> str:
    from cursor_sdk import Agent, AgentOptions, LocalAgentOptions

    result = Agent.prompt(
        prompt,
        AgentOptions(
            api_key=api_key,
            model=model,
            local=LocalAgentOptions(cwd=str(REPO_ROOT)),
        ),
    )

    if result.status == "error":
        raise RuntimeError(f"Agent run failed (id={result.id}): status={result.status}")

    return result.result or ""


def filter_dataset(dataset: list[dict], pattern: str) -> list[dict]:
    f = pattern.lower()
    return [
        t for t in dataset
        if f in t["id"].lower()
        or f in t.get("category", "").lower()
        or any(f in tgt.lower() for tgt in t.get("targets", []))
    ]


def show_status(dataset: list[dict], model: str) -> None:
    captured = sum(1 for t in dataset if has_response(t["id"], model))
    total = len(dataset)
    pct = (captured / total * 100) if total > 0 else 0
    print(f"Captured: {captured}/{total} ({pct:.0f}%) for model '{model}'")


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated response capture via Cursor SDK")
    parser.add_argument("--filter", help="Only capture tests matching this string")
    parser.add_argument("--model", default=os.environ.get("CAPTURE_MODEL", "composer-2.5"),
                        help="Cursor model to use (default: composer-2.5)")
    parser.add_argument("--force", action="store_true",
                        help="Re-capture even if response already exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be captured without running")
    parser.add_argument("--status", action="store_true",
                        help="Show capture progress and exit")
    parser.add_argument("--no-context", action="store_true",
                        help="Skip context injection (raw prompts, like before)")
    args = parser.parse_args()

    api_key = os.environ.get("CURSOR_API_KEY", "")
    if not api_key and not args.dry_run and not args.status:
        print("Error: CURSOR_API_KEY environment variable is required.", file=sys.stderr)
        print("Get your key at: https://cursor.com/dashboard/integrations", file=sys.stderr)
        return 1

    dataset = load_dataset()
    if args.filter:
        dataset = filter_dataset(dataset, args.filter)

    if args.status:
        show_status(dataset, args.model)
        return 0

    to_capture = [
        t for t in dataset
        if args.force or not has_response(t["id"], args.model)
    ]

    if not to_capture:
        print("All test cases already have responses.")
        show_status(dataset, args.model)
        return 0

    inject_context = not args.no_context

    if args.dry_run:
        print(f"Would capture {len(to_capture)} responses with model '{args.model}':")
        print(f"Context injection: {'ON' if inject_context else 'OFF'}\n")
        for t in to_capture:
            status = "exists (--force)" if has_response(t["id"], args.model) else "missing"
            is_hook_response = t.get("scenario_type") == "hook_response"
            will_route = (
                inject_context
                and not is_hook_response
                and classify_complexity(t["prompt"])
                and t.get("category") not in ("adversarial",)
            )
            flag = " [COMPLEX→routing]" if will_route else ""
            if is_hook_response and inject_context:
                flag = " [hook_response→raw]"
            print(f"  {t['id']:50s} [{status}]{flag}")
        return 0

    total = len(to_capture)
    passed = 0
    failed = 0

    print(f"Capturing {total} responses with model '{args.model}'...")
    print(f"Workspace: {REPO_ROOT}")
    print(f"Context injection: {'ON' if inject_context else 'OFF'}\n")

    for i, test_case in enumerate(to_capture, 1):
        test_id = test_case["id"]
        print(f"[{i}/{total}] {test_id}...", end=" ", flush=True)

        full_prompt = build_injected_prompt(test_case, inject_context)

        start = time.time()
        try:
            response = capture_one(full_prompt, args.model, api_key)
            path = save_response(test_id, args.model, response)
            elapsed = time.time() - start
            print(f"ok ({elapsed:.1f}s, {len(response)} chars) -> {path.name}")
            passed += 1
        except Exception as e:
            elapsed = time.time() - start
            print(f"FAILED ({elapsed:.1f}s): {e}")
            failed += 1

    print(f"\nDone: {passed} captured, {failed} failed, {total - passed - failed} skipped")
    show_status(dataset, args.model)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
