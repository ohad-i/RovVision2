#!/bin/bash
#rsync -avzu -e "ssh -p 2222" --exclude="*.AppImage*" --exclude="*.mp4" --exclude="*.pyc" --exclude=".git/" . stereo@localhost:/home/stereo/bluerov/
#export REMOTE_SUB=nanosub@192.168.2.10

echo subsub | ssh -tt $REMOTE_SUB  "sudo date --set \"$(date)\""

rsync -avzu --exclude=".git" --include="*/"  --include="*.ini" --include="*.c" --include="*.sh" --include="*.py" --include="*.ino" --exclude="*" $HOME/proj/RovVision2/ $REMOTE_SUB:/home/nanosub/proj/RovVision2/
sleep 2
