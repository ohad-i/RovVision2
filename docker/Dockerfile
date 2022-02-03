FROM ubuntu:20.04
FROM ubuntu:bionic

ENV DEBIAN_FRONTEND=noninteractive

######## some base installs ########
RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install gawk git
RUN apt-get -y install xterm
RUN apt-get -y install build-essential
RUN apt-get -y install curl
RUN apt-get -y install vim
RUN apt-get -y install wget tmux
RUN apt-get -y install bash-completion
RUN apt-get -y install python3-pip
RUN apt-get -y install ipython3
RUN apt-get -y install locate
RUN apt-get -y install net-tools
RUN apt-get -y install usbutils
RUN apt-get -y install git-cola
RUN apt-get -y install software-properties-common
RUN apt-get -y install libasound-dev
RUN apt-get -y install mesa-utils 
RUN apt-get -y install libgl1-mesa-glx
RUN apt-get -y install ipython
RUN apt-get -y install python3-tk
RUN apt-get -y install libjpeg-dev zlib1g-dev
#RUN apt-get update

RUN pip3 install scikit-build
RUN pip3 install cmake
RUN pip3 install pybullet 
RUN pip3 install pygame 
#RUN pip3 install opencv-contrib-python 
RUN pip3 install dill numpy zmq scikit-image matplotlib
ENV CMAKE_MAKE_PROGRAM="make -j 6"
RUN CMAKE_ARGS="-DOPENCV_ENABLE_NONFREE=ON" pip3 install -v --no-binary=opencv-contrib-python opencv-contrib-python==4.5.3.56
#RUN pip3 install opencv-python 

ENV DEBIAN_FRONTEND=

ENV ROV_TYPE=4
ENV ROV_IP=192.168.3.10
ENV WORK_DIR=/home/docker INSTALL_DIR=/opt
WORKDIR ${WORK_DIR}

######## limesdr install ###########
#packages for soapysdr available at myriadrf PPA
RUN add-apt-repository -y ppa:myriadrf/drivers
RUN apt-get update

#install core library and build dependencies
RUN apt-get -y install git g++ cmake libsqlite3-dev

RUN apt-get clean
RUN apt-get autoclean
RUN apt-get autoremove -y

######## user settings ######
RUN apt-get install sudo
RUN useradd -u 1000 docker
RUN echo "docker:docker" | chpasswd
RUN echo "root:root" | chpasswd
RUN echo 'root:Docker!' | chpasswd
RUN echo "docker ALL=(ALL:ALL) NOPASSWD:ALL" >> /etc/sudoers

USER docker

#RUN sudo udevadm control --reload-rules || echo "done" 
#RUN udevadm trigger

# All users can use /home/user as their home directory
ENV HOME=/home/docker

WORKDIR /home/docker


####### handle limesdr-mini rules and permissions
RUN sudo usermod -a -G plugdev docker
RUN sudo usermod -aG root docker

RUN sudo chown -R docker:docker /home/docker
#RUN sudo service udev restart
