#!/usr/bin/env bash
# Launch the full SUAS SITL mapping stack in one tmux session:
#   host apps: QGroundControl + Foxglove Studio (ws://localhost:8765)
#   pane 0: PX4 + Gazebo + nadir camera (sitl.sh)
#   pane 1: autonomous mission (waits for camera, then make run)
#   pane 2: scratch shell (curl health, make map/eval)
#
# Usage (from repo root):
#   make up
#   make up MISSION=loop
#   SUAS_SKIP_APPS=1 make up   # tmux/SITL only
#   make down

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

SESSION="${SUAS_TMUX_SESSION:-suas}"
MISSION="${MISSION:-mapping_sitl}"
CAMERA_PORT="${SUAS_CAMERA_PORT:-8554}"
SITL_WAIT_S="${SUAS_SITL_WAIT_S:-180}"
SKIP_APPS="${SUAS_SKIP_APPS:-0}"
FOXGLOVE_WS="${SUAS_FOXGLOVE_WS:-ws://localhost:8765}"
LAYOUT_PATH="${REPO_ROOT}/foxglove_layout.json"

open_host_apps() {
    if [[ "${SKIP_APPS}" != "0" ]]; then
        echo "[apps] Skipping QGroundControl / Foxglove (SUAS_SKIP_APPS=${SKIP_APPS})"
        return 0
    fi
    if [[ "$(uname -s)" != "Darwin" ]]; then
        echo "[apps] Host app launch is macOS-only; open QGC + Foxglove yourself."
        return 0
    fi

    if [[ -d "/Applications/QGroundControl.app" ]]; then
        echo "[apps] Opening QGroundControl..."
        open -a QGroundControl || true
    else
        echo "[apps] QGroundControl.app not found in /Applications (install from qgroundcontrol.com)" >&2
    fi

    if [[ -d "/Applications/Foxglove.app" ]]; then
        echo "[apps] Opening Foxglove Studio → ${FOXGLOVE_WS}"
        # Deep-link opens a WebSocket connection; import foxglove_layout.json once via Layout → Import.
        open "foxglove://open?ds=foxglove-websocket&ds.url=$(python3 -c "import urllib.parse; print(urllib.parse.quote('${FOXGLOVE_WS}', safe=''))")" \
            || open -a Foxglove || true
        if [[ -f "${LAYOUT_PATH}" ]]; then
            echo "[apps] Foxglove layout: Layout → Import from file… → ${LAYOUT_PATH}"
        fi
    else
        echo "[apps] Foxglove.app not found (brew install --cask foxglove)" >&2
        echo "[apps] Browser fallback: https://app.foxglove.dev → connect ${FOXGLOVE_WS}"
        open "https://app.foxglove.dev" 2>/dev/null || true
    fi
}

if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is required. Install with: brew install tmux" >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required and must be running." >&2
    exit 1
fi

make venv
open_host_apps

if tmux has-session -t "${SESSION}" 2>/dev/null; then
    echo "Session '${SESSION}' already exists — attaching."
    echo "  Detach: Ctrl-b d    Kill: make down"
    exec tmux attach -t "${SESSION}"
fi

docker stop suas-px4-sitl >/dev/null 2>&1 || true

# pane 0 — SITL (camera + suas_site via Makefile)
tmux new-session -d -s "${SESSION}" -n stack -c "${REPO_ROOT}" \
    "make sitl; echo; echo '[sitl] exited — press enter'; read"

# pane 1 — wait for camera, then mission
tmux split-window -h -t "${SESSION}:stack" -c "${REPO_ROOT}" \
    "MISSION='${MISSION}' CAMERA_PORT='${CAMERA_PORT}' SITL_WAIT_S='${SITL_WAIT_S}' bash '${REPO_ROOT}/scripts/dev_wait_and_run.sh'"

# pane 2 — scratch
tmux split-window -v -t "${SESSION}:stack.1" -c "${REPO_ROOT}" \
    "CAMERA_PORT='${CAMERA_PORT}' bash '${REPO_ROOT}/scripts/dev_scratch.sh'"

tmux select-pane -t "${SESSION}:stack.0"
tmux set-option -t "${SESSION}" mouse on
tmux set-option -t "${SESSION}" remain-on-exit on

echo "Started tmux session '${SESSION}' (sitl | mission | scratch)"
echo "  QGC + Foxglove launched on host (telemetry after make run connects)"
echo "  detach: Ctrl-b d"
echo "  stop:   make down   (leaves QGC/Foxglove running)"
exec tmux attach -t "${SESSION}"
