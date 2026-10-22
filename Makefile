.PHONY: setup test test-fast lint fmt exp baseline figures check upstream clean

setup:
	uv sync --frozen --python 3.12 --extra dev

test:
	uv run pytest -q

# Unit tests without the whole-simulation and data-building suites (~1 min); `make test` before a behaviour change
test-fast:
	uv run pytest -q -p no:warnings --ignore=tests/test_macromodel/unit/test_simulation.py --ignore=tests/test_macro_data

# The credit clearing file is excluded from the format check until upstream merges PR #104 (E11):
# reformatting it here would conflict with that merge.
LINT_FORMAT_EXCLUDE = macromodel/markets/credit_market/func/clearing.py

lint:
	uv run ruff check macromodel macro_data experiments tests
	uv run ruff format --check --exclude $(LINT_FORMAT_EXCLUDE) macromodel macro_data experiments tests

fmt:
	uv run ruff format --exclude $(LINT_FORMAT_EXCLUDE) macromodel macro_data experiments tests
	uv run ruff check --fix macromodel macro_data experiments tests

# make exp EXP=exp001 ARGS="--seeds 5"
exp:
	@test -n "$(EXP)" || { echo "usage: make exp EXP=exp001 [ARGS=...]"; exit 1; }
	@f=$$(ls experiments/$(EXP)*.py 2>/dev/null | head -1); \
	 test -n "$$f" || { echo "no experiment matching '$(EXP)'"; exit 1; }; \
	 echo "running $$f $(ARGS)"; uv run python "$$f" $(ARGS)

# Reference run: default model, France 2014-Q1, scored against data. ~15 s.
baseline:
	uv run python experiments/exp001_baseline.py

# The standard figures (model map, baseline fan and dashboard, ladder, robustness) from existing outputs
figures:
	uv run python experiments/figures.py

# Everything to run before committing a change to model behaviour
check: test lint baseline

# What upstream (INET-Complexity) has that we don't: open branches ahead of main.
upstream:
	@git fetch -q upstream && git fetch -q origin
	@echo "main vs upstream/main: $$(git rev-list --count main..upstream/main) behind, $$(git rev-list --count upstream/main..main) ahead"
	@for b in $$(git branch -r --list 'upstream/*' | grep -vE 'HEAD|gh-pages'); do \
	   n=$$(git rev-list --count main..$$b); \
	   [ "$$n" -gt 0 ] && printf "%4s ahead  %s  %s\n" "$$n" "$$(git log -1 --format=%cs $$b)" "$$b"; \
	 done | sort -k3 -r; true

clean:
	find . -name __pycache__ -type d -prune -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
