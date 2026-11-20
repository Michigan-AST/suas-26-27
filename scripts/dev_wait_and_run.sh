#!/usr/bin/env bash
# Wait for Gazebo camera HTTP relay, then start the autonomous mission.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

MISSION="${MISSION:-mapping_sitl}"
CAMERA_PORT="${CAMERA_PORT:-${SUAS_CAMERA_PORT:-8554}}"
SITL_WAIT_S="${SITL_WAIT_S:-${SUAS_SITL_WAIT_S:-180}}"

echo "[mission] Waiting up to ${SITL_WAIT_S}s for camera on :${CAMERA_PORT} ..."
deadline=$((SECONDS + SITL_WAIT_S))
while (( SECONDS < deadline )); do
    if curl -sf "http://127.0.0.1:${CAMERA_PORT}/health" 2>/dev/null \
        | grep -q '"ready"[[:space:]]*:[[:space:]]*true'; then
        echo "[mission] Camera ready — starting make run ${MISSION}"
        exec make run "${MISSION}"
    fi
    sleep 1
done

echo "[mission] Timed out waiting for camera. Check the sitl pane." >&2
echo "  curl -s http://127.0.0.1:${CAMERA_PORT}/health" >&2
exit 1
