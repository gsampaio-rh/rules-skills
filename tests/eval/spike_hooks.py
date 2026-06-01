#!/usr/bin/env python3
"""Spike: verify which hooks fire in the Cursor SDK bridge.

Sends a simple Write-triggering prompt through a sandboxed workspace that has
contract-gate.sh active (state.json exists, no contract.json).  Then inspects
the workspace for evidence of hook execution.

Usage:
    CURSOR_API_KEY=crsr_... python tests/eval/spike_hooks.py

Expected if preToolUse fires:
    - .cursor/hooks.log contains "contract-gate: DENIED"
    - Agent transcript contains "WRITE BLOCKED"
    - Agent may create .harness/contract.json before writing code

Expected if only sessionStart fires:
    - .cursor/hooks.log contains "harness-context: triggered"
    - breadcrumbs.jsonl has "session_start" entry
    - Agent writes code freely without DENY
"""

import json
import os
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).parent
sys.path.insert(0, str(EVAL_DIR))

from sandbox import CaptureWorkspace


def main() -> int:
    api_key = os.environ.get("CURSOR_API_KEY", "")
    if not api_key:
        print("Error: CURSOR_API_KEY not set")
        return 1

    from cursor_sdk import CursorClient, LocalAgentOptions

    seed_files = {
        ".harness/state.json": json.dumps({
            "project": "hook-spike",
            "tasks": [
                {"id": "f1", "name": "Add hello endpoint", "status": "building", "type": "feature"},
            ],
        }),
    }

    with CaptureWorkspace(prefix="spike-hooks-", seed_files=seed_files) as ws:
        print(f"Workspace: {ws.path}")
        print(f"hooks.json exists: {(ws.path / '.cursor' / 'hooks.json').exists()}")
        print(f"contract-gate.sh exists: {(ws.path / '.cursor' / 'hooks' / 'contract-gate.sh').exists()}")
        print(f"state.json seeded: {(ws.path / '.harness' / 'state.json').exists()}")
        print()

        with CursorClient.launch_bridge(workspace=str(ws.path)) as client:
            with client.agents.create(
                model=os.environ.get("CAPTURE_MODEL", "composer-2.5"),
                api_key=api_key,
                local=LocalAgentOptions(
                    cwd=str(ws.path),
                    setting_sources=["project"],
                ),
            ) as agent:
                print("Sending prompt (should trigger Write)...")
                run = agent.send(
                    "Create a file called hello.py with a single function: "
                    "def hello(): return 'Hello, world!'"
                )
                result = run.wait()
                transcript_text = run.text() or ""

        hooks_log = ws.path / ".cursor" / "hooks.log"
        contract = ws.path / ".harness" / "contract.json"
        breadcrumbs = ws.path / ".harness" / "breadcrumbs.jsonl"
        hello_py = ws.path / "hello.py"

        print("\n=== RESULTS ===")
        print(f"hello.py created:      {hello_py.exists()}")
        print(f"contract.json created: {contract.exists()}")
        print(f"hooks.log exists:      {hooks_log.exists()}")

        if hooks_log.exists():
            log_content = hooks_log.read_text()
            print(f"\n--- hooks.log ---\n{log_content}")
            has_contract_gate = "contract-gate" in log_content
            has_denied = "DENIED" in log_content
            has_session_start = "harness-context" in log_content
            print(f"\ncontract-gate triggered: {has_contract_gate}")
            print(f"DENIED entry:           {has_denied}")
            print(f"sessionStart triggered:  {has_session_start}")
        else:
            has_denied = False
            has_session_start = False
            print("\nNo hooks.log — hooks likely not firing at all")

        write_blocked = "WRITE BLOCKED" in transcript_text
        print(f"\nWRITE BLOCKED in transcript: {write_blocked}")

        if breadcrumbs.exists():
            bc_text = breadcrumbs.read_text()
            has_session_bc = "session_start" in bc_text
            print(f"session_start breadcrumb: {has_session_bc}")
        else:
            has_session_bc = False
            print("No breadcrumbs.jsonl")

        print("\n=== VERDICT ===")
        if has_denied or write_blocked:
            print("preToolUse hooks FIRE -> Phase 2B (tune eval)")
        elif has_session_start or has_session_bc:
            print("sessionStart fires, preToolUse does NOT -> Phase 2C (partial hooks)")
        else:
            print("No hooks fire at all -> Phase 2C (no hook support)")

        print(f"\n--- Transcript excerpt ---\n{transcript_text[:500]}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
