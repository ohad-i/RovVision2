#!/bin/bash
#rsync -avzu -e "ssh -p 2222" --exclude="*.AppImage*" --exclude="*.mp4" --exclude="*.pyc" --exclude=".git/" . stereo@localhost:/home/stereo/bluerov/
#export REMOTE_SUB=nanosub@192.168.2.10
source ./setProfile.sh
BASEDIR=$(pwd)
echo subsub | ssh -tt $REMOTE_SUB  "sudo date --set \"$(date)\""

rsync -avzu --exclude="oculus/*fips*" --exclude="libg3logger" --exclude="web" --exclude="ground_control" --exclude="sim" --exclude="*.avi" --exclude=".git" --exclude="installs" --exclude="records" --exclude "*.mp4" --exclude="*.zip" --exclude="*.pyc" --exclude="__pycache__" --exclude="people" --exclude="*.swp" --include="*/"  --include="*.ini" --include="*.c" --include="*.sh" --include="*.py" --include="*.ino" --include='*.json' --include="../hw/oculus/liboculus"  $BASEDIR/.. $REMOTE_SUB:/home/nanosub/proj/RovVision2/
sleep 2
