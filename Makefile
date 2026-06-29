# Cross-platform venv python (no activation needed).
ifeq ($(OS),Windows_NT)
PY ?= .venv/Scripts/python.exe
else
PY ?= .venv/bin/python
endif

.DEFAULT_GOAL := help
.PHONY: help install dev console lint type test eval check docker-build clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Create venv and install the project with dev deps
	python -m venv .venv
	$(PY) -m pip install -U pip
	$(PY) -m pip install -e ".[dev]"

dev:  ## Run the worker connected to LiveKit (needs LIVEKIT_*)
	$(PY) -m voice_agent_pizzeria.agent dev

console:  ## Talk to the agent locally in the terminal
	$(PY) -m voice_agent_pizzeria.agent console

lint:  ## Ruff lint
	$(PY) -m ruff check .

type:  ## Mypy (strict)
	$(PY) -m mypy

test:  ## Run unit tests (evals skipped)
	$(PY) -m pytest -q

eval:  ## Run live LLM-as-judge evals (POSIX shell; needs OPENAI_API_KEY)
	RUN_LIVE_EVALS=1 $(PY) -m pytest tests/test_evals.py -v

check: lint type test  ## Lint + type + test (the CI gate)

docker-build:  ## Build the worker container image
	docker build -t voice-agent-pizzeria .

clean:  ## Remove caches (keeps .venv)
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
