"""Hybrid evaluator: structural pattern matching (Tier 1) + LLM fallback (Tier 2).

Tier 1 uses regex/structural checks for criteria that can be assessed deterministically.
Tier 2 defers to the LLM judge (judge.py) for behavioral/intent criteria.
Tier 3 marks criteria as unscored when no LLM is available and structural checks are
inconclusive.

This replaces the crude keyword-only approach in local_judge.py with precise patterns.
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

EVAL_DIR = Path(__file__).parent


@dataclass
class StructuralResult:
    passed: bool
    confident: bool
    reason: str


def llm_available() -> bool:
    return bool(
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("CURSOR_API_KEY")
        or os.environ.get("EVAL_API_KEY")
    )


# ─── Structural Checks (Tier 1) ──────────────────────────────────────────────


def check_coaching_tip(response: str) -> StructuralResult:
    """Check for properly formatted coaching tip."""
    pattern = r'>\s*\*\*Tip:\*\*'
    if re.search(pattern, response):
        return StructuralResult(passed=True, confident=True, reason="Found formatted coaching tip (> **Tip:**)")
    if "tip:" in response.lower() and "**" in response:
        return StructuralResult(passed=True, confident=True, reason="Found coaching tip variant")
    return StructuralResult(passed=False, confident=False, reason="No coaching tip format detected")


def check_todowrite(response: str) -> StructuralResult:
    """Check for TodoWrite usage or structured task planning."""
    resp_lower = response.lower()
    if "todowrite" in resp_lower:
        return StructuralResult(passed=True, confident=True, reason="Explicit TodoWrite reference")
    numbered_steps = re.findall(r'^\s*\d+[\.\)]\s+\S', response, re.MULTILINE)
    if len(numbered_steps) >= 3:
        return StructuralResult(passed=True, confident=True, reason=f"Found {len(numbered_steps)} numbered steps (task plan)")
    if any(p in resp_lower for p in ["task list", "todo list", "step 1", "in_progress", "pending"]):
        return StructuralResult(passed=True, confident=True, reason="Found task planning language")
    return StructuralResult(passed=False, confident=False, reason="No task planning detected")


def check_breadcrumbs(response: str) -> StructuralResult:
    """Check for breadcrumb references."""
    resp_lower = response.lower()
    if "breadcrumbs.jsonl" in resp_lower:
        return StructuralResult(passed=True, confident=True, reason="Explicit breadcrumbs.jsonl reference")
    if "breadcrumb" in resp_lower:
        return StructuralResult(passed=True, confident=True, reason="Breadcrumb mention")
    json_pattern = r'\{"ts".*"role".*"msg"'
    if re.search(json_pattern, response):
        return StructuralResult(passed=True, confident=True, reason="Found breadcrumb JSON shape")
    return StructuralResult(passed=False, confident=False, reason="No breadcrumbs detected")


def check_planner_routing(response: str) -> StructuralResult:
    """Check for planner/planning references."""
    resp_lower = response.lower()
    planner_signals = ["planner", "/planner", "spec.md", "state.json", "launch.*plan", "plan first"]
    for signal in planner_signals:
        if re.search(signal, resp_lower):
            return StructuralResult(passed=True, confident=True, reason=f"Found planner signal: {signal}")
    if any(p in resp_lower for p in ["planning phase", "decompose", "feature list"]):
        return StructuralResult(passed=True, confident=True, reason="Found planning language")
    return StructuralResult(passed=False, confident=False, reason="No planner routing detected")


def check_contract_fields(response: str) -> StructuralResult:
    """Check for contract JSON fields in the response."""
    contract_fields = ["acceptance_criteria", "edge_cases", "verification_method", "feature_id", "phase"]
    found = [f for f in contract_fields if f in response.lower()]
    if len(found) >= 3:
        return StructuralResult(passed=True, confident=True, reason=f"Found contract fields: {found}")
    if len(found) >= 1:
        return StructuralResult(passed=True, confident=False, reason=f"Partial contract fields: {found}")
    if "contract.json" in response.lower():
        return StructuralResult(passed=True, confident=True, reason="Contract.json reference")
    return StructuralResult(passed=False, confident=True, reason="No contract fields found")


def check_type_hints(response: str) -> StructuralResult:
    """Check for Python type hints."""
    type_patterns = [r'->\s*\w', r':\s*(str|int|float|bool|list|dict|None|Optional|tuple)', r'def\s+\w+\([^)]*:\s*\w+']
    hits = sum(1 for p in type_patterns if re.search(p, response))
    if hits >= 2:
        return StructuralResult(passed=True, confident=True, reason=f"Found {hits} type hint patterns")
    if hits == 1:
        return StructuralResult(passed=True, confident=False, reason="Found 1 type hint pattern")
    return StructuralResult(passed=False, confident=False, reason="No type hints detected")


def check_function_splitting(response: str) -> StructuralResult:
    """Check for multiple function definitions (code was split)."""
    func_count = len(re.findall(r'\bdef\s+\w+', response))
    if func_count >= 3:
        return StructuralResult(passed=True, confident=True, reason=f"Found {func_count} function definitions")
    if func_count >= 2:
        return StructuralResult(passed=True, confident=False, reason=f"Found {func_count} functions")
    return StructuralResult(passed=False, confident=False, reason=f"Only {func_count} function(s)")


def check_verification_step(response: str) -> StructuralResult:
    """Check for verification commands (test, lint, build)."""
    resp_lower = response.lower()
    verification_cmds = ["pytest", "npm test", "make test", "ruff", "eslint", "mypy", "tsc", "npm run build", "python -c"]
    found = [v for v in verification_cmds if v in resp_lower]
    if found:
        return StructuralResult(passed=True, confident=True, reason=f"Found verification: {found}")
    if any(p in resp_lower for p in ["run the tests", "run lint", "verify", "check passes"]):
        return StructuralResult(passed=True, confident=False, reason="Found verification intent")
    return StructuralResult(passed=False, confident=False, reason="No verification detected")


def check_questions_asked(response: str) -> StructuralResult:
    """Check if the response asks clarifying questions."""
    question_marks = response.count("?")
    if question_marks >= 2:
        return StructuralResult(passed=True, confident=True, reason=f"Found {question_marks} questions")
    if question_marks == 1:
        return StructuralResult(passed=True, confident=False, reason="Found 1 question")
    return StructuralResult(passed=False, confident=True, reason="No questions asked")


def check_pushback(response: str) -> StructuralResult:
    """Check if the agent pushed back or suggested alternatives."""
    resp_lower = response.lower()
    pushback_signals = ["however", "instead", "alternatively", "suggest", "recommend",
                        "better approach", "consider", "trade-off", "risk", "concern"]
    found = [s for s in pushback_signals if s in resp_lower]
    if len(found) >= 2:
        return StructuralResult(passed=True, confident=True, reason=f"Found pushback: {found}")
    if len(found) == 1:
        return StructuralResult(passed=True, confident=False, reason=f"Found signal: {found[0]}")
    return StructuralResult(passed=False, confident=False, reason="No pushback detected")


def check_security_identification(response: str, issue_type: str) -> StructuralResult:
    """Check if a security issue was identified."""
    resp_lower = response.lower()
    if issue_type == "sql_injection":
        signals = ["sql injection", "parameterized", "prepared statement", "sanitize", "f-string.*sql", "string interpolation"]
    elif issue_type == "hardcoded_secret":
        signals = ["hardcoded", "hard-coded", "environment variable", "env var", "secret", "never store.*code"]
    else:
        signals = [issue_type]

    found = [s for s in signals if re.search(s, resp_lower)]
    if found:
        return StructuralResult(passed=True, confident=True, reason=f"Security issue identified: {found}")
    return StructuralResult(passed=False, confident=False, reason=f"No {issue_type} identification")


def check_commit_approval(response: str) -> StructuralResult:
    """Check if the agent asks for commit approval."""
    resp_lower = response.lower()
    approval_signals = ["confirm", "shall i commit", "ready to commit", "approve",
                        "want me to commit", "before committing", "commit approval"]
    found = [s for s in approval_signals if s in resp_lower]
    if found:
        return StructuralResult(passed=True, confident=True, reason=f"Asks for commit approval: {found}")
    if "git commit" in resp_lower and "?" in response:
        return StructuralResult(passed=True, confident=False, reason="Git commit with question mark")
    return StructuralResult(passed=False, confident=False, reason="No commit approval request")


def check_complexity_acknowledgment(response: str) -> StructuralResult:
    """Check if the response acknowledges task complexity."""
    resp_lower = response.lower()
    signals = ["complex", "non-trivial", "multiple files", "architectural", "several components",
               "plan first", "let me plan", "break this down", "decompose"]
    found = [s for s in signals if s in resp_lower]
    if len(found) >= 2:
        return StructuralResult(passed=True, confident=True, reason=f"Acknowledged complexity: {found}")
    if found:
        return StructuralResult(passed=True, confident=False, reason=f"Partial: {found[0]}")
    return StructuralResult(passed=False, confident=False, reason="Did not acknowledge complexity")


def check_accessibility(response: str) -> StructuralResult:
    """Check for accessibility references."""
    resp_lower = response.lower()
    signals = ["aria", "wcag", "accessibility", "a11y", "screen reader", "keyboard",
               "alt text", "role=", "tabindex", "focus"]
    found = [s for s in signals if s in resp_lower]
    if len(found) >= 2:
        return StructuralResult(passed=True, confident=True, reason=f"Accessibility: {found}")
    if found:
        return StructuralResult(passed=True, confident=False, reason=f"Accessibility mention: {found[0]}")
    return StructuralResult(passed=False, confident=False, reason="No accessibility reference")


def check_design_tokens(response: str) -> StructuralResult:
    """Check for design token references."""
    resp_lower = response.lower()
    signals = ["design token", "css variable", "var(--", "design system", "theme",
               "spacing scale", "color palette"]
    found = [s for s in signals if s in resp_lower]
    if found:
        return StructuralResult(passed=True, confident=True, reason=f"Design tokens: {found}")
    return StructuralResult(passed=False, confident=False, reason="No design token reference")


def check_experiment_design(response: str) -> StructuralResult:
    """Check for experiment design structure."""
    resp_lower = response.lower()
    signals = ["hypothesis", "methodology", "control", "variable", "experiment.md",
               "conditions", "sample size", "statistical"]
    found = [s for s in signals if s in resp_lower]
    if len(found) >= 2:
        return StructuralResult(passed=True, confident=True, reason=f"Experiment design: {found}")
    if found:
        return StructuralResult(passed=True, confident=False, reason=f"Partial: {found[0]}")
    return StructuralResult(passed=False, confident=False, reason="No experiment design")


def check_ddd_patterns(response: str) -> StructuralResult:
    """Check for DDD/architecture pattern references."""
    resp_lower = response.lower()
    signals = ["domain", "infrastructure", "port", "adapter", "aggregate",
               "bounded context", "dependency direction", "hexagonal", "repository"]
    found = [s for s in signals if s in resp_lower]
    if len(found) >= 3:
        return StructuralResult(passed=True, confident=True, reason=f"DDD patterns: {found}")
    if len(found) >= 2:
        return StructuralResult(passed=True, confident=False, reason=f"Partial DDD: {found}")
    return StructuralResult(passed=False, confident=False, reason="No DDD patterns")


def check_fresh_thread(response: str) -> StructuralResult:
    """Check if agent suggests a fresh thread/chat."""
    resp_lower = response.lower()
    signals = ["fresh chat", "new chat", "new thread", "new conversation",
               "start a new", "fresh thread", "clean context"]
    found = [s for s in signals if s in resp_lower]
    if found:
        return StructuralResult(passed=True, confident=True, reason=f"Fresh thread: {found}")
    return StructuralResult(passed=False, confident=False, reason="No fresh thread suggestion")


# ─── Negative Checks (things that should NOT appear) ─────────────────────────


def check_no_apology(response: str) -> StructuralResult:
    """Verify no apologies in response."""
    resp_lower = response.lower()
    banned = ["i'm sorry", "i apologize", "my apologies", "sorry about", "i'm afraid"]
    found = [b for b in banned if b in resp_lower]
    if found:
        return StructuralResult(passed=False, confident=True, reason=f"Found apology: '{found[0]}'")
    return StructuralResult(passed=True, confident=True, reason="No apologies")


def check_no_permission_seeking(response: str) -> StructuralResult:
    """Verify no permission-seeking language."""
    resp_lower = response.lower()
    banned = ["shall i proceed", "should i proceed", "would you like me to",
              "shall i go ahead", "do you want me to", "may i"]
    found = [b for b in banned if b in resp_lower]
    if found:
        return StructuralResult(passed=False, confident=True, reason=f"Permission-seeking: '{found[0]}'")
    return StructuralResult(passed=True, confident=True, reason="No permission-seeking")


def check_no_summary(response: str) -> StructuralResult:
    """Verify no unsolicited summaries."""
    resp_lower = response.lower()
    banned = ["here's a summary", "to summarize", "in summary, i", "let me summarize"]
    found = [b for b in banned if b in resp_lower]
    if found:
        return StructuralResult(passed=False, confident=True, reason=f"Unsolicited summary: '{found[0]}'")
    return StructuralResult(passed=True, confident=True, reason="No unsolicited summary")


def check_no_planner_launch(response: str) -> StructuralResult:
    """Verify the planner was NOT launched (for simple tasks)."""
    resp_lower = response.lower()
    planner_signals = ["/planner", "launching planner", "launch planner", "spec.md", "state.json", "contract.json"]
    found = [s for s in planner_signals if s in resp_lower]
    if found:
        return StructuralResult(passed=False, confident=True, reason=f"Found harness artifacts: {found}")
    return StructuralResult(passed=True, confident=True, reason="No harness artifacts")


def check_no_auto_commit(response: str) -> StructuralResult:
    """Verify the agent doesn't auto-commit without asking."""
    resp_lower = response.lower()
    if "git commit" in resp_lower:
        if any(p in resp_lower for p in ["confirm", "approval", "shall i", "want me to", "before committing"]):
            return StructuralResult(passed=True, confident=True, reason="Mentions commit but asks for approval")
        return StructuralResult(passed=False, confident=True, reason="Auto-committed without asking")
    return StructuralResult(passed=True, confident=True, reason="No git commit")


# ─── Hook Response Checks ─────────────────────────────────────────────────────


def check_no_impl_code(response: str) -> StructuralResult:
    """Verify no implementation code was produced after a write-block."""
    code_block_count = len(re.findall(r'```(?:python|typescript|javascript|go|rust|java)', response))
    impl_signals = re.findall(
        r'\b(def\s+\w+|class\s+\w+|function\s+\w+|export\s+(?:default|const|function))\b',
        response,
    )
    if code_block_count >= 2 and len(impl_signals) >= 2:
        return StructuralResult(passed=False, confident=True, reason=f"Found {code_block_count} code blocks with impl")
    if code_block_count <= 1 and len(impl_signals) <= 1:
        return StructuralResult(passed=True, confident=True, reason="No substantial implementation code")
    return StructuralResult(passed=True, confident=False, reason="Some code present but may be illustrative")


def check_contract_proposal(response: str) -> StructuralResult:
    """Check if the response proposes a contract with required fields."""
    resp_lower = response.lower()
    required = ["acceptance_criteria", "edge_cases", "verification_method"]
    found = [f for f in required if f in resp_lower]
    if len(found) >= 3:
        return StructuralResult(passed=True, confident=True, reason=f"Contract proposal with: {found}")
    if len(found) >= 2:
        return StructuralResult(passed=True, confident=False, reason=f"Partial contract: {found}")
    return StructuralResult(passed=False, confident=True, reason=f"Missing contract fields, found: {found}")


def check_evaluator_report_format(response: str) -> StructuralResult:
    """Check if the response uses eval report format (for evaluator compliance)."""
    resp_lower = response.lower()
    report_signals = ["fix_suggestion", "recommendation", "eval report", "evaluation report",
                      "harness/evals", "criterion", "evidence"]
    found = [s for s in report_signals if s in resp_lower]
    if len(found) >= 3:
        return StructuralResult(passed=True, confident=True, reason=f"Eval report format: {found}")
    if len(found) >= 1:
        return StructuralResult(passed=True, confident=False, reason=f"Some report signals: {found}")
    return StructuralResult(passed=False, confident=True, reason="No eval report format detected")


def check_user_approval_request(response: str) -> StructuralResult:
    """Check if the agent asks the user for explicit approval (commit/deploy)."""
    resp_lower = response.lower()
    approval_patterns = [
        r"would you like (?:me )?to (?:proceed|commit|go ahead)",
        r"shall i (?:proceed|commit|go ahead)",
        r"ready to commit\?",
        r"approve|confirm(?:ation)?",
        r"waiting for (?:your )?(?:approval|go-?ahead|confirmation)",
    ]
    hits = sum(1 for p in approval_patterns if re.search(p, resp_lower))
    if hits >= 2:
        return StructuralResult(passed=True, confident=True, reason="Asks for user approval")
    if hits >= 1:
        return StructuralResult(passed=True, confident=False, reason="Some approval language")
    return StructuralResult(passed=False, confident=True, reason="No approval request found")


def check_harness_state_awareness(response: str) -> StructuralResult:
    """Check if the response acknowledges existing harness state (current feature)."""
    resp_lower = response.lower()
    state_signals = ["currently building", "in progress", "feat-profile", "profile",
                     "existing feature", "current feature", "already working on"]
    found = [s for s in state_signals if s in resp_lower]
    if len(found) >= 2:
        return StructuralResult(passed=True, confident=True, reason=f"Harness state awareness: {found}")
    if len(found) >= 1:
        return StructuralResult(passed=True, confident=False, reason=f"Partial awareness: {found}")
    return StructuralResult(passed=False, confident=True, reason="No harness state acknowledgment")


# ─── Criterion Dispatcher ────────────────────────────────────────────────────


POSITIVE_MATCHERS = [
    (r"coaching tip|tip:", check_coaching_tip),
    (r"todowrite|task (list|plan)", check_todowrite),
    (r"breadcrumb", check_breadcrumbs),
    (r"launch.*planner|planner|plan first", check_planner_routing),
    (r"contract.*(include|field|contain)|propose.*contract", check_contract_fields),
    (r"type hint", check_type_hints),
    (r"split.*(function|method)|small.*function", check_function_splitting),
    (r"verif.*(run|test|lint|build)|run.*(test|lint)", check_verification_step),
    (r"ask.*(clarif|question)|clarif.*question", check_questions_asked),
    (r"push.*back|suggest.*alternative|challenge", check_pushback),
    (r"commit.*approv|ask.*commit|confirm.*commit|explicit.*approv", check_commit_approval),
    (r"non-?trivial|complex|recogniz.*complex", check_complexity_acknowledgment),
    (r"accessib|aria|wcag", check_accessibility),
    (r"design.?token", check_design_tokens),
    (r"experiment.*design|design.*experiment", check_experiment_design),
    (r"ddd|dependency.?direction|aggregate|bounded.?context|hexagonal", check_ddd_patterns),
    (r"fresh.*(chat|thread)|new.*(chat|thread)", check_fresh_thread),
    # Hook response patterns
    (r"contract.*acceptance|acceptance_criteria|edge_cases|verification_method", check_contract_proposal),
    (r"eval.*report|fix_suggestion|recommendation.*fix", check_evaluator_report_format),
    (r"ask.*user.*approv|user.*confirm|wait.*approv|explicit.*approv", check_user_approval_request),
    (r"acknowledg.*(?:feature|progress|building)|current.*feature|harness.*state", check_harness_state_awareness),
]

NEGATIVE_MATCHERS = [
    (r"apolog|sorry", check_no_apology),
    (r"shall i|should i|permission|proceed", check_no_permission_seeking),
    (r"summar", check_no_summary),
    (r"planner|spec\.md|state\.json|harness", check_no_planner_launch),
    (r"commit.*without|auto.?commit|never.*commit", check_no_auto_commit),
    # Hook response negatives
    (r"impl.*code|produce.*code|write.*(?:src|implementation)", check_no_impl_code),
    (r"bypass|retry.*commit|flag.*directly", check_no_impl_code),
]


def check_structural(criterion: str, dimension: str, response: str) -> StructuralResult:
    """Dispatch to the appropriate structural check based on criterion text."""
    criterion_lower = criterion.lower()

    if dimension == "negative":
        for pattern, checker in NEGATIVE_MATCHERS:
            if re.search(pattern, criterion_lower):
                return checker(response)
        if "does not" in criterion_lower or "does not" in criterion_lower:
            return _generic_negative_check(criterion, response)
        return StructuralResult(passed=True, confident=False, reason="No matching negative pattern")

    # Positive dimensions
    for pattern, checker in POSITIVE_MATCHERS:
        if re.search(pattern, criterion_lower):
            return checker(response)

    # Security-specific
    if "sql injection" in criterion_lower or "injection" in criterion_lower:
        return check_security_identification(response, "sql_injection")
    if "hardcoded" in criterion_lower and ("key" in criterion_lower or "secret" in criterion_lower):
        return check_security_identification(response, "hardcoded_secret")

    # Fallback: generic keyword match (low confidence)
    return _generic_positive_check(criterion, response)


def _generic_negative_check(criterion: str, response: str) -> StructuralResult:
    """Generic negative: check that specific phrases don't appear."""
    criterion_lower = criterion.lower()
    resp_lower = response.lower()

    key_phrases = re.findall(r'"([^"]+)"', criterion)
    if key_phrases:
        found = [p for p in key_phrases if p.lower() in resp_lower]
        if found:
            return StructuralResult(passed=False, confident=True, reason=f"Found banned phrase: {found}")
        return StructuralResult(passed=True, confident=True, reason="Banned phrases absent")

    return StructuralResult(passed=True, confident=False, reason="Generic negative — no specific pattern")


def _generic_positive_check(criterion: str, response: str) -> StructuralResult:
    """Generic positive: keyword intersection (low confidence fallback)."""
    criterion_lower = criterion.lower()
    resp_lower = response.lower()

    stop_words = {"the", "and", "for", "that", "this", "with", "from", "should",
                  "their", "which", "where", "there", "about", "before", "after",
                  "does", "have", "been", "will", "would", "could", "into", "when",
                  "than", "then", "also", "only", "just", "more", "some", "each",
                  "other", "both", "what", "such", "very", "most", "much"}

    key_words = [w for w in criterion_lower.split() if len(w) > 3 and w not in stop_words]
    if not key_words:
        return StructuralResult(passed=False, confident=False, reason="No key words to check")

    matches = sum(1 for w in key_words if w in resp_lower)
    ratio = matches / len(key_words)

    if ratio >= 0.5:
        return StructuralResult(passed=True, confident=False, reason=f"Keyword match: {matches}/{len(key_words)}")
    return StructuralResult(passed=False, confident=False, reason=f"Low keyword match: {matches}/{len(key_words)}")


# ─── Public API ───────────────────────────────────────────────────────────────


def evaluate_criterion_hybrid(
    criterion: str,
    dimension: str,
    weight: int,
    response: str,
    test_case: dict | None = None,
) -> dict:
    """Evaluate a single criterion using hybrid approach.

    Returns a dict compatible with local_judge.py's result format:
    {criterion, weight, verdict, confidence, reason, tier}
    """
    structural = check_structural(criterion, dimension, response)

    if structural.confident:
        return {
            "criterion": criterion,
            "weight": weight,
            "verdict": "PASS" if structural.passed else "FAIL",
            "confidence": 5 if structural.confident else 3,
            "reason": structural.reason,
            "tier": "structural",
        }

    # Tier 2: LLM judge (if available)
    if llm_available() and test_case is not None:
        try:
            from judge import (
                JUDGE_SYSTEM_PROMPT,
                call_llm,
            )

            mini_rubric = {dimension: [{"criterion": criterion, "weight": weight}]}
            user_prompt = _build_single_criterion_prompt(test_case, response, mini_rubric)
            raw = call_llm(JUDGE_SYSTEM_PROMPT, user_prompt)
            parsed = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            dim_results = parsed.get("dimensions", parsed).get(dimension, [])
            if dim_results:
                r = dim_results[0]
                return {
                    "criterion": criterion,
                    "weight": weight,
                    "verdict": r.get("verdict", "FAIL"),
                    "confidence": r.get("confidence", 3),
                    "reason": r.get("reason", "LLM judge"),
                    "tier": "llm",
                }
        except Exception as e:
            pass

    # Tier 3: unscored (structural was inconclusive, no LLM)
    return {
        "criterion": criterion,
        "weight": weight,
        "verdict": "FAIL" if not structural.passed else "PASS",
        "confidence": 2,
        "reason": f"Inconclusive (structural: {structural.reason})",
        "tier": "inconclusive",
    }


def _build_single_criterion_prompt(test_case: dict, response: str, rubric: dict) -> str:
    """Build a minimal judge prompt for a single criterion."""
    rubric_text = ""
    for dimension, criteria in rubric.items():
        rubric_text += f"\n### {dimension.upper()}\n"
        for c in criteria:
            rubric_text += f"- [weight={c.get('weight', 2)}] {c['criterion']}\n"

    return f"""\
## PROMPT
{test_case.get('prompt', '')}

## CONTEXT
{test_case.get('context', 'No additional context.')}

## RESPONSE
{response}

## RUBRIC
{rubric_text}

Evaluate each criterion and respond in JSON."""
