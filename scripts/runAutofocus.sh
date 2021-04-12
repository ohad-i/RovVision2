#!/bin/bash

SESSION=autoFocus
tmux kill-session -t $SESSION
tmux new-session -d -s $SESSION

PROJECT_PATH=/home/nanosub/proj/RovVision2/

tmux send-keys -t $SESSION "cd $PROJECT_PATH/utils" ENTER
tmux send-keys -t $SESSION "python3 autoFocus.py" ENTER

#tmux send-keys -t $SESSION "tmux kill-session -t $SESSION" ENTER
#tmux attach -d

