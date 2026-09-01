# Eval pipeline for rules-skills
#
# Prerequisites:
#   pip install -r tests/eval/requirements.txt
#   export CURSOR_API_KEY="crsr_..."
#
# Quick reference:
#   make eval-unit      → hook unit tests (~60s, no API)
#   make eval-fast      → validate + eval-unit + contract/harness lint (~70s, no API)
#   make eval-session   → LOCAL SDK session eval (needs CURSOR_API_KEY; not hosted CI)
#   make eval           → eval-fast + eval-session

PYTHON      ?= python
MODEL       ?= composer-2.5
ABLATE_RULE ?= adversarial_harness.mdc

.PHONY: help validate setup sync-local
.PHONY: eval eval-fast eval-session eval-session-dry eval-session-judge eval-session-report
.PHONY: eval-session-long eval-session-long-dry eval-session-long-judge
.PHONY: eval-ci-pr eval-ci-nightly eval-regression-check
.PHONY: eval-ablation eval-ablation-dry eval-ablation-adversarial
.PHONY: clean harness-dashboard

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─── Local Setup ─────────────────────────────────────────────

setup: sync-local ## Initial setup for fresh clone (populates .cursor/ from library/cursor/)
	@mkdir -p .harness/evals

sync-local: ## Copy library/cursor/ into .cursor/ (rules, skills, hooks, agents, references)
	@echo "Syncing library/cursor/ → .cursor/ ..."
	@mkdir -p .cursor
	@# Cleanup stale runtime artifacts
	@rm -f .cursor/.DS_Store .cursor/hooks/.commit-approved
	@rm -rf .cursor/hooks.bak
	@# Cleanup deprecated harness dirs (v2 simplification: no more docs/ or audits/)
	@rm -rf .harness/docs .harness/audits
	@if [ -f .cursor/hooks.log ] && [ $$(wc -c < .cursor/hooks.log) -gt 102400 ]; then \
		tail -200 .cursor/hooks.log > .cursor/hooks.log.tmp && \
		mv .cursor/hooks.log.tmp .cursor/hooks.log; \
		echo "  Trimmed hooks.log (kept last 200 lines)"; \
	fi
	@# Sync directories (rm + cp = full cleanup of deleted files)
	@for dir in rules skills hooks agents references templates; do \
		if [ -L ".cursor/$$dir" ]; then rm ".cursor/$$dir"; fi; \
		if [ -d "library/cursor/$$dir" ]; then \
			rm -rf ".cursor/$$dir"; \
			cp -R "library/cursor/$$dir" ".cursor/$$dir"; \
		fi; \
	done
	@# Remove _archive/ from deployed .cursor/ — library/ keeps history; .cursor/ is active catalog only.
	@# Cursor scans all SKILL.md under .cursor/skills/**; _archive/ skills would leak into the active catalog.
	@rm -rf .cursor/skills/_archive .cursor/hooks/_archive
	@rm -f .cursor/hooks.json .cursor/hooks.full.json .cursor/hooks.lean.json
	@cp library/cursor/hooks.json .cursor/hooks.json
	@cp library/cursor/hooks.optional.json .cursor/hooks.optional.json
	@echo "default" > .cursor/.hooks-profile
	@cp library/cursor/harness-model-routing.json .cursor/harness-model-routing.json
	@bash scripts/adopt-agents-md.sh . library/cursor
	@echo "Done. Profile: default (run scripts/hooks-profile.sh optional to add advisories)"

validate: ## Validate rules and skills against authoring standards
	$(PYTHON) tests/validate.py

# ─── Eval Pipeline ───────────────────────────────────────────

eval: eval-fast eval-session ## Run full eval (Tier 1 + Tier 2 + Tier 3)

eval-fast: validate eval-unit ## Tier 1+2: validate + hook unit tests + contract/harness lint (no API)
	$(PYTHON) tests/eval/contract_lint.py
	$(PYTHON) tests/eval/harness_lint.py

eval-unit: ## Tier 2: deterministic hook behavior tests (no API; ~60s)
	$(PYTHON) -m pytest tests/eval/ -q --tb=line

eval-session: ## LOCAL SDK: run scenarios (needs CURSOR_API_KEY; no GitHub Actions)
	$(PYTHON) tests/eval/session_runner.py --model $(MODEL) --timeout 300

eval-session-dry: ## LOCAL SDK: show session scenario plan
	$(PYTHON) tests/eval/session_runner.py --dry-run

eval-session-judge: ## LOCAL SDK: judge completed sessions (structural checks)
	$(PYTHON) tests/eval/session_judge.py --tier structural

eval-session-judge-full: ## LOCAL SDK: judge with all tiers including LLM
	$(PYTHON) tests/eval/session_judge.py

eval-session-report: ## LOCAL SDK: aggregated report from judgments
	$(PYTHON) tests/eval/session_report.py --save

eval-session-long: ## LOCAL SDK: long scenarios (~10-15 min each, needs CURSOR_API_KEY)
	$(PYTHON) tests/eval/session_runner.py --long --model $(MODEL)

eval-session-long-dry: ## LOCAL SDK: show long scenario plan
	$(PYTHON) tests/eval/session_runner.py --long --dry-run

eval-session-long-judge: ## LOCAL SDK: judge completed long sessions
	$(PYTHON) tests/eval/session_judge.py --tier structural

eval-ci-pr: ## LOCAL SDK only (not hosted CI): PR-tier scenarios + regression check
	@echo "NOTE: No GitHub Actions — this runs locally via Cursor SDK"
	$(PYTHON) tests/eval/session_runner.py --ci-tier pr --model $(MODEL)
	$(PYTHON) tests/eval/session_judge.py --tier structural
	$(PYTHON) tests/eval/session_report.py --save
	$(PYTHON) tests/eval/eval_regression_check.py \
		--run-dir tests/eval_results/$$(ls -t tests/eval_results/ | head -1) \
		--baseline tests/eval/fixtures/eval_baseline.json \
		--tier pr \
		--write-diff tests/eval_results/$$(ls -t tests/eval_results/ | head -1)/regression.json

eval-ci-nightly: ## LOCAL SDK only (not hosted CI): nightly scenarios + regression check
	@echo "NOTE: No GitHub Actions — this runs locally via Cursor SDK"
	$(PYTHON) tests/eval/session_runner.py --ci-tier nightly --model $(MODEL)
	$(PYTHON) tests/eval/session_judge.py --tier structural
	$(PYTHON) tests/eval/session_report.py --save
	$(PYTHON) tests/eval/eval_regression_check.py \
		--run-dir tests/eval_results/$$(ls -t tests/eval_results/ | head -1) \
		--baseline tests/eval/fixtures/eval_baseline.json \
		--tier nightly \
		--write-diff tests/eval_results/$$(ls -t tests/eval_results/ | head -1)/regression.json

eval-regression-check: ## LOCAL: regression check against latest run dir
	$(PYTHON) tests/eval/eval_regression_check.py \
		--run-dir tests/eval_results/$$(ls -t tests/eval_results/ | head -1) \
		--baseline tests/eval/fixtures/eval_baseline.json \
		--tier pr

eval-ablation: ## LOCAL SDK: ablation (control + ablated). Set ABLATE_RULE=<rule.mdc>
	$(PYTHON) tests/eval/session_runner.py --ablate-rule $(ABLATE_RULE) --model $(MODEL)

eval-ablation-dry: ## LOCAL SDK: show ablation plan without running
	$(PYTHON) tests/eval/session_runner.py --ablate-rule $(ABLATE_RULE) --dry-run

eval-ablation-adversarial: ## LOCAL SDK: ablation targeting adversarial_harness.mdc
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

harness-dashboard: ## Generate read-only Genius Bar session desk (.harness/dashboard.html)
	@$(PYTHON) library/cursor/hooks/harness-dashboard.py --root . --out .harness/dashboard.html

# ─── Utilities ────────────────────────────────────────────────

clean: ## Remove all eval results
	rm -rf tests/eval_results/
