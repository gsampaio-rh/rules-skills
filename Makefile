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

# ─── Pipelines ────────────────────────────────────────────────

pipeline: validate capture eval-quick ## Quick pipeline: validate → capture → eval (N=1)

pipeline-full: validate capture eval-full eval-report ## Full pipeline: validate → capture → eval (N=3) → report

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

# ─── Profile app ──────────────────────────────────────────────

profile-api: ## Run profile API on http://127.0.0.1:8000
	.venv/bin/uvicorn backend.src.api.main:app --reload --host 127.0.0.1 --port 8000

profile-ui: ## Run profile frontend on http://127.0.0.1:5173
	cd frontend && npm run dev

profile-test: ## Run profile API tests
	.venv/bin/pytest tests/test_profile_api.py -q

payment-test: ## Run payment, order, and checkout API tests
	.venv/bin/pytest tests/test_payment_api.py tests/test_order_domain.py tests/test_cart_api.py -q

notification-test: ## Run auth, notification service, and notification API tests
	.venv/bin/pytest tests/test_notification_service.py tests/test_auth_api.py tests/test_notification_api.py -q

search-test: ## Run unified search API tests
	.venv/bin/pytest tests/test_search_api.py -q

weekly-digest: ## Send weekly digest emails to eligible users
	.venv/bin/python -m backend.src.jobs.send_weekly_digests
