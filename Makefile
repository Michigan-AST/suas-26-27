# Use a different interpreter with: make venv PYTHON=python3.11
PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

.DEFAULT_GOAL := venv
.PHONY: venv run test help

# Reinstall dependencies only when the requirements or setup instructions change.
venv: $(VENV)/.requirements-installed

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

$(VENV)/.requirements-installed: requirements.txt Makefile | $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip check
	touch $@

# The simulator must already be running. This starts the flight instructions.
run: venv
	$(VENV_PYTHON) scripts/drone_control.py

test: venv
	$(VENV_PYTHON) -m unittest discover -s tests

help:
	@echo "make venv  Create .venv and install pinned dependencies (default)."
	@echo "make run   Run flight instructions; starts flying when SITL is ready."
	@echo "make test  Run Python tests."
	@echo "Override Python with: make venv PYTHON=python3.11"
