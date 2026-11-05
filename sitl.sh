#!/usr/bin/env bash

# Launch QGroundControl First!
# If you use docker desktop, go to Docker Desktop → Settings → Resources → Network → Enable host networkin
# RUN THIS FROM REPO ROOT (suas-26-27)

## helpful for debugging
# -e: exit on non-zero exit status
# -x: print commands to out pipe
# -u: fail on undefined variable
# -o pipefail: if any command in a pipeline fails, cascade the error and the entire script fails
set -euxo pipefail

PX4_VERSION="v1.17.0"

# Parse arguments: check for --rebuild flag and forward any remaining arguments
REBUILD=0
RUN_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--rebuild" ]]; then
        REBUILD=1
    else
        RUN_ARGS+=("$arg")
    fi
done

# Only checkout and update submodules if not already at PX4_VERSION
CURRENT_PX4_COMMIT="$(git -C src/PX4-Autopilot rev-parse HEAD 2>/dev/null || true)"
TARGET_PX4_COMMIT="$(git -C src/PX4-Autopilot rev-parse "$PX4_VERSION^{commit}" 2>/dev/null || true)"

if [ ! -f "src/PX4-Autopilot/Makefile" ] || [ -z "$CURRENT_PX4_COMMIT" ] || [ "$CURRENT_PX4_COMMIT" != "$TARGET_PX4_COMMIT" ]; then
    echo "Initializing or updating PX4 submodules for $PX4_VERSION..."
    git submodule update --init --recursive
    git -C src/PX4-Autopilot checkout "$PX4_VERSION"
    git -C src/PX4-Autopilot submodule update --init --recursive
fi

IMAGE_NAME="suas-px4-sitl"
IMAGE_TAG="$IMAGE_NAME:$PX4_VERSION"
DOCKERFILE="docker/sitl.dockerfile"

# Mount the whole repo (not just the submodule) at the same absolute path
# inside the container. src/PX4-Autopilot/.git is a submodule gitlink
# ("gitdir: ../../.git/modules/src/PX4-Autopilot") that resolves relative
# to this layout, so PX4's CMake version check only works if the
# surrounding .git/modules structure comes along with it.

REPO_ROOT="$(pwd)"

# PX4 is stored at ./src
# but since it's a git submodule, it's commits and refs are all stored in .git/submodules
# since PX4 runs `git describe`, we need it to be able to see the actual source code
PX4_SRC="${REPO_ROOT}/src/PX4-Autopilot"

# Only build the image if it doesn't already exist or if --rebuild is explicitly requested
if [[ "$REBUILD" -eq 1 ]] || ! docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
    echo "Building Docker image $IMAGE_TAG..."
    docker build -t "$IMAGE_TAG" -f "$DOCKERFILE" .
else
    echo "Docker image $IMAGE_TAG already exists. Skipping build (pass --rebuild to force)."
fi

# Enable access to xhost from the container (for Gazebo GUI, if not headless)
# xhost +local:root

docker run -it --rm \
    --env=LOCAL_USER_ID="$(id -u)" \
    --volume="${REPO_ROOT}:${REPO_ROOT}:rw" \
    --volume=/tmp/.X11-unix:/tmp/.X11-unix:rw \
    --env=DISPLAY="${DISPLAY:-:0}" \
    --network host \
    --workdir="${PX4_SRC}" \
    --name=suas-px4-sitl \
    "$IMAGE_TAG" "${RUN_ARGS[@]+"${RUN_ARGS[@]}"}"

# Stop with docker stop suas-px4-sitl
