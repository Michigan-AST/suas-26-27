# Ubuntu
FROM ubuntu:24.04

# Basic dependencies
RUN apt update && apt install -y \
    bash \
    curl \
    git \
    sudo


COPY src/PX4-Autopilot/Tools/setup/ /tmp/px4-setup/
RUN RUNS_IN_DOCKER=true bash /tmp/px4-setup/ubuntu.sh && rm -rf /tmp/px4-setup

# the container runs as root but the source is bind-mounted in from the
# host (owned by the host user), so git refuses it as "dubious ownership"
RUN git config --global --add safe.directory '*'

ENV HEADLESS=1

WORKDIR /PX4-Autopilot

# make px4_sitl gz_x500 (Make gazebo simulation for the x500 drone)
CMD ["make", "px4_sitl", "gz_x500"]

# to make for an ARM controller instead (like on the drone)
# we have to run `make px4_fmu-v6x_default` instead of 
# `make px4_sitl`.
