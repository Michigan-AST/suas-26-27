# Ubuntu
FROM ubuntu:24.04


# Basic dependencies
RUN apt update

RUN apt install -y \
    bash \
    curl \
    git

# Install PX4 Autopilot
RUN git clone https://github.com/PX4/PX4-Autopilot.git

# ------ Install Simulation Dependencies --------
WORKDIR /PX4-Autopilot

# Update submodules of PX4-Autopilot
RUN git submodule update --init --recursive 

# Run the setup script for Ubuntu to install dependencies
RUN RUNS_IN_DOCKER=true bash ./Tools/setup/ubuntu.sh 

# Build PX4 SITL for Gazebo
RUN make px4_sitl_default

# Headless mode (no GUI)
ENV HEADLESS=1

# make px4_sitl gz_x500 (Make gazebo simulation for the x500 drone)
CMD ["make", "px4_sitl", "gz_x500"]

# Make sure host networking is on in docker desktop
# (Settings -> Resources -> Network -> Enable Host Networking)
# Then, open qgroundcontrol on the host machine:
# Auto-connect on 14550 and 14580 

