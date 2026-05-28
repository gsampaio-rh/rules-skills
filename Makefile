# Eval pipeline for rules-skills
#
# Prerequisites:
#   pip install -r tests/eval/requirements.txt
#   export CURSOR_API_KEY="cursor_..."      (for capture)
#   export OPENAI_API_KEY="sk-..."          (for eval, or ANTHROPIC_API_KEY)
#
# Quick reference:
#   make eval-quick     → fast check (N=1, no save)
#   make eval-full      → rigorous eval (N=3, saved to history)
#   make eval-regress   → regression check against baseline
#   make eval-baseline  → lock current scores as baseline
#   make eval-report    → generate rich markdown report

PYTHON   ?= python
MODEL    ?= composer-2.5
N_RUNS   ?= 3

.PHONY: help validate capture eval pipeline compare status clean
.PHONY: eval-quick eval-full eval-regress eval-baseline eval-report
.PHONY: eval-multi eval-multi-save eval-multi-dry eval-multi-capture eval-multi-judge
.PHONY: divergence trace-review

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

validate: ## Validate rules and skills against authoring standards
	$(PYTHON) tests/validate.py

# ─── Capture ──────────────────────────────────────────────────

capture: ## Capture agent responses via Cursor SDK (skips existing)
	$(PYTHON) tests/eval/auto_capture.py --model $(MODEL)

capture-force: ## Re-capture all responses (overwrites existing)
	$(PYTHON) tests/eval/auto_capture.py --model $(MODEL) --force

# ─── Evaluation ───────────────────────────────────────────────

eval: eval-quick ## Alias for eval-quick

eval-quick: ## Quick eval: N=1 judge run, no save (fast, cheap)
	$(PYTHON) tests/eval/run_eval.py --model $(MODEL)

eval-full: ## Full eval: N=3 judge runs, saved to history (rigorous)
	$(PYTHON) tests/eval/run_eval.py --model $(MODEL) --full --save

eval-regress: ## Regression check against locked baseline
	$(PYTHON) tests/eval/stats.py --regress

eval-baseline: ## Lock current scores as the new baseline
	$(PYTHON) tests/eval/stats.py --baseline

eval-report: ## Generate rich markdown report from latest run
	$(PYTHON) tests/eval/report.py

eval-trends: ## Show score trends across historical runs
	$(PYTHON) tests/eval/stats.py --trends

eval-summary: ## Show summary of latest run
	$(PYTHON) tests/eval/stats.py --summary

# ─── Multi-Turn Eval ─────────────────────────────────────────

JUDGE_MODEL ?= claude-opus-4-6

eval-multi: ## Multi-turn eval: capture + judge via Cursor SDK
	$(PYTHON) tests/eval/multi_turn_eval.py --capture-model $(MODEL) --judge-model $(JUDGE_MODEL)

eval-multi-save: ## Multi-turn eval with history save
	$(PYTHON) tests/eval/multi_turn_eval.py --capture-model $(MODEL) --judge-model $(JUDGE_MODEL) --save

eval-multi-dry: ## Show multi-turn test plan
	$(PYTHON) tests/eval/multi_turn_eval.py --dry-run

eval-multi-capture: ## Capture multi-turn transcripts only (no judging)
	$(PYTHON) tests/eval/multi_turn_eval.py --capture-model $(MODEL) --capture-only

eval-multi-judge: ## Judge existing transcripts only (no capture)
	$(PYTHON) tests/eval/multi_turn_eval.py --judge-model $(JUDGE_MODEL) --judge-only

# ─── Analysis ────────────────────────────────────────────────

divergence: ## Analyze divergence patterns from latest eval run
	$(PYTHON) tests/eval/divergence.py --verbose

trace-review: ## AI-powered review of failing traces (uses CURSOR_API_KEY)
	$(PYTHON) tests/eval/trace_review.py --model $(JUDGE_MODEL)

# ─── Pipelines ────────────────────────────────────────────────

pipeline: validate capture eval-quick ## Quick pipeline: validate → capture → eval (N=1)

pipeline-full: validate capture eval-full eval-multi eval-report ## Full pipeline: validate → capture → eval (N=3) → multi-turn → report

# ─── Utilities ────────────────────────────────────────────────

compare: ## Compare response availability across models
	$(PYTHON) tests/eval/run_eval.py --compare

status: ## Show capture progress
	$(PYTHON) tests/eval/auto_capture.py --model $(MODEL) --status

dry-run: ## Show what would be captured and evaluated
	@echo "=== Capture plan ==="
	$(PYTHON) tests/eval/auto_capture.py --model $(MODEL) --dry-run
	@echo ""
	@echo "=== Eval plan ==="
	$(PYTHON) tests/eval/run_eval.py --model $(MODEL) --dry-run

clean: ## Remove all captured responses (all models)
	rm -rf tests/eval/responses/*/

clean-history: ## Remove all eval history (runs + trends)
	rm -rf tests/eval/history/runs/
	rm -rf tests/eval/history/trends.json
