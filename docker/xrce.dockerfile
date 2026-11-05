# Micro XRCE-DDS Agent: passes messages between PX4 and ROS 2
# Builds in one stage and copies the result out, leaving the compilers behind.
FROM ubuntu:24.04 AS build

# Must stay on v2.x: PX4's client is not compatible with v3.x.
ARG XRCE_AGENT_VERSION=v2.4.3

# Basic dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git

RUN git clone --depth 1 -b "$XRCE_AGENT_VERSION" \
        https://github.com/eProsima/Micro-XRCE-DDS-Agent.git /tmp/xrce-agent \
    && cmake -S /tmp/xrce-agent -B /tmp/xrce-agent/build \
    && cmake --build /tmp/xrce-agent/build -j"$(nproc)" \
    && cmake --install /tmp/xrce-agent/build

FROM ubuntu:24.04

COPY --from=build /usr/local /usr/local
RUN ldconfig /usr/local/lib

# Default port PX4 connects to
CMD ["MicroXRCEAgent", "udp4", "-p", "8888"]
