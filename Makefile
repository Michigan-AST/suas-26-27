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

# Camera + SUAS site world is the default mission path (CAMERA=0 for plain PX4 worlds).
CAMERA ?= 1
CAMERA_PORT ?= 8554
# Built-in PX4 world name, or a custom ./worlds/<WORLD>.sdf (without .sdf). Used when CAMERA=0.
WORLD ?= suas_site

MISSION ?= mapping_sitl
# Default CAPTURE = newest directory under captures/ (override with CAPTURE=... or positional arg)
CAPTURE ?= $(shell ls -1dt captures/*/ 2>/dev/null | head -1 | sed 's:/*$$::')

# Allow positional syntax like 'make run loop' or 'make map smoke_cli'
ifeq (run,$(firstword $(MAKECMDGOALS)))
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(RUN_ARGS),)
    MISSION := $(firstword $(RUN_ARGS))
    $(eval $(RUN_ARGS):;@:)
  endif
endif
ifeq ($(firstword $(MAKECMDGOALS)),$(filter $(firstword $(MAKECMDGOALS)),map eval))
  CAPTURE_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(CAPTURE_ARGS),)
    CAPTURE_ARG := $(firstword $(CAPTURE_ARGS))
    ifeq ($(wildcard $(CAPTURE_ARG)/.),)
      ifneq ($(wildcard captures/$(CAPTURE_ARG)/.),)
        CAPTURE := captures/$(CAPTURE_ARG)
      else
        CAPTURE := $(CAPTURE_ARG)
      endif
    else
      CAPTURE := $(CAPTURE_ARG)
    endif
    $(eval $(CAPTURE_ARGS):;@:)
  endif
endif

.DEFAULT_GOAL := venv
.PHONY: venv sitl run foxglove world map eval test up down clean help

# Reinstall dependencies only when the requirements or setup instructions change.
venv: $(VENV)/.requirements-installed

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

$(VENV)/.requirements-installed: requirements.txt Makefile | $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip check
	touch $@

# Launch QGroundControl first! If using Docker Desktop, enable host networking.
# Default: CAMERA=1 runs sim/gz/launch_sim.sh (suas_site + 2 Hz nadir camera).
# Opt out: make sitl CAMERA=0 WORLD=moving_platform
# Stop with: docker stop suas-px4-sitl  (or make down)
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
	if [ "$(CAMERA)" = "1" ]; then \
		if [ ! -f "$(CURDIR)/sim/gz/worlds/$(WORLD).sdf" ]; then \
			echo "Generating Gazebo world '$(WORLD)'..."; \
			$(VENV_PYTHON) worlds/suas_site/build_site.py; \
		fi; \
		EFFECTIVE_ARGS='bash $(CURDIR)/sim/gz/launch_sim.sh'; \
	else \
		EFFECTIVE_ARGS='$(SITL_ARGS)'; \
	fi; \
	if [ -t 0 ] && [ -t 1 ]; then TTY_FLAG="-it"; else TTY_FLAG="-i"; fi; \
	set -- \
		--env=LOCAL_USER_ID="$$(id -u)" \
		--env=PX4_SIM_SPEED_FACTOR="$(SPEED)" \
		--env=PX4_GZ_WORLD="$(WORLD)" \
		--env=SUAS_REPO_ROOT="$(CURDIR)" \
		--env=SUAS_WORLD_NAME="$(WORLD)" \
		--env=SUAS_CAMERA_PORT="$(CAMERA_PORT)" \
		--volume="$(CURDIR):$(CURDIR):rw" \
		--volume=/tmp/.X11-unix:/tmp/.X11-unix:rw \
		--env=DISPLAY="$${DISPLAY:-:0}" \
		--network host \
		--workdir="$(PX4_SRC)" \
		--name=suas-px4-sitl; \
	if [ "$(CAMERA)" != "1" ] && [ -f "$(CURDIR)/worlds/$(WORLD).sdf" ]; then \
		set -- "$$@" --volume="$(CURDIR)/worlds/$(WORLD).sdf:$(PX4_SRC)/Tools/simulation/gz/worlds/$(WORLD).sdf:ro"; \
	fi; \
	docker run $$TTY_FLAG --rm "$$@" "$(SITL_IMAGE)" $$EFFECTIVE_ARGS

# The simulator must already be running. This starts the autonomous mission loop.
run: venv
	$(VENV_PYTHON) scripts/drone_control.py --mission $(MISSION)

# Stream SITL telemetry + site terrain/targets to Foxglove Studio in 3D (ws://localhost:8765)
foxglove: venv
	$(VENV_PYTHON) scripts/foxglove_bridge.py

# Regenerate worlds/suas_site/ (scene.json, dem.npz, ground_texture.png) and sim/gz/worlds/suas_site.sdf
world: venv
	$(VENV_PYTHON) worlds/suas_site/build_site.py

# Build Risk Mapping orthomosaic from a capture folder.
#   make map                  -> newest captures/*
#   make map smoke_cli        -> captures/smoke_cli
map: venv
	@test -n "$(CAPTURE)" || (echo "No captures found. Run a mapping mission first, or: make map smoke_cli" && exit 1)
	@echo "Mapping $(CAPTURE)"
	PYTHONPATH=scripts $(VENV_PYTHON) -m perception.mapper $(CAPTURE)

# Score SITL capture vs scene.json ground truth (coverage %, geolocation error, map time).
eval: venv
	@test -n "$(CAPTURE)" || (echo "No captures found. Run a mapping mission first, or: make eval smoke_cli" && exit 1)
	@echo "Evaluating $(CAPTURE)"
	PYTHONPATH=scripts $(VENV_PYTHON) -m perception.evaluate $(CAPTURE)

test: venv
	$(VENV_PYTHON) -m unittest discover -s tests

# One-shot: open QGC+Foxglove, tmux with make sitl + make run + scratch.
up: venv
	@command -v tmux >/dev/null || (echo "Install tmux first: brew install tmux" && exit 1)
	bash scripts/dev_up.sh

down:
	bash scripts/dev_down.sh

# Remove CMake cache and build directories (falls back to Docker for root-owned SITL files)
clean:
	rm -rf build src/PX4-Autopilot/build 2>/dev/null || \
		docker run --rm -v "$(CURDIR):/work" -w /work alpine rm -rf build src/PX4-Autopilot/build

help:
	@echo "make up        Open QGC+Foxglove, tmux: sitl + make run + scratch (brew install tmux)."
	@echo "make down      Kill tmux session and stop suas-px4-sitl (leaves QGC/Foxglove open)."
	@echo "make venv      Create .venv and install pinned dependencies (default)."
	@echo "make sitl      Start PX4 + Gazebo (CAMERA=1 default; CAMERA=0 WORLD=moving_platform; SPEED=2)."
	@echo "make run       Run autonomous mission (default: mapping_sitl; also 'make run loop')."
	@echo "make foxglove  Stream live telemetry + terrain to Foxglove Studio (3D viewer)."
	@echo "make world     Regenerate SUAS SITL world bundle and Gazebo SDF."
	@echo "make map       OPTIONAL redo of orthomosaic (flight auto-spawns mapper after SURVEY)."
	@echo "make eval      OPTIONAL scorecard: coverage % + geolocation vs scene.json."
	@echo "make test      Run Python tests."
	@echo "make clean     Clear CMake cache and build directories."
	@echo "Override Python with: make venv PYTHON=python3.11"
