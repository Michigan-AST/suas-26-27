# you should probably run this with nohup

# Use a different interpreter with: make venv PYTHON=python3.11
PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

PX4_VERSION ?= v1.17.0
SITL_IMAGE := suas-px4-sitl:$(PX4_VERSION)
SITL_DOCKERFILE := docker/px4.dockerfile
PX4_SRC := $(CURDIR)/src/PX4-Autopilot
REBUILD ?= 0
SPEED ?= $(PX4_SIM_SPEED_FACTOR)
SITL_ARGS ?=

# Built-in PX4 world name, or a custom ./worlds/<WORLD>.sdf (without .sdf)
WORLD ?= moving_platform

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
.PHONY: venv sitl run foxglove test clear help

# Reinstall dependencies only when the requirements or setup instructions change.
venv: $(VENV)/.requirements-installed

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

$(VENV)/.requirements-installed: requirements.txt Makefile | $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip check
	touch $@

# Launch QGroundControl first! If using Docker Desktop, enable host networking.
# Mount the whole repo (not just the submodule) at the same absolute path
# inside the container. src/PX4-Autopilot/.git is a submodule gitlink
# ("gitdir: ../../.git/modules/src/PX4-Autopilot") that resolves relative
# to this layout, so PX4's CMake version check only works if the
# surrounding .git/modules structure comes along with it.
# Stop with: docker stop suas-px4-sitl
sitl:
	@set -eu; \
	CURRENT_PX4_COMMIT="$$(git -C src/PX4-Autopilot rev-parse HEAD 2>/dev/null || true)"; \
	TARGET_PX4_COMMIT="$$(git -C src/PX4-Autopilot rev-parse "$(PX4_VERSION)^{commit}" 2>/dev/null || true)"; \
	if [ ! -f "src/PX4-Autopilot/Makefile" ] || [ -z "$$CURRENT_PX4_COMMIT" ] || [ "$$CURRENT_PX4_COMMIT" != "$$TARGET_PX4_COMMIT" ]; then \
		echo "Initializing or updating PX4 submodules for $(PX4_VERSION)..."; \
		git submodule update --init --recursive; \
		git -C src/PX4-Autopilot checkout "$(PX4_VERSION)"; \
		git -C src/PX4-Autopilot submodule update --init --recursive; \
	fi; \
	if [ "$(REBUILD)" = "1" ] || ! docker image inspect "$(SITL_IMAGE)" >/dev/null 2>&1; then \
		echo "Building Docker image $(SITL_IMAGE)..."; \
		docker build -t "$(SITL_IMAGE)" -f "$(SITL_DOCKERFILE)" .; \
	else \
		echo "Docker image $(SITL_IMAGE) already exists. Skipping build (pass REBUILD=1 to force)."; \
	fi; \
	if [ -t 0 ] && [ -t 1 ]; then TTY_FLAG="-it"; else TTY_FLAG="-i"; fi; \
	set -- \
		--env=LOCAL_USER_ID="$$(id -u)" \
		--env=PX4_SIM_SPEED_FACTOR="$(SPEED)" \
		--env=PX4_GZ_WORLD="$(WORLD)" \
		--volume="$(CURDIR):$(CURDIR):rw" \
		--volume=/tmp/.X11-unix:/tmp/.X11-unix:rw \
		--env=DISPLAY="$${DISPLAY:-:0}" \
		--network host \
		--workdir="$(PX4_SRC)" \
		--name=suas-px4-sitl; \
	if [ -f "$(CURDIR)/worlds/$(WORLD).sdf" ]; then \
		set -- "$$@" --volume="$(CURDIR)/worlds/$(WORLD).sdf:$(PX4_SRC)/Tools/simulation/gz/worlds/$(WORLD).sdf:ro"; \
	fi; \
	docker run $$TTY_FLAG --rm "$$@" "$(SITL_IMAGE)" $(SITL_ARGS)

# The simulator must already be running. This starts the autonomous mission loop.
run: venv
	$(VENV_PYTHON) scripts/drone_control.py --mission $(MISSION)

# Stream SITL telemetry to Foxglove Studio in 3D (listening on ws://localhost:8765)
foxglove: venv
	$(VENV_PYTHON) scripts/foxglove_bridge.py

test: venv
	$(VENV_PYTHON) -m unittest discover -s tests

# Remove CMake cache and build directories (falls back to Docker for root-owned SITL files)
clean:
	rm -rf build src/PX4-Autopilot/build 2>/dev/null || \
		docker run --rm -v "$(CURDIR):/work" -w /work alpine rm -rf build src/PX4-Autopilot/build

help:
	@echo "make venv      Create .venv and install pinned dependencies (default)."
	@echo "make sitl      Start PX4 + Gazebo SITL container (WORLD=default, SPEED=2, REBUILD=1)."
	@echo "make run       Run autonomous mission loop (or 'make run loop', 'make run MISSION=flight_line_1')."
	@echo "make foxglove  Stream live telemetry to Foxglove Studio (3D viewer)."
	@echo "make test      Run Python tests."
	@echo "make clear     Clear CMake cache and build directories."
	@echo "Override Python with: make venv PYTHON=python3.11"
