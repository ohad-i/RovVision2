#!/bin/bash


tmux kill-ser
sleep 1

if [ "$1" = "kill" ]; then
    echo "kill all system"
    ssh $REMOTE_SUB "tmux kill-ser"
    exit 1
fi


./run_remote.sh
sleep 10
./run_ground_control.sh
