#!/usr/bin/env bash
# Launch headless Gazebo Harmonic (with EGL camera rendering), camera HTTP relay,
# and PX4 SITL attached to the downward-camera rc_cessna model inside the container.

set -euo pipefail

REPO_ROOT="${SUAS_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PX4_SRC="${REPO_ROOT}/src/PX4-Autopilot"
WORLD_NAME="${SUAS_WORLD_NAME:-suas_site}"
CAMERA_PORT="${SUAS_CAMERA_PORT:-8554}"
MODEL_NAME="${SUAS_MODEL_NAME:-rc_cessna_0}"

WORLD_SDF="${REPO_ROOT}/sim/gz/worlds/${WORLD_NAME}.sdf"
if [ ! -f "${WORLD_SDF}" ]; then
    echo "ERROR: World SDF not found: ${WORLD_SDF}" >&2
    exit 1
fi

# Software EGL rendering for macOS Docker (no GPU passthrough) and headless Linux CI
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export MESA_GL_VERSION_OVERRIDE="${MESA_GL_VERSION_OVERRIDE:-4.3}"
export EGL_PLATFORM="${EGL_PLATFORM:-surfaceless}"
export HEADLESS=1

# Include both our repo's models/worlds and PX4's bundled models/worlds
export GZ_SIM_RESOURCE_PATH="${REPO_ROOT}/sim/gz/models:${REPO_ROOT}/sim/gz/worlds:${REPO_ROOT}/worlds:${PX4_SRC}/Tools/simulation/gz/models:${PX4_SRC}/Tools/simulation/gz/worlds:${GZ_SIM_RESOURCE_PATH:-}"
export GZ_SIM_SERVER_CONFIG_PATH="${PX4_SRC}/Tools/simulation/gz/server.config"
export GZ_SIM_SYSTEM_PLUGIN_PATH="${PX4_SRC}/build/px4_sitl_default/src/modules/simulation/gz_plugins:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"

GZ_PID=""
RELAY_PID=""
cleanup() {
    echo "Shutting down Gazebo camera relay and simulation..."
    [ -n "${RELAY_PID}" ] && kill "${RELAY_PID}" 2>/dev/null || true
    [ -n "${GZ_PID}" ] && kill "${GZ_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting headless Gazebo Harmonic with world: ${WORLD_SDF}"
DISPLAY= gz sim -r -s --headless-rendering --verbose=1 "${WORLD_SDF}" &
GZ_PID=$!

# Wait for Gazebo world service to come up before starting PX4
for _ in $(seq 1 40); do
    if gz service -i --service "/world/${WORLD_NAME}/scene/info" 2>/dev/null | grep -q "Service providers"; then
        break
    fi
    sleep 0.5
done

echo "Starting Gazebo camera HTTP relay on http://0.0.0.0:${CAMERA_PORT} (topic /camera)"
python3 "${REPO_ROOT}/sim/gz/camera_relay.py" --topic /camera --port "${CAMERA_PORT}" &
RELAY_PID=$!

cd "${PX4_SRC}"
export PX4_GZ_STANDALONE=1
export PX4_GZ_WORLD="${WORLD_NAME}"
export PX4_GZ_MODEL_NAME="${MODEL_NAME}"

echo "Starting PX4 SITL attached to ${MODEL_NAME} in world ${WORLD_NAME}..."
exec make px4_sitl gz_rc_cessna
