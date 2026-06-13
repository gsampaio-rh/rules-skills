# Vacuous Feature Detection

**Task:** spike-vacuous-feature-detection  
**Status:** complete  
**Date:** 2026-06-13  
**Type:** spike — research + recommendation only, no implementation  
**Deliverable:** recommendation for detecting feature contracts with zero behavioral change at negotiation time

---

## Root Cause

### What happened with feat-role-model-config

`feat-role-model-config` was a task typed as `feature` with a contract negotiated and accepted by the evaluator. At evaluation time, 5/5 acceptance criteria passed:

- **AC1**: `harness-model-routing.json` exists and is valid JSON with correct structure
- **AC2**: `Makefile` contains the sync line for `harness-model-routing.json`
- **AC3**: `AGENTS.md` contains a `Role model routing` section
- **AC4**: `library/cursor/agents/planner.md` and `evaluator.md` **still have `model: inherit`** (explicitly asserting no behavioral change)
- **AC5**: `make sync-local` runs without error and `.cursor/harness-model-routing.json` exists after sync

Every single AC tests file existence, file content, or JSON structure. AC4 explicitly asserts that the key behavioral field — `model: inherit` — was unchanged. The task was accepted as a feature despite delivering no behavioral change to the harness workflow.

The evaluator was not at fault. It tested what the contract specified and reported PASS correctly. The failure occurred at contract negotiation time: the AC set was accepted as legitimate for a `feature`-typed task when it should have been flagged as documentation-and-config structure with no runtime behavioral change. The negotiation accepted a contract where every AC was a `grep`/file-existence check.

### Failure mode definition

**Vacuous feature**: a contract typed as `feature` where every acceptance criterion tests only file structure (existence, content, or JSON parse) — none tests that something in the system works differently before and after the change.

This is distinct from:
- A legitimate `chore` or `docs` task that intentionally delivers only file changes
- A legitimate `feature` where a file structure change IS the behavioral signal (e.g., creating a new config file that downstream code reads for the first time)

Detection must fire at **contract negotiation time** — when the evaluator reviews the proposed ACs and before any implementation is built. Post-build detection is too late: the builder has already delivered a task that may never have needed feature-level verification.

---

## Candidate A: Prompt-Only

**Mechanism**: Add an anti-vacuity rule to `evaluator.md` Mode 1 (Contract Negotiation) instructing the evaluator to reject feature contracts where all ACs are file-existence or content checks with no runtime behavioral assertion.

**Example rule text**:
> If the contract is typed as a feature (task_id prefixed `feat-`) and every acceptance criterion is a `grep`, `test -f`, `python3 -c "open(...)"`, or JSON-parse one-liner with no runtime behavioral command, push back: "All ACs test file structure only. Either add an AC that tests that something works differently after this change, or retype the task as chore."

### Reliability

Medium. An LLM evaluator can semantically recognize the pattern: "these ACs only read files — none of them run the application or test a behavior change." This is a meaningful judgment that static tools cannot make easily. However, LLM compliance with negotiation rules is probabilistic. A context-heavy session may not apply the rule consistently. The evaluator already operates under many instructions, and adding one more increases the risk of selective non-compliance.

### False-positive rate

Medium. Risk cases:
- A config feature where creating a new file IS the behavioral change (e.g., a plugin system that activates when a config file is present). The evaluator must assess whether "file exists" implies behavioral change — and a context-limited session may not have enough knowledge of the downstream system.
- A documentation task intentionally scoped as `feature` because it requires feature-level review. Prompt rule depends on the evaluator correctly interpreting the scoping intent.
- Mitigation: the rule must be scoped to `feat-` prefix contracts only, and must include explicit examples of legitimate exceptions.

### Implementation cost

Very low. 3–5 sentences added to `evaluator.md` Mode 1 negotiation section. No code change, no test update. Can be deployed in minutes.

### Impact on valid contracts

Low if scoped correctly. The risk is that the evaluator over-applies the rule to boundary cases (config-as-behavior, documentation-as-feature). Including a worked example in the rule text (e.g., "harness-model-routing.json existing is config structure, not behavioral change") reduces this risk.

---

## Candidate B: Structural/Heuristic

**Mechanism**: Add a static check to `harness_lint.py` that reads the active `contract.json` and flags feature contracts where all ACs match a syntactic "file-existence only" pattern.

### Detection signal

A feature contract (task_id prefixed `feat-`) is flagged as potentially vacuous when **every** acceptance criterion string matches:

- **Permitted**: `test -f`, `grep -c`, `grep -q`, `grep -n`, `python3 -c "...open(...).read()..."`, `python3 -c "...json.load(open(...))..."`, `ls `, `wc -l`, `cat `
- **Not present**: `make [target]`, `python3 scripts/`, `pytest`, `npm test`, `curl`, application-specific executables, `python3 -c "import subprocess"`, any command that invokes the application under test

The lint rule fires when ALL ACs match the permitted list and NONE contain a runtime executable.

**Trigger pattern** (pseudo-regex):
```
vacuous = all(
    re.match(r'^(test -f|grep|python3 -c ["\'].*open\(|ls |wc -l|cat )', ac.strip())
    for ac in contract['acceptance_criteria']
)
```

### Reliability

High for syntactically clear cases. The pattern matcher deterministically flags `grep -c` and `python3 -c "open(...)"` without LLM involvement. However, boundary cases reduce reliability:

- `make sync-local && test -f .cursor/harness-model-routing.json` contains `make` (a runtime command) but tests only that a file was created — not that behavior changed. The static check would NOT flag this as vacuous because `make` is present, even though the AC is functionally file-existence.
- A behavioral AC written as a long python3 one-liner that internally opens files might be misclassified as file-only.
- The check has a **semantic blindspot**: it can detect syntactic patterns but cannot determine whether a runtime command actually tests behavioral change.

### False-positive rate

Medium-High for boundary cases. The check will NOT fire if any AC contains `make`, `python3 script.py`, or a test runner — even if those commands only create files or verify structure. This means feat-role-model-config itself would NOT have been caught (AC5 contained `make sync-local`). The false-negative rate is significant.

### Implementation cost

Medium. Approximately 30–50 lines in `harness_lint.py` with:
- AC string pattern matching
- Task type detection from `task_id` prefix
- Warning message with remediation guidance
- 5–10 pytest tests for the lint rule (vacuous/not-vacuous/boundary cases)

### Impact on valid contracts

Low (false-positive toward feature contracts is the main risk, not chore/docs contracts, which are exempt by type check). The semantic blindspot means the check is more likely to produce false-negatives than false-positives.

---

## Candidate C: Hybrid

**Mechanism**: The hybrid approach deploys Candidate A (evaluator.md prompt rule) and Candidate B (harness_lint.py static check) together, with divided responsibility.

### What each layer catches independently

**Static layer catches**:
- Contracts where EVERY AC string is syntactically a `grep`, `test -f`, or `python3 -c open(...)` command
- Fast, deterministic, zero LLM cost
- Fires before the evaluator is launched (at `make eval-fast` time)
- Cannot catch: contracts where ACs include runtime commands that test only file side-effects (e.g., `make sync-local && test -f ...`)

**Prompt layer catches**:
- Contracts where ACs include runtime commands but the commands test only file creation/content — not behavioral change
- The evaluator can semantically distinguish "`make sync-local && test -f .cursor/harness-model-routing.json`" (file creation side-effect) from "`make eval-fast && echo PASS`" (behavioral — did the harness validate correctly?)
- Can catch: the exact `feat-role-model-config` pattern where `make sync-local` runs but tests only file existence
- Cannot catch independently: syntactically-obvious grep-only patterns (the static layer is faster and more reliable for those)

**Division of responsibility**: static layer handles the syntactically obvious cases early; prompt layer handles the semantically ambiguous cases during negotiation. Neither layer is redundant — the static layer catches what prompt misses (context-heavy sessions that skip rules), and the prompt layer catches what static misses (runtime commands that test only file side-effects).

### Reliability

Highest of the three candidates. Dual coverage means a vacuous contract must evade both a deterministic pattern check AND a semantic evaluator rule to pass undetected. The `feat-role-model-config` pattern specifically (runtime command testing file side-effects) would have been caught by the prompt layer even if the static layer missed it.

### False-positive rate

Lowest. The static layer fires only on syntactically unambiguous cases; the prompt layer applies contextual judgment. The evaluator in prompt mode is the final gate and has access to task context, which allows it to recognize legitimate config-as-feature patterns.

### Implementation cost

Medium-High (= Candidate A cost + Candidate B cost). Recommended phased deployment:
- Phase 1: Candidate A (prompt rule) — immediate, zero code cost
- Phase 2: Candidate B (harness_lint.py) — after prompt rule has been validated in 3+ real tasks

---

## Comparison

| Dimension | Candidate A (Prompt) | Candidate B (Structural) | Candidate C (Hybrid) |
|---|---|---|---|
| **Reliability** | Medium — LLM-probabilistic | High for syntax patterns, low for semantic boundary cases | Highest — dual coverage |
| **False-positive rate** | Medium — depends on evaluator judgment quality | Medium-High — semantic blindspot on runtime commands | Lowest — dual filter with context awareness |
| **Implementation cost** | Very low — 3–5 sentences in evaluator.md | Medium — ~40 lines + tests in harness_lint.py | Medium-High — both layers |
| **Coverage of feat-role-model-config pattern** | Catches it (semantic: make sync-local tests file only) | Misses it (make command bypasses grep-only filter) | Catches it (prompt layer covers the gap) |
| **False-negative risk** | Low in focused sessions, higher in context-heavy sessions | High for runtime-command-but-file-only ACs | Low |

**Ranking (reliability + false-positive combined)**: C > A > B

**Ranking (implementation cost)**: A > B > C

**Summary**: Candidate B is the weakest on both reliability and false-positive dimensions because it has a fundamental semantic blindspot — runtime commands that produce only file side-effects bypass the filter entirely. The exact failure mode (`feat-role-model-config` with `make sync-local && test -f`) would NOT have been caught by B alone. Between A and C: A is free and significantly better than B; C adds the static backstop that catches context-heavy sessions where A's probabilistic compliance degrades.

---

## Recommendation

**Recommended approach: Hybrid (Candidate C), deployed in two phases.**

### Phase 1 — Prompt rule (immediate)

Add the following rule to `evaluator.md` Mode 1 (Contract Negotiation), under the "What to challenge" section:

> **Vacuity check (feature contracts only)**: If the contract task_id is prefixed `feat-`, verify that at least one acceptance criterion tests a runtime behavioral change — not just that a file exists, a JSON key is present, or a grep finds a string. Commands like `grep -c`, `test -f`, and `python3 -c "open(...).read()"` test file structure only. A command like `make sync-local && test -f .cursor/output.json` tests a file side-effect, not behavioral change. If every AC is a file-interrogation check, REJECT and ask the builder to either add a behavioral AC or retype the task as `chore`.

**Detection signal**: For a `feat-` contract, every AC is file-interrogation only (no runtime behavioral assertion).

**What the check emits**: Evaluator responds with `REJECT` during negotiation, citing the vacuity pattern and requesting one of: (1) a behavioral AC added, or (2) task retyped as `chore`. The negotiation breadcrumb records `type: negotiate, result: null` until the contract is corrected.

**Exempt task types**: `chore`, `spike`, `docs` — vacuity detection applies only to `feat-`-prefixed contracts. A task like `docs-eval-measurement-runbook` with file-existence-only ACs must not be flagged: it is typed as `docs` and delivering file structure is its explicit purpose. Detection scoped to `feature` contracts only.

### Phase 2 — Static lint check (after prompt rule validation)

After the prompt rule has been applied in 3+ real build tasks (validating the signal definition), add a `lint_vacuous_feature_contract` function to `harness_lint.py`:

```python
def lint_vacuous_feature_contract(contract: dict) -> list[tuple[str, str, str]]:
    """Warn when a feat- contract has only file-interrogation ACs."""
    issues = []
    task_id = contract.get("task_id", "")
    if not task_id.startswith("feat-"):
        return issues
    acs = contract.get("acceptance_criteria", [])
    file_only_patterns = re.compile(
        r"^\s*(test -f|grep -[cqn]|python3 -c ['\"].*open\(|ls |wc -l|cat )"
    )
    if acs and all(file_only_patterns.match(ac) for ac in acs):
        issues.append((
            "WARN",
            "lint_vacuous_feature_contract",
            f"Contract {task_id} appears vacuous — all ACs test file existence/content only, "
            "none test runtime behavioral change. Add a behavioral AC or retype as chore."
        ))
    return issues
```

**What the static check emits**: `WARN lint_vacuous_feature_contract` on `make eval-fast`. Warn level (not error) because boundary cases exist — the prompt layer is the hard gate.

**Follow-on implementation task**: Create `feat-vacuous-detection-impl` to implement the Phase 2 harness_lint.py check with the pseudo-code above as spec. Phase 1 prompt rule should be added to `evaluator.md` as a separate small patch (≤5 lines) independent of the Phase 2 implementation task.

### Why not B alone

Candidate B misses the exact failure mode (`feat-role-model-config`): `make sync-local && test -f .cursor/harness-model-routing.json` contains a runtime command and bypasses the grep-only filter. A static check that can be circumvented by the most common false-feature pattern is not reliable enough to be the sole gate.

### Why not A alone

Probabilistic. The evaluator instruction is followed in focused, short sessions but degrades in context-heavy, multi-task sessions. For a safety property (preventing vacuous features from passing), deterministic backstop improves the guarantee even if it catches a subset of cases.

### Scoping note

This recommendation applies only to `feat-`-prefixed contracts. Chore, spike, and docs tasks routinely deliver only file structure changes and must not be flagged. The `docs-eval-measurement-runbook` task (a `chore/docs` type) had only file-existence ACs by design — correctly not flagged under this mechanism.
