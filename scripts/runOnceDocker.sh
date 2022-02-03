#!/bin/bash

#docker run -ti --net=host -e DISPLAY -v /tmp/.X11-unixi --rm $1 bash
# --restart=always 
docker run --privileged -v /dev/bus/usb:/dev/bus/usb -v /dev:/dev -v /proc:/proc -v $HOME/proj:/home/docker/proj -t -i --net=host -e DISPLAY -v /tmp/.X11-unixi --rm $1 bash
#docker run --privileged -v /dev/bus/usb:/dev/bus/usb -v $HOME:/home/docker/ -t -i --net=host -e DISPLAY -v /tmp/.X11-unixi $1 bash
