#!/usr/bin/env bash
# Thin wrapper kept for muscle memory. Prefer: make sitl
# Forwards common flags into the Makefile sitl target.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${REPO_ROOT}"

CAMERA=1
SPEED="${PX4_SIM_SPEED_FACTOR:-}"
REBUILD=0
WORLD="${PX4_GZ_WORLD:-suas_site}"
CAMERA_PORT="${SUAS_CAMERA_PORT:-8554}"
EXTRA=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rebuild) REBUILD=1; shift ;;
        --speed|-s) SPEED="$2"; shift 2 ;;
        --speed=*) SPEED="${1#*=}"; shift ;;
        --camera) CAMERA=1; shift ;;
        --no-camera) CAMERA=0; shift ;;
        --world) WORLD="$2"; shift 2 ;;
        --world=*) WORLD="${1#*=}"; shift ;;
        --camera-port) CAMERA_PORT="$2"; shift 2 ;;
        --camera-port=*) CAMERA_PORT="${1#*=}"; shift ;;
        *) EXTRA+=("$1"); shift ;;
    esac
done

ARGS=(sitl CAMERA="${CAMERA}" WORLD="${WORLD}" CAMERA_PORT="${CAMERA_PORT}" REBUILD="${REBUILD}")
if [[ -n "${SPEED}" ]]; then
    ARGS+=(SPEED="${SPEED}")
fi
if [[ ${#EXTRA[@]} -gt 0 ]]; then
    ARGS+=(SITL_ARGS="${EXTRA[*]}")
fi

exec make "${ARGS[@]}"
