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

# make sure PX4 has all of its dependencies (like gazebo, for this sitl script)
git submodule update --init --recursive

IMAGE_NAME="suas-px4-sitl"
IMAGE_TAG="$IMAGE_NAME:latest"
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

docker build -t "$IMAGE_TAG" -f "$DOCKERFILE" .

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
    "$IMAGE_TAG" "$@"

# Stop with docker stop suas-px4-sitl
