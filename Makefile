# Use a different interpreter with: make venv PYTHON=python3.11
PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

MISSION ?= default

# Allow positional syntax like 'make run loop' or 'make run flight_line_1'
ifeq (run,$(firstword $(MAKECMDGOALS)))
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(RUN_ARGS),)
    MISSION := $(firstword $(RUN_ARGS))
    $(eval $(RUN_ARGS):;@:)
  endif
endif

.DEFAULT_GOAL := venv
.PHONY: venv run foxglove test help

# Reinstall dependencies only when the requirements or setup instructions change.
venv: $(VENV)/.requirements-installed

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

$(VENV)/.requirements-installed: requirements.txt Makefile | $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip check
	touch $@

# The simulator must already be running. This starts the autonomous mission loop.
run: venv
	$(VENV_PYTHON) scripts/drone_control.py --mission $(MISSION)

# Stream SITL telemetry to Foxglove Studio in 3D (listening on ws://localhost:8765)
foxglove: venv
	$(VENV_PYTHON) scripts/foxglove_bridge.py

test: venv
	$(VENV_PYTHON) -m unittest discover -s tests

help:
	@echo "make venv      Create .venv and install pinned dependencies (default)."
	@echo "make run       Run autonomous mission loop (or 'make run loop', 'make run MISSION=flight_line_1')."
	@echo "make foxglove  Stream live telemetry to Foxglove Studio (3D viewer)."
	@echo "make test      Run Python tests."
	@echo "Override Python with: make venv PYTHON=python3.11"
