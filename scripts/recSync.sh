#export REMOTE_SUB=nanosub@192.168.2.10

tmux kill-session -t syncRec
tmux new-session -d -s syncRec

tmux send-keys -t syncRec "rsync -avuAXEh --progress --info=progress2 --partial-dir=.rsync-partial --remove-source-files --exclude=".git" --exclude="*.py" --exclude="*.bck" --include="*/" --include="*.pkl" --include="*.bin" $REMOTE_SUB:/home/nanosub/proj/RovVision2/records $HOME/proj/RovVision2/" ENTER
tmux send-keys -t syncRec "sleep 30" ENTER
tmux send-keys -t syncRec "tmux kill-session -t syncRec" ENTER
tmux attach -d
