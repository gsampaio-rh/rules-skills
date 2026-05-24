# Eval pipeline for rules-skills
#
# Prerequisites:
#   pip install -r tests/eval/requirements.txt
#   export CURSOR_API_KEY="cursor_..."      (for capture)
#   export OPENAI_API_KEY="sk-..."          (for eval, or ANTHROPIC_API_KEY)

PYTHON   ?= python
MODEL    ?= composer-2.5

.PHONY: help validate capture eval pipeline compare status clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

validate: ## Validate rules and skills against authoring standards
	$(PYTHON) tests/validate.py

capture: ## Capture agent responses via Cursor SDK (skips existing)
	$(PYTHON) tests/eval/auto_capture.py --model $(MODEL)

capture-force: ## Re-capture all responses (overwrites existing)
	$(PYTHON) tests/eval/auto_capture.py --model $(MODEL) --force

eval: ## Run LLM-as-judge evaluation on captured responses
	$(PYTHON) tests/eval/run_eval.py --model $(MODEL)

pipeline: validate capture eval ## Full pipeline: validate → capture → eval

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
