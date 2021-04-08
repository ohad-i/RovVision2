#!/bin/bash

tmux kill-session -t updatePIDS
tmux new-session -d -s updatePIDS

CMD="pkill -f plugin.py"
#./sync_onboard.sh && sleep 2 && ssh -t $REMOTE_SUB $CMD

tmux send-keys -t updatePIDS "./sync_onboard.sh && ssh -t $REMOTE_SUB $CMD && tmux kill-session -t updatePIDS" ENTER
#tmux attach -d




