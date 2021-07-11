#export REMOTE_SUB=nanosub@192.168.2.10

PANE_NAME=runRec
tmux kill-session -t $PANE_NAME
tmux new-session -d -s $PANE_NAME

tmux send-keys -t $PANE_NAME "cd ../utils/ && python player.py -r $1 && sleep 120 && tmux kill-session -t $PANE_NAME" ENTER
#tmux attach -d
