#!/bin/bash
#rsync -avzu -e "ssh -p 2222" --exclude="*.AppImage*" --exclude="*.mp4" --exclude="*.pyc" --exclude=".git/" . stereo@localhost:/home/stereo/bluerov/
rsync -avzu --exclude=".git" --include="*/" --include="*.c" --include="*.sh" --include="*.py" --include="*.ino" --exclude="*" $HOME/proj/RovVision2/ nanosub@192.168.2.10:/home/nanosub/proj/RovVision2/
sleep 2
