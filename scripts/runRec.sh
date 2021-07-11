#export REMOTE_SUB=nanosub@192.168.2.10

PANE_NAME=runRec
tmux kill-session -t $PANE_NAME
tmux new-session -d -s $PANE_NAME

SKIP=""
if [ ! -z "$2" ]
then
     if [ "$2" -gt 0 ]
     then
	SKIP="-s $2"
     fi
fi

SAVE_AVI=""
if [ ! -z "$3" ]
then
     if [ "$3" -lt 1 ]
     then
	SAVE_AVI="-V"
     fi
fi

SAVE_TIFF=""
if [ ! -z "$4" ]
then
     if [ "$4" -lt 1 ]
     then
	SAVE_TIFF="-t"
     fi
fi

FREE_RUN=""
if [ ! -z "$5" ]
then
     if [ "$5" -lt 1 ]
     then
	FREE_RUN="-f -q"
     fi
fi



tmux send-keys -t $PANE_NAME "cd ../utils/ && python player.py -r $1 $SKIP $SAVE_AVI $SAVE_TIFF $FREE_RUN && sleep 120 && tmux kill-session -t $PANE_NAME" ENTER
#tmux attach -d
