#!/usr/bin/env bash
# Interactive helper pane inside `make up`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

CAMERA_PORT="${CAMERA_PORT:-${SUAS_CAMERA_PORT:-8554}}"

cat <<MSG
SUAS scratch pane
  curl -s http://127.0.0.1:${CAMERA_PORT}/health
  make map / make eval     # OPTIONAL redo / score (mapper auto-spawns after SURVEY)
  make down                # stop tmux + docker (leaves QGC/Foxglove open)
  make sitl CAMERA=0       # plain PX4 world if needed
  Foxglove: ws://localhost:8765  (app opened by make up; bridge starts with make run)
  Layout: Import foxglove_layout.json once if panels look empty
  QGroundControl: opened by make up
MSG

exec bash
