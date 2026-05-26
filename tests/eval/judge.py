"""Rubric-based LLM judge for evaluating agent responses.

Supports multi-dimensional scoring (1-5 per axis), confidence scores,
and multiple judge runs for statistical reliability.
"""

import json
import os
from dataclasses import dataclass, field

JUDGE_SYSTEM_PROMPT = """\
You are an expert evaluator assessing whether an AI coding assistant followed \
specific behavioral guidelines. You will receive:

1. The PROMPT given to the assistant
2. The CONTEXT describing the test scenario
3. The assistant's RESPONSE
4. A RUBRIC with criteria organized by dimension, each with a weight (1-3)

For each criterion, respond with:
- verdict: PASS or FAIL
- confidence: 1-5 (1=unsure, 5=certain)
- reason: one sentence explaining your judgment

Respond in JSON format:
{
  "dimensions": {
    "dimension_name": [
      {"criterion": "...", "verdict": "PASS|FAIL", "confidence": 5, "reason": "..."}
    ]
  }
}

Grading rules:
- PASS means clear evidence the assistant exhibited the expected behavior
- FAIL means the behavior was absent or the opposite was observed
- For "negative" dimension criteria: PASS means correctly AVOIDED the bad behavior
- Be strict but fair. Only PASS when evidence is clear.
- Confidence 5 = completely certain, 1 = guessing (e.g., ambiguous response)
- Weight indicates importance: 3=critical, 2=important, 1=nice-to-have"""


@dataclass
class CriterionResult:
    criterion: str
    dimension: str
    weight: int
    verdict: str = ""
    confidence: int = 5
    reason: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"

    @property
    def weighted_score(self) -> float:
        return self.weight if self.passed else 0.0

    @property
    def max_score(self) -> float:
        return float(self.weight)


@dataclass
class DimensionScore:
    dimension: str
    criteria: list[CriterionResult] = field(default_factory=list)

    @property
    def score(self) -> float:
        total = sum(c.max_score for c in self.criteria)
        if total == 0:
            return 0.0
        return sum(c.weighted_score for c in self.criteria) / total

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.criteria if c.passed)

    @property
    def total_count(self) -> int:
        return len(self.criteria)

    @property
    def avg_confidence(self) -> float:
        if not self.criteria:
            return 0.0
        return sum(c.confidence for c in self.criteria) / len(self.criteria)


@dataclass
class JudgeResult:
    test_id: str
    targets: list[str]
    category: str
    difficulty: str
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    error: str = ""
    run_index: int = 0

    @property
    def overall_score(self) -> float:
        all_criteria = [c for d in self.dimensions.values() for c in d.criteria]
        total_weight = sum(c.max_score for c in all_criteria)
        if total_weight == 0:
            return 0.0
        return sum(c.weighted_score for c in all_criteria) / total_weight

    @property
    def passed(self) -> bool:
        return self.error == "" and self.overall_score >= 0.8

    @property
    def avg_confidence(self) -> float:
        all_criteria = [c for d in self.dimensions.values() for c in d.criteria]
        if not all_criteria:
            return 0.0
        return sum(c.confidence for c in all_criteria) / len(all_criteria)

    @property
    def total_criteria(self) -> int:
        return sum(d.total_count for d in self.dimensions.values())

    @property
    def passed_criteria(self) -> int:
        return sum(d.passed_count for d in self.dimensions.values())

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "targets": self.targets,
            "category": self.category,
            "difficulty": self.difficulty,
            "overall_score": round(self.overall_score, 3),
            "passed": self.passed,
            "avg_confidence": round(self.avg_confidence, 2),
            "criteria_passed": f"{self.passed_criteria}/{self.total_criteria}",
            "run_index": self.run_index,
            "error": self.error,
            "dimensions": {
                name: {
                    "score": round(dim.score, 3),
                    "criteria": [
                        {
                            "criterion": c.criterion,
                            "weight": c.weight,
                            "verdict": c.verdict,
                            "confidence": c.confidence,
                            "reason": c.reason,
                        }
                        for c in dim.criteria
                    ],
                }
                for name, dim in self.dimensions.items()
            },
        }


def build_judge_prompt(test_case: dict, response: str) -> str:
    rubric = test_case.get("rubric", {})

    if not rubric:
        rubric = _convert_legacy_to_rubric(test_case)

    rubric_text = ""
    for dimension, criteria in rubric.items():
        rubric_text += f"\n### {dimension.upper()}\n"
        for c in criteria:
            weight = c.get("weight", 2)
            rubric_text += f"- [weight={weight}] {c['criterion']}\n"

    return f"""\
## PROMPT
{test_case['prompt']}

## CONTEXT
{test_case.get('context', 'No additional context.')}

## RESPONSE
{response}

## RUBRIC
{rubric_text}

Evaluate each criterion and respond in JSON."""


def _convert_legacy_to_rubric(test_case: dict) -> dict:
    """Convert legacy expected/anti_expected format to rubric format."""
    rubric = {}
    expected = test_case.get("expected", [])
    anti_expected = test_case.get("anti_expected", [])

    if expected:
        rubric["behavioral"] = [
            {"criterion": e, "weight": 2} for e in expected
        ]
    if anti_expected:
        rubric["negative"] = [
            {"criterion": a, "weight": 2} for a in anti_expected
        ]
    return rubric


def call_llm(system: str, user: str) -> str:
    provider = os.environ.get("EVAL_PROVIDER", "openai").lower()

    if provider == "openai":
        model = os.environ.get("EVAL_MODEL", "gpt-4o")
        api_key = os.environ.get("EVAL_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        return _call_openai(system, user, model, api_key)
    elif provider == "anthropic":
        model = os.environ.get("EVAL_MODEL", "claude-sonnet-4-20250514")
        api_key = os.environ.get("EVAL_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
        return _call_anthropic(system, user, model, api_key)
    elif provider == "cursor":
        model = os.environ.get("EVAL_MODEL", "claude-opus-4-6")
        api_key = os.environ.get("EVAL_API_KEY") or os.environ.get("CURSOR_API_KEY", "")
        return _call_cursor(system, user, model, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'openai', 'anthropic', or 'cursor'.")


def _call_openai(system: str, user: str, model: str, api_key: str, base_url: str | None = None) -> str:
    from openai import OpenAI

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(system: str, user: str, model: str, api_key: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0.0,
    )
    return resp.content[0].text


def _call_cursor(system: str, user: str, model: str, api_key: str) -> str:
    from cursor_sdk import Agent, AgentOptions

    prompt = f"{system}\n\n---\n\n{user}"
    result = Agent.prompt(
        prompt,
        AgentOptions(api_key=api_key, model=model),
    )
    return result.result or ""


def parse_judge_response(raw: str, test_case: dict) -> dict[str, DimensionScore]:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]

    data = json.loads(clean)
    dimensions_data = data.get("dimensions", data)

    rubric = test_case.get("rubric", {})
    if not rubric:
        rubric = _convert_legacy_to_rubric(test_case)

    dimensions: dict[str, DimensionScore] = {}

    for dim_name, criteria_spec in rubric.items():
        dim_results = dimensions_data.get(dim_name, [])
        dim_score = DimensionScore(dimension=dim_name)

        for i, spec in enumerate(criteria_spec):
            result = dim_results[i] if i < len(dim_results) else {}
            dim_score.criteria.append(
                CriterionResult(
                    criterion=spec["criterion"],
                    dimension=dim_name,
                    weight=spec.get("weight", 2),
                    verdict=result.get("verdict", "FAIL"),
                    confidence=result.get("confidence", 3),
                    reason=result.get("reason", "No response from judge"),
                )
            )

        dimensions[dim_name] = dim_score

    return dimensions


def evaluate_single(test_case: dict, response: str, run_index: int = 0) -> JudgeResult:
    result = JudgeResult(
        test_id=test_case["id"],
        targets=test_case.get("targets", []),
        category=test_case.get("category", ""),
        difficulty=test_case.get("difficulty", "medium"),
        run_index=run_index,
    )

    user_prompt = build_judge_prompt(test_case, response)

    try:
        raw = call_llm(JUDGE_SYSTEM_PROMPT, user_prompt)
        result.dimensions = parse_judge_response(raw, test_case)
    except Exception as e:
        result.error = f"judge_error: {e}"

    return result


def evaluate_multi_run(
    test_case: dict, response: str, n_runs: int = 3
) -> list[JudgeResult]:
    return [evaluate_single(test_case, response, run_index=i) for i in range(n_runs)]
