# Eval pipeline for rules-skills
#
# Prerequisites:
#   pip install -r tests/eval/requirements.txt
#   export CURSOR_API_KEY="crsr_..."
#
# Quick reference:
#   make eval-fast      → Tier 1: static lints (seconds, no API key)
#   make eval-session   → Tier 3: full session eval (needs CURSOR_API_KEY)
#   make eval           → Tier 1 + Tier 3

PYTHON      ?= python
MODEL       ?= composer-2.5
ABLATE_RULE ?= adversarial_harness.mdc

.PHONY: help validate setup sync-local
.PHONY: eval eval-fast eval-session eval-session-dry eval-session-judge eval-session-report
.PHONY: eval-session-long eval-session-long-dry eval-session-long-judge
.PHONY: eval-ci-pr eval-ci-nightly eval-regression-check
.PHONY: eval-ablation eval-ablation-dry eval-ablation-adversarial
.PHONY: clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─── Local Setup ─────────────────────────────────────────────

setup: sync-local ## Initial setup for fresh clone (populates .cursor/ from library/cursor/)
	@mkdir -p .harness/evals .harness/audits

sync-local: ## Copy library/cursor/ into .cursor/ (rules, skills, hooks, agents, references)
	@echo "Syncing library/cursor/ → .cursor/ ..."
	@mkdir -p .cursor
	@# Cleanup stale runtime artifacts
	@rm -f .cursor/.DS_Store .cursor/hooks/.commit-approved
	@rm -rf .cursor/hooks.bak
	@if [ -f .cursor/hooks.log ] && [ $$(wc -c < .cursor/hooks.log) -gt 102400 ]; then \
		tail -200 .cursor/hooks.log > .cursor/hooks.log.tmp && \
		mv .cursor/hooks.log.tmp .cursor/hooks.log; \
		echo "  Trimmed hooks.log (kept last 200 lines)"; \
	fi
	@# Sync directories (rm + cp = full cleanup of deleted files)
	@for dir in rules skills hooks agents references; do \
		if [ -L ".cursor/$$dir" ]; then rm ".cursor/$$dir"; fi; \
		if [ -d "library/cursor/$$dir" ]; then \
			rm -rf ".cursor/$$dir"; \
			cp -R "library/cursor/$$dir" ".cursor/$$dir"; \
		fi; \
	done
	@rm -f .cursor/hooks.json .cursor/hooks.full.json .cursor/hooks.lean.json
	@cp library/cursor/hooks.full.json .cursor/hooks.full.json
	@cp library/cursor/hooks.lean.json .cursor/hooks.lean.json
	@cp library/cursor/hooks.lean.json .cursor/hooks.json
	@echo "lean" > .cursor/.hooks-profile
	@echo "Done. Profile: lean (run scripts/hooks-profile.sh full to switch)"

validate: ## Validate rules and skills against authoring standards
	$(PYTHON) tests/validate.py

# ─── Eval Pipeline ───────────────────────────────────────────

eval: eval-fast eval-session ## Run full eval (Tier 1 + Tier 3)

eval-fast: validate ## Tier 1: fast static checks (seconds, no API key)
	$(PYTHON) tests/eval/contract_lint.py
	$(PYTHON) tests/eval/harness_lint.py

eval-session: ## Tier 3: run scenarios in isolated sandbox via Cursor SDK
	$(PYTHON) tests/eval/session_runner.py --model $(MODEL) --timeout 300

eval-session-dry: ## Tier 3: show session scenario plan
	$(PYTHON) tests/eval/session_runner.py --dry-run

eval-session-judge: ## Tier 3: judge completed sessions (structural checks)
	$(PYTHON) tests/eval/session_judge.py --tier structural

eval-session-judge-full: ## Tier 3: judge with all tiers including LLM
	$(PYTHON) tests/eval/session_judge.py

eval-session-report: ## Tier 3: aggregated report from judgments
	$(PYTHON) tests/eval/session_report.py --save

eval-session-long: ## Tier 3: run long scenarios (~10-15 min each, needs CURSOR_API_KEY)
	$(PYTHON) tests/eval/session_runner.py --long --model $(MODEL)

eval-session-long-dry: ## Tier 3: show long scenario plan
	$(PYTHON) tests/eval/session_runner.py --long --dry-run

eval-session-long-judge: ## Tier 3: judge completed long sessions
	$(PYTHON) tests/eval/session_judge.py --tier structural

eval-ci-pr: ## CI: run PR tier (11 protocol scenarios) + judge + regression check
	$(PYTHON) tests/eval/session_runner.py --ci-tier pr --model $(MODEL)
	$(PYTHON) tests/eval/session_judge.py --tier structural
	$(PYTHON) tests/eval/session_report.py --save
	$(PYTHON) tests/eval/eval_regression_check.py \
		--run-dir tests/eval_results/$$(ls -t tests/eval_results/ | head -1) \
		--baseline tests/eval/fixtures/eval_baseline.json \
		--tier pr \
		--write-diff tests/eval_results/$$(ls -t tests/eval_results/ | head -1)/regression.json

eval-ci-nightly: ## CI: run nightly tier (31 scenarios) + judge + regression check
	$(PYTHON) tests/eval/session_runner.py --ci-tier nightly --model $(MODEL)
	$(PYTHON) tests/eval/session_judge.py --tier structural
	$(PYTHON) tests/eval/session_report.py --save
	$(PYTHON) tests/eval/eval_regression_check.py \
		--run-dir tests/eval_results/$$(ls -t tests/eval_results/ | head -1) \
		--baseline tests/eval/fixtures/eval_baseline.json \
		--tier nightly \
		--write-diff tests/eval_results/$$(ls -t tests/eval_results/ | head -1)/regression.json

eval-regression-check: ## Run regression check against latest run dir
	$(PYTHON) tests/eval/eval_regression_check.py \
		--run-dir tests/eval_results/$$(ls -t tests/eval_results/ | head -1) \
		--baseline tests/eval/fixtures/eval_baseline.json \
		--tier pr

eval-ablation: ## Ablation run: each standard scenario 2x (control + ablated). Set ABLATE_RULE=<rule.mdc>
	$(PYTHON) tests/eval/session_runner.py --ablate-rule $(ABLATE_RULE) --model $(MODEL)

eval-ablation-dry: ## Show ablation plan without running
	$(PYTHON) tests/eval/session_runner.py --ablate-rule $(ABLATE_RULE) --dry-run

eval-ablation-adversarial: ## Ablation targeting adversarial_harness.mdc (ACAM Configuration gate)
	$(PYTHON) tests/eval/session_runner.py \
		--ablate-rule adversarial_harness.mdc \
		--filter protocol \
		--model $(MODEL)

# ─── Schema Migration ───────────────────────────────────────

migrate-harness: ## Migrate .harness/ files from v1 (features) to v2 (tasks) schema
	$(PYTHON) scripts/migrate-state-schema.py

migrate-harness-dry: ## Preview migration without writing files
	$(PYTHON) scripts/migrate-state-schema.py --dry-run

harness-prune: ## Preview stale harness state to prune (dry-run; use --apply to mutate)
	$(PYTHON) library/cursor/hooks/prune-harness.py

# ─── Utilities ────────────────────────────────────────────────

clean: ## Remove all eval results
	rm -rf tests/eval_results/
