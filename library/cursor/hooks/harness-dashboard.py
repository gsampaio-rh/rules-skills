#!/usr/bin/env python3
"""
Read-only Genius Bar session desk for the adversarial harness.

Aggregates real local harness artifacts into a self-contained HTML board
(.harness/dashboard.html by default). Observability only — never invents
metrics. Tokens stay Unavailable unless a real local source appears.

Usage:
    python library/cursor/hooks/harness-dashboard.py
    python library/cursor/hooks/harness-dashboard.py --root . --out .harness/dashboard.html --open
    python library/cursor/hooks/harness-dashboard.py --json
"""

from __future__ import annotations

import argparse
import html
import json
import webbrowser
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BREADCRUMB_HOT = 30
ACTIVITY_LIMIT = 12
HOOKS_LOG_LINES = 20
ARCHIVE_SNIPPET = 5
_ACTIVE = {"pending", "building", "evaluating"}

# Stable section markers — owned jointly with tests/eval/test_harness_dashboard.py
MARKER_NOW = "Now serving"
MARKER_VITALS = "Session vitals"
MARKER_QUEUE = "Queue"
MARKER_CONTRACT = "Contract"
MARKER_ACTIVITY = "Recent activity"
MARKER_FLAGS = "Flags/gates"
MARKER_NO_HARNESS = "No harness active"
MARKER_TOKENS_UNAVAILABLE = "Unavailable"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_paths(root: Path) -> dict[str, Path]:
    harness = root / ".harness"
    archive = harness / ".archive"
    hooks = root / ".cursor" / "hooks"
    return {
        "root": root,
        "harness": harness,
        "state": harness / "state.json",
        "contract": harness / "contract.json",
        "breadcrumbs": harness / "breadcrumbs.jsonl",
        "session_stats": harness / ".session-stats.json",
        "routing": harness / ".routing-pending",
        "archive_jsonl": archive / "archive.jsonl",
        "evals_dir": archive / "evals",
        "evaluator_active": hooks / ".evaluator-active",
        "commit_approved": hooks / ".commit-approved",
        "hooks_log": root / ".cursor" / "hooks.log",
    }


def _load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except OSError:
        return []
    return out


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())
    except OSError:
        return 0


def _flag_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "age_seconds": None, "path": str(path)}
    try:
        mtime = path.stat().st_mtime
        age = max(0, int(_now().timestamp() - mtime))
    except OSError:
        age = None
    return {"present": True, "age_seconds": age, "path": str(path)}


def _fmt_age(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def _active_task(tasks: list[dict]) -> dict | None:
    for t in tasks:
        if t.get("status") in _ACTIVE:
            return {
                "id": t.get("id"),
                "name": t.get("name"),
                "status": t.get("status"),
                "type": t.get("type"),
            }
    return None


def _status_counts(tasks: list[dict]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for t in tasks:
        c[str(t.get("status") or "unknown")] += 1
    return dict(c)


def _breadcrumb_stats(entries: list[dict]) -> dict[str, Any]:
    hot = entries[-BREADCRUMB_HOT:]
    roles = Counter(e.get("role", "unknown") for e in hot)
    types = Counter(e.get("type", "unknown") for e in hot)
    sessions = sum(1 for e in hot if e.get("type") == "session_start")
    eval_pass = sum(
        1
        for e in hot
        if e.get("type") in ("evaluate", "eval") and str(e.get("result", "")).lower() == "pass"
    )
    eval_fail = sum(
        1
        for e in hot
        if e.get("type") in ("evaluate", "eval") and str(e.get("result", "")).lower() == "fail"
    )
    negotiate = sum(1 for e in hot if e.get("type") == "negotiate")
    return {
        "hot_count": len(hot),
        "roles": dict(roles),
        "types": dict(types),
        "session_starts": sessions,
        "eval_pass": eval_pass,
        "eval_fail": eval_fail,
        "negotiate_rounds": negotiate,
        "recent": hot[-ACTIVITY_LIMIT:],
    }


def _latest_eval(evals_dir: Path) -> dict[str, Any] | None:
    if not evals_dir.is_dir():
        return None
    reports = sorted(evals_dir.glob("eval-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not reports:
        return None
    data = _load_json(reports[0])
    if not isinstance(data, dict):
        return {"file": reports[0].name}
    return {
        "file": reports[0].name,
        "overall": data.get("overall") or data.get("result") or data.get("verdict"),
        "recommendation": data.get("recommendation")
        or (data.get("harvest_recommendation") or {}).get("type"),
    }


def _archive_snippet(entries: list[dict]) -> list[dict]:
    interesting = [
        e
        for e in entries
        if e.get("type") in ("task_archived", "archive", "prune") or "archiv" in str(e.get("msg", "")).lower()
    ]
    src = interesting or entries
    return src[-ARCHIVE_SNIPPET:]


def _hooks_log_tail(path: Path, n: int = HOOKS_LOG_LINES) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
        return lines[-n:]
    except OSError:
        return []


def collect_metrics(root: Path) -> dict[str, Any]:
    """Build the stable metrics payload (also used by --json)."""
    paths = _resolve_paths(root)
    harness_dir = paths["harness"]
    generated_at = _iso_now()

    state_raw = _load_json(paths["state"])
    state_error = None
    if paths["state"].exists() and state_raw is None:
        state_error = "unreadable"
    elif not isinstance(state_raw, dict):
        if paths["state"].exists():
            state_error = "invalid"
            state_raw = None

    harness_active = harness_dir.is_dir() and state_raw is not None and state_error is None

    project = None
    vision = None
    schema_version = None
    tasks: list[dict] = []
    if isinstance(state_raw, dict):
        project = state_raw.get("project") or root.name
        vision = state_raw.get("vision")
        schema_version = state_raw.get("schema_version")
        tasks = list(state_raw.get("tasks") or [])
    else:
        project = root.name

    active = _active_task(tasks) if harness_active else None
    if active:
        for t in tasks:
            if t.get("id") == active.get("id"):
                active["scope"] = t.get("scope")
                break

    contract_raw = _load_json(paths["contract"])
    contract: dict[str, Any] | None = None
    if isinstance(contract_raw, dict):
        ac = contract_raw.get("acceptance_criteria") or []
        edges = contract_raw.get("edge_cases") or []
        ac_list = [str(x) for x in ac] if isinstance(ac, list) else []
        edge_list = [str(x) for x in edges] if isinstance(edges, list) else []
        rubrics = contract_raw.get("rubrics") or []
        if not isinstance(rubrics, list):
            rubrics = []
        contract = {
            "task_id": contract_raw.get("task_id"),
            "feature": contract_raw.get("feature"),
            "problem": contract_raw.get("problem"),
            "proposed_solution": contract_raw.get("proposed_solution"),
            "phase": contract_raw.get("phase"),
            "verified": bool(contract_raw.get("verified", False)),
            "acceptance_criteria": ac_list,
            "edge_cases": edge_list,
            "ac_count": len(ac_list),
            "edge_count": len(edge_list),
            "negotiation_rounds": contract_raw.get("negotiation_rounds"),
            "verification_method": contract_raw.get("verification_method") or "",
            "rubrics": [str(r) for r in rubrics],
            "rubric_mode": contract_raw.get("rubric_mode"),
        }

    crumbs = _load_jsonl(paths["breadcrumbs"])
    crumb_stats = _breadcrumb_stats(crumbs)

    stats_raw = _load_json(paths["session_stats"])
    session = {
        "turns": None,
        "source_writes": None,
    }
    if isinstance(stats_raw, dict):
        session["turns"] = stats_raw.get("turns", 0)
        session["source_writes"] = stats_raw.get("source_writes", 0)

    archive_entries = _load_jsonl(paths["archive_jsonl"])
    eval_files = list(paths["evals_dir"].glob("eval-*.json")) if paths["evals_dir"].is_dir() else []
    archive = {
        "line_count": _count_lines(paths["archive_jsonl"]),
        "eval_report_count": len(eval_files),
        "latest_eval": _latest_eval(paths["evals_dir"]),
        "recent": _archive_snippet(archive_entries),
    }

    flags = {
        "routing_pending": _flag_info(paths["routing"]),
        "evaluator_active": _flag_info(paths["evaluator_active"]),
        "commit_approved": _flag_info(paths["commit_approved"]),
    }

    # Tokens: Cursor does not reliably expose token counts into .harness/ today.
    # Do not invent numbers — honest empty state only.
    tokens = {"available": False, "value": None, "label": MARKER_TOKENS_UNAVAILABLE}

    return {
        "generated_at": generated_at,
        "harness_active": harness_active,
        "state_error": state_error,
        "project": project,
        "vision": vision,
        "schema_version": schema_version,
        "task": active,
        "tasks": [
            {
                "id": t.get("id"),
                "name": t.get("name"),
                "status": t.get("status"),
                "type": t.get("type"),
                "scope": t.get("scope"),
            }
            for t in tasks[:5]
        ],
        "status_counts": _status_counts(tasks),
        "contract": contract,
        "session": session,
        "breadcrumbs": crumb_stats,
        "archive": archive,
        "flags": flags,
        "tokens": tokens,
        "hooks_log_tail": _hooks_log_tail(paths["hooks_log"]),
        "empty_message": None if harness_active else MARKER_NO_HARNESS,
    }


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _chip(text: str, kind: str = "") -> str:
    cls = f"chip chip-{kind}" if kind else "chip"
    return f'<span class="{cls}">{_esc(text)}</span>'


def _vital(label: str, value: Any) -> str:
    display = "—" if value is None else value
    return (
        f'<div class="vital">'
        f'<span class="vital-value">{_esc(display)}</span>'
        f'<span class="vital-label">{_esc(label)}</span>'
        f"</div>"
    )


def _ol(items: list[str], css_class: str = "detail-list") -> str:
    if not items:
        return '<p class="muted">None</p>'
    lis = "".join(f"<li>{_esc(item)}</li>" for item in items)
    return f'<ol class="{css_class}">{lis}</ol>'


def render_html(metrics: dict[str, Any]) -> str:
    project = metrics.get("project") or "harness"
    vision = metrics.get("vision")
    generated = metrics.get("generated_at") or ""
    schema_version = metrics.get("schema_version")
    status_counts = metrics.get("status_counts") or {}
    active = metrics.get("task")
    contract = metrics.get("contract")
    session = metrics.get("session") or {}
    crumbs = metrics.get("breadcrumbs") or {}
    archive = metrics.get("archive") or {}
    flags = metrics.get("flags") or {}
    tasks = metrics.get("tasks") or []
    tokens = metrics.get("tokens") or {}
    empty = metrics.get("empty_message")
    state_error = metrics.get("state_error")

    phase = (contract or {}).get("phase") if contract else None
    verified = (contract or {}).get("verified") if contract else None

    if empty:
        serving_body = f'<p class="empty-state">{_esc(empty)}</p>'
        if state_error:
            serving_body += f'<p class="muted">state.json: {_esc(state_error)}</p>'
    elif active:
        scope = active.get("scope")
        scope_html = (
            f'<p class="scope">{_esc(scope)}</p>' if scope else ""
        )
        serving_body = (
            f'<p class="serving-id">{_esc(active.get("id"))}</p>'
            f'<p class="serving-name">{_esc(active.get("name") or "")}</p>'
            f'<div class="chip-row">'
            f'{_chip(str(active.get("type") or "task"), "muted")}'
            f'{_chip(str(active.get("status") or "?"), "status")}'
            f'{_chip(str(phase or "no contract"), "phase")}'
            f'{_chip("verified" if verified else "unverified", "ok" if verified else "warn")}'
            f"</div>"
            f"{scope_html}"
        )
    else:
        serving_body = (
            '<p class="empty-state">No active task</p>'
            '<p class="muted">Queue has no pending / building / evaluating item</p>'
        )

    vitals = "".join(
        [
            _vital("turns", session.get("turns")),
            _vital("source_writes", session.get("source_writes")),
            _vital("breadcrumbs", crumbs.get("hot_count", 0)),
            _vital("archive", archive.get("line_count", 0)),
            _vital("eval reports", archive.get("eval_report_count", 0)),
            _vital("Tokens", tokens.get("label", MARKER_TOKENS_UNAVAILABLE)),
        ]
    )

    counts_bits = " · ".join(
        f"{k} {v}" for k, v in sorted(status_counts.items()) if v
    )
    state_meta = (
        f'<div class="meta-row state-meta">'
        f'<span>schema v{_esc(schema_version if schema_version is not None else "—")}</span>'
        f'<span>{_esc(len(tasks))} tasks</span>'
        f'<span>{_esc(counts_bits or "no status counts")}</span>'
        f"</div>"
    )

    queue_rows = []
    for t in tasks:
        scope = t.get("scope")
        scope_block = (
            f'<details class="scope-details"><summary>Scope</summary>'
            f'<p class="scope">{_esc(scope)}</p></details>'
            if scope
            else ""
        )
        queue_rows.append(
            "<li>"
            f'<div class="q-main">'
            f'<span class="q-id">{_esc(t.get("id"))}</span>'
            f'<span class="q-name">{_esc(t.get("name"))}</span>'
            f'{_chip(str(t.get("type") or "?"), "muted")}'
            f'{_chip(str(t.get("status") or "?"), "status")}'
            f"</div>"
            f"{scope_block}"
            "</li>"
        )
    queue_html = state_meta + (
        f'<ol class="queue">{"".join(queue_rows)}</ol>'
        if queue_rows
        else '<p class="muted">No tasks in state</p>'
    )

    if contract:
        ac_items = list(contract.get("acceptance_criteria") or [])
        edge_items = list(contract.get("edge_cases") or [])
        rubrics = list(contract.get("rubrics") or [])
        rubric_mode = contract.get("rubric_mode")
        problem = contract.get("problem")
        solution = contract.get("proposed_solution")
        vm = contract.get("verification_method") or ""

        prose = ""
        if problem:
            prose += (
                f'<div class="prose-block"><h3>Problem</h3>'
                f'<p>{_esc(problem)}</p></div>'
            )
        if solution:
            prose += (
                f'<div class="prose-block"><h3>Proposed solution</h3>'
                f'<p>{_esc(solution)}</p></div>'
            )

        rubrics_html = ""
        if rubrics or rubric_mode:
            chips = "".join(_chip(r, "muted") for r in rubrics)
            mode = _chip(f"mode:{rubric_mode}", "phase") if rubric_mode else ""
            rubrics_html = f'<div class="chip-row rubrics-row">{chips}{mode}</div>'

        rounds = contract.get("negotiation_rounds")
        rounds_label = f"rounds {rounds}" if rounds is not None else "rounds —"
        vm_text = _esc(vm) if vm else "—"

        contract_html = (
            f'<p class="serving-id">{_esc(contract.get("task_id") or "—")}</p>'
            f'<p class="contract-feature">{_esc(contract.get("feature") or "—")}</p>'
            f'<div class="chip-row">'
            f'{_chip(str(phase or "?"), "phase")}'
            f'{_chip("verified" if verified else "unverified", "ok" if verified else "warn")}'
            f'{_chip(rounds_label, "muted")}'
            f"</div>"
            f"{prose}"
            f'<div class="contract-lists">'
            f'<div><h3>Acceptance criteria ({_esc(len(ac_items))})</h3>{_ol(ac_items)}</div>'
            f'<div><h3>Edge cases ({_esc(len(edge_items))})</h3>{_ol(edge_items)}</div>'
            f"</div>"
            f"{rubrics_html}"
            f'<div class="prose-block"><h3>Verification</h3>'
            f'<p class="vm">{vm_text}</p></div>'
        )
    else:
        contract_html = '<p class="muted">No active contract</p>'

    activity_items = []
    for e in crumbs.get("recent") or []:
        activity_items.append(
            "<li>"
            f'<time>{_esc(e.get("ts") or "")}</time>'
            f'<span class="role">{_esc(e.get("role") or "")}</span>'
            f'<span class="type">{_esc(e.get("type") or "")}</span>'
            f'<span class="msg">{_esc(e.get("msg") or "")}</span>'
            "</li>"
        )
    activity_html = (
        f'<ol class="timeline">{"".join(activity_items)}</ol>'
        if activity_items
        else '<p class="muted">No breadcrumbs in hot window</p>'
    )

    def flag_row(key: str, label: str) -> str:
        info = flags.get(key) or {}
        present = bool(info.get("present"))
        age = _fmt_age(info.get("age_seconds"))
        state = "present" if present else "absent"
        return (
            f'<li><span class="flag-name">{_esc(label)}</span>'
            f'{_chip(state, "ok" if present else "muted")}'
            f'<span class="flag-age">{_esc(age if present else "—")}</span></li>'
        )

    flags_html = (
        "<ul class=\"flags\">"
        + flag_row("routing_pending", "routing-pending")
        + flag_row("evaluator_active", "evaluator-active")
        + flag_row("commit_approved", "commit-approved")
        + "</ul>"
    )

    vision_html = f'<p class="vision">{_esc(vision)}</p>' if vision else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(project)} · Session desk</title>
<style>
:root {{
  --bg0: #e8eaee;
  --bg1: #f5f6f8;
  --ink: #1d1d1f;
  --ink2: #6e6e73;
  --line: rgba(0,0,0,0.08);
  --accent: #0071e3;
  --ok: #1f7a4d;
  --warn: #9a6700;
  --surface: rgba(255,255,255,0.72);
  --shadow: 0 1px 0 rgba(255,255,255,0.7) inset, 0 18px 40px rgba(15,23,42,0.06);
  --font-display: "Avenir Next", "Segoe UI", Candara, "Century Gothic", sans-serif;
  --font-body: "New York", "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  --font-mono: "SF Mono", "Menlo", "Consolas", monospace;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; min-height: 100%; }}
body {{
  color: var(--ink);
  font-family: var(--font-body);
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(255,255,255,0.95), transparent 55%),
    radial-gradient(900px 500px at 90% 0%, rgba(180,190,205,0.35), transparent 50%),
    linear-gradient(180deg, var(--bg1), var(--bg0));
  line-height: 1.45;
}}
.desk {{
  width: min(720px, calc(100% - 2rem));
  margin: 0 auto;
  padding: 2.5rem 0 3rem;
}}
header.brand {{
  margin-bottom: 2rem;
  animation: rise 0.55s ease both;
}}
.brand-kicker {{
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ink2);
  margin: 0 0 0.4rem;
}}
.brand-title {{
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(2.2rem, 5vw, 3rem);
  letter-spacing: -0.03em;
  margin: 0;
  line-height: 1.05;
}}
.brand-sub {{
  font-family: var(--font-display);
  color: var(--ink2);
  margin: 0.55rem 0 0;
  font-size: 0.95rem;
}}
.vision {{
  margin: 0.85rem 0 0;
  color: var(--ink2);
  max-width: 38rem;
}}
section {{
  background: var(--surface);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: var(--shadow);
  padding: 1.25rem 1.35rem 1.35rem;
  margin: 0 0 0.9rem;
  animation: rise 0.6s ease both;
}}
section:nth-of-type(2) {{ animation-delay: 0.05s; }}
section:nth-of-type(3) {{ animation-delay: 0.1s; }}
section:nth-of-type(4) {{ animation-delay: 0.14s; }}
section:nth-of-type(5) {{ animation-delay: 0.18s; }}
section:nth-of-type(6) {{ animation-delay: 0.22s; }}
section:nth-of-type(7) {{ animation-delay: 0.26s; }}
h2 {{
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink2);
  margin: 0 0 0.85rem;
  font-weight: 600;
}}
.serving-id {{
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--accent);
  margin: 0 0 0.25rem;
}}
.serving-name {{
  font-family: var(--font-display);
  font-size: 1.45rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 0 0 0.75rem;
}}
.chip-row, .meta-row {{ display: flex; flex-wrap: wrap; gap: 0.45rem; }}
.chip {{
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  padding: 0.28rem 0.55rem;
  border-radius: 999px;
  background: rgba(0,0,0,0.05);
  color: var(--ink);
}}
.chip-phase {{ background: rgba(0,113,227,0.12); color: #024ea4; }}
.chip-ok {{ background: rgba(31,122,77,0.12); color: var(--ok); }}
.chip-warn {{ background: rgba(154,103,0,0.14); color: var(--warn); }}
.chip-muted {{ background: rgba(0,0,0,0.04); color: var(--ink2); }}
.vitals {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem 0.5rem;
}}
.vital {{ display: flex; flex-direction: column; gap: 0.15rem; }}
.vital-value {{
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}}
.vital-label {{
  font-family: var(--font-display);
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink2);
}}
.queue, .timeline, .flags {{
  list-style: none;
  margin: 0;
  padding: 0;
}}
.queue li {{
  display: block;
  padding: 0.65rem 0;
  border-top: 1px solid var(--line);
  font-family: var(--font-display);
  font-size: 0.92rem;
}}
.queue li:first-child {{ border-top: 0; padding-top: 0; }}
.q-main {{
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem 0.65rem;
  align-items: center;
}}
.flags li {{
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 0.65rem;
  align-items: center;
  padding: 0.45rem 0;
  border-top: 1px solid var(--line);
  font-family: var(--font-display);
  font-size: 0.92rem;
}}
.flags li:first-child {{ border-top: 0; padding-top: 0; }}
.q-id, .flag-name {{ font-family: var(--font-mono); font-size: 0.78rem; color: var(--ink2); }}
.q-name {{ min-width: 0; flex: 1 1 10rem; }}
.flag-age {{ font-family: var(--font-mono); font-size: 0.75rem; color: var(--ink2); min-width: 2.5rem; text-align: right; }}
.scope {{
  margin: 0.55rem 0 0;
  color: var(--ink2);
  font-family: var(--font-display);
  font-size: 0.88rem;
  line-height: 1.45;
  white-space: pre-wrap;
}}
.scope-details {{
  margin-top: 0.4rem;
}}
.scope-details summary {{
  cursor: pointer;
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink2);
  user-select: none;
}}
.scope-details[open] summary {{ margin-bottom: 0.25rem; }}
.state-meta {{ margin-bottom: 0.75rem; }}
.contract-feature {{
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 0.6rem;
}}
.meta-row span {{
  font-family: var(--font-display);
  font-size: 0.8rem;
  color: var(--ink2);
  padding-right: 0.75rem;
}}
.prose-block {{
  margin-top: 0.95rem;
}}
.prose-block h3, .contract-lists h3 {{
  font-family: var(--font-display);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink2);
  margin: 0 0 0.4rem;
  font-weight: 600;
}}
.prose-block p {{
  margin: 0;
  font-family: var(--font-display);
  font-size: 0.92rem;
  line-height: 1.45;
  color: var(--ink);
}}
.contract-lists {{
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  margin-top: 1rem;
}}
.detail-list {{
  margin: 0;
  padding-left: 1.15rem;
  font-family: var(--font-display);
  font-size: 0.88rem;
  line-height: 1.45;
  color: var(--ink);
}}
.detail-list li {{ margin: 0.35rem 0; }}
.rubrics-row {{ margin-top: 0.9rem; }}
.vm {{ margin: 0; font-size: 0.9rem; white-space: pre-wrap; word-break: break-word; }}
.timeline li {{
  display: grid;
  grid-template-columns: 9.5rem 5.5rem 5.5rem 1fr;
  gap: 0.5rem;
  padding: 0.4rem 0;
  border-top: 1px solid var(--line);
  font-size: 0.82rem;
}}
.timeline li:first-child {{ border-top: 0; padding-top: 0; }}
.timeline time, .timeline .role, .timeline .type {{
  font-family: var(--font-mono);
  color: var(--ink2);
  font-size: 0.72rem;
}}
.timeline .msg {{ font-family: var(--font-display); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.empty-state {{
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 600;
  margin: 0;
}}
.muted {{ color: var(--ink2); margin: 0.4rem 0 0; font-family: var(--font-display); font-size: 0.88rem; }}
footer {{
  margin-top: 1.4rem;
  color: var(--ink2);
  font-family: var(--font-display);
  font-size: 0.75rem;
  line-height: 1.5;
  animation: fade 0.8s ease both 0.3s;
}}
footer code {{ font-family: var(--font-mono); font-size: 0.72rem; }}
@keyframes rise {{
  from {{ opacity: 0; transform: translateY(8px); }}
  to {{ opacity: 1; transform: none; }}
}}
@keyframes fade {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}
@media (max-width: 640px) {{
  .desk {{ width: calc(100% - 1.25rem); padding-top: 1.5rem; }}
  .vitals {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .timeline li {{ grid-template-columns: 1fr 1fr; }}
  .timeline .msg {{ grid-column: 1 / -1; white-space: normal; }}
}}
</style>
</head>
<body>
<main class="desk">
  <header class="brand">
    <p class="brand-kicker">Harness · Session desk</p>
    <h1 class="brand-title">{_esc(project)}</h1>
    <p class="brand-sub">Generated {_esc(generated)}</p>
    {vision_html}
  </header>

  <section aria-labelledby="now-serving">
    <h2 id="now-serving">{MARKER_NOW}</h2>
    {serving_body}
  </section>

  <section aria-labelledby="session-vitals">
    <h2 id="session-vitals">{MARKER_VITALS}</h2>
    <div class="vitals">{vitals}</div>
  </section>

  <section aria-labelledby="queue">
    <h2 id="queue">{MARKER_QUEUE}</h2>
    {queue_html}
  </section>

  <section aria-labelledby="contract">
    <h2 id="contract">{MARKER_CONTRACT}</h2>
    {contract_html}
  </section>

  <section aria-labelledby="recent-activity">
    <h2 id="recent-activity">{MARKER_ACTIVITY}</h2>
    {activity_html}
  </section>

  <section aria-labelledby="flags-gates">
    <h2 id="flags-gates">{MARKER_FLAGS}</h2>
    {flags_html}
  </section>

  <footer>
    <p>Forensic archive is not injected into prompts. Board path: <code>.harness/dashboard.html</code></p>
    <p><!-- Tokens: Cursor does not reliably expose token counts into .harness/ today; tile stays Unavailable unless a real local source exists. --></p>
  </footer>
</main>
<script>
document.documentElement.dataset.ready = "1";
</script>
</body>
</html>
"""


def write_dashboard(root: Path, out: Path, open_browser: bool = False) -> dict[str, Any]:
    metrics = collect_metrics(root)
    html_text = render_html(metrics)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_text, encoding="utf-8")
    if open_browser:
        webbrowser.open(out.resolve().as_uri())
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate harness session desk HTML")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repo root")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output HTML path (default: <root>/.harness/dashboard.html)",
    )
    parser.add_argument("--open", action="store_true", help="Open the HTML in a browser")
    parser.add_argument("--json", action="store_true", help="Print metrics JSON to stdout")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    out = (args.out if args.out is not None else root / ".harness" / "dashboard.html").resolve()

    try:
        metrics = write_dashboard(root, out, open_browser=args.open)
    except Exception as exc:  # fail soft
        # Still try to emit a minimal board
        metrics = {
            "generated_at": _iso_now(),
            "harness_active": False,
            "state_error": "error",
            "project": root.name,
            "vision": None,
            "schema_version": None,
            "task": None,
            "tasks": [],
            "status_counts": {},
            "contract": None,
            "session": {"turns": None, "source_writes": None},
            "breadcrumbs": {
                "hot_count": 0,
                "roles": {},
                "types": {},
                "session_starts": 0,
                "eval_pass": 0,
                "eval_fail": 0,
                "negotiate_rounds": 0,
                "recent": [],
            },
            "archive": {
                "line_count": 0,
                "eval_report_count": 0,
                "latest_eval": None,
                "recent": [],
            },
            "flags": {
                "routing_pending": {"present": False, "age_seconds": None},
                "evaluator_active": {"present": False, "age_seconds": None},
                "commit_approved": {"present": False, "age_seconds": None},
            },
            "tokens": {"available": False, "value": None, "label": MARKER_TOKENS_UNAVAILABLE},
            "hooks_log_tail": [],
            "empty_message": MARKER_NO_HARNESS,
            "error": str(exc),
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_html(metrics), encoding="utf-8")

    if args.json:
        # Stable public keys for tests + consumers
        payload = {
            "task": metrics.get("task"),
            "contract": metrics.get("contract"),
            "session": metrics.get("session"),
            "breadcrumbs": metrics.get("breadcrumbs"),
            "archive": metrics.get("archive"),
            "flags": metrics.get("flags"),
            "project": metrics.get("project"),
            "vision": metrics.get("vision"),
            "tokens": metrics.get("tokens"),
            "harness_active": metrics.get("harness_active"),
            "generated_at": metrics.get("generated_at"),
            "out": str(out),
        }
        print(json.dumps(payload, indent=2, default=str))
    else:
        # Single-line path for `make harness-dashboard`
        try:
            rel = out.relative_to(Path.cwd().resolve())
            print(rel.as_posix())
        except ValueError:
            print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
