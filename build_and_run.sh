#!/usr/bin/env bash
set -euo pipefail

# Stop on a failed build so an older suas image cannot be launched.
docker build -f docker/Dockerfile -t suas .

open -a QGroundControl

docker run --rm -it --name suas-sitl --network host -e HEADLESS=1 suas


# Stop with: docker stop suas-sitl
