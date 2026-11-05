# ROS 2 Jazzy on Ubuntu 24.04
FROM ros:jazzy-ros-base

# PX4_MSGS_BRANCH must match PX4_VERSION in sitl.sh, or topics may not match.
ARG PX4_MSGS_BRANCH=release/1.17

# Basic dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# ROS workspace with the PX4 message definitions
WORKDIR /ros2_ws
RUN git clone --depth 1 -b "$PX4_MSGS_BRANCH" \
        https://github.com/PX4/px4_msgs.git src/px4_msgs \
    && . /opt/ros/jazzy/setup.sh \
    && colcon build --packages-select px4_msgs

# Make the workspace available to every command the container runs
RUN sed -i 's|^source "/opt/ros/$ROS_DISTRO/setup.bash".*|&\nsource /ros2_ws/install/setup.bash|' /ros_entrypoint.sh \
    && grep -q '/ros2_ws/install/setup.bash' /ros_entrypoint.sh
RUN echo 'source /ros2_ws/install/setup.bash' >> /root/.bashrc

CMD ["bash"]
