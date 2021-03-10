#export REMOTE_SUB=nanosub@192.168.2.10

tmux kill-session -t syncRec
tmux new-session -d -s syncRec

tmux send-keys "rsync -avzu --progress --remove-source-files --exclude=".git" --include="*/"  --include="*.pkl" --include="*.bin" --exclude="*" $REMOTE_SUB:/home/nanosub/proj/RovVision2/records $HOME/proj/RovVision2/" ENTER
tmux send-keys "sleep 300" ENTER
tmux send-keys "tmux kill-session -t syncRec" ENTER
