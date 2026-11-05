FROM ubuntu:24.04

RUN apt update && apt install -y \
    sudo \
    bash \
    curl \
    git \
    python3-flake8-blind-except \
    python3-flake8-class-newline \
    python3-flake8-deprecated \
    python3-mypy \
    python3-pip \
    python3-pytest \
    python3-pytest-cov \
    python3-pytest-mock \
    python3-pytest-repeat \
    python3-pytest-rerunfailures \
    python3-pytest-runner \
    python3-pytest-timeout \
    
RUN sudo apt update && sudo apt install locales
RUN sudo locale-gen en_US en_US.UTF-8
RUN sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
ENV LANG="en_US.UTF-8"

RUN sudo add-apt-repository universe

RUN sudo apt install software-properties-common
RUN sudo add-apt-repository universe

ENV ROS_APT_SOURCE_VERSION=curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}'

RUN curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"

RUN sudo dpkg -i /tmp/ros2-apt-source.deb

#create workspace, clone all repo
RUN mkdir -p ~/ros2_jazzy/src
WORKDIR ~/ros2_jazzy
RUN vcs import --input https://raw.githubusercontent.com/ros2/ros2/jazzy/ros2.repos src

# updates ros packages automatically
RUN sudo apt upgrade
RUN sudo apt update

RUN sudo rosdep init
RUN rosdep update
RUN rosdep install --from-paths src --ignore-src -y --skip-keys "fastcdr rti-connext-dds-6.0.1 urdfdom_headers"

RUN sudo apt install ros-jazzy-ros-base

RUN sudo apt ros-dev-tools