#!/usr/bin/env python3
"""LLM-as-judge evaluator for Cursor rules and skills.

Reads test cases from dataset.yaml, matches them with captured agent responses,
and scores each response using rubric-based multi-dimensional evaluation.

Modes:
    eval-quick:  N=1 judge run per test (fast, cheap, less reliable)
    eval-full:   N=3 judge runs per test (slower, statistical confidence)

Usage:
    python tests/eval/run_eval.py                           # quick eval (N=1)
    python tests/eval/run_eval.py --full                    # full eval (N=3)
    python tests/eval/run_eval.py --model composer-2.5      # specific model
    python tests/eval/run_eval.py --filter security         # only matching tests
    python tests/eval/run_eval.py --category routing        # only a category
    python tests/eval/run_eval.py --difficulty hard         # only hard tests
    python tests/eval/run_eval.py --compare                 # compare models
    python tests/eval/run_eval.py --dry-run                 # show plan
    python tests/eval/run_eval.py --save                    # save results to history/

Environment variables:
    EVAL_PROVIDER   - 'openai' or 'anthropic' (default: openai)
    EVAL_MODEL      - model name (default: gpt-4o for openai, claude-sonnet-4-20250514 for anthropic)
    EVAL_API_KEY    - API key (or OPENAI_API_KEY / ANTHROPIC_API_KEY)
"""

import argparse
import sys

from capture import discover_models, print_compare, print_eval_plan
from common import filter_dataset, load_dataset
from judging import run_evaluation
from reporting import print_report, save_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate agent responses against rules/skills")
    parser.add_argument("--filter", help="Only tests matching this string (id, target, or category)")
    parser.add_argument("--category", help="Only tests in this category")
    parser.add_argument("--difficulty", help="Only tests at this difficulty (easy/medium/hard)")
    parser.add_argument("--model", help="Evaluate responses from a specific model subdirectory")
    parser.add_argument("--full", action="store_true", help="Full eval with N=3 runs per test")
    parser.add_argument("--runs", type=int, default=None, help="Custom number of judge runs (default: 1, --full: 3)")
    parser.add_argument("--compare", action="store_true", help="Compare response availability across models")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be evaluated")
    parser.add_argument("--save", action="store_true", help="Save results to history/runs/")
    args = parser.parse_args()

    dataset = load_dataset()
    dataset = filter_dataset(dataset, args.filter, args.category, args.difficulty)

    if args.compare:
        models = discover_models()
        if not models:
            print("No model subdirectories found in responses/.")
            return 1
        print_compare(dataset, models)
        return 0

    if args.dry_run:
        print_eval_plan(dataset, args.model)
        return 0

    n_runs = args.runs or (3 if args.full else 1)
    print(f"Running evaluation (N={n_runs} runs per test)...\n")

    results = run_evaluation(dataset, args.model, n_runs)
    print_report(results)

    if args.save:
        save_run(results, args.model)

    evaluated = [r for r in results if r.error != "no_response"]
    if evaluated:
        overall = sum(r.overall_score for r in evaluated) / len(evaluated)
        return 0 if overall >= 0.8 else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
