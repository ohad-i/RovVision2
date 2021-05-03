#export REMOTE_SUB=nanosub@192.168.2.10

REMOTE_WIFI_SUB=nanosub@192.168.204.58

tmux kill-session -t wifiSyncRec
tmux new-session -d -s wifiSyncRec

tmux send-keys -t wifiSyncRec "rsync -avuAXEh --progress --partial-dir=.rsync-partial --remove-source-files --exclude=".git" --include="*/"  --include="*.pkl" --include="*.bin" $REMOTE_WIFI_SUB:/home/nanosub/proj/RovVision2/records $HOME/proj/RovVision2/" ENTER
tmux send-keys -t wifiSyncRec "sleep 30" ENTER
tmux send-keys -t wifiSyncRec "tmux kill-session -t syncRec" ENTER
tmux attach -d
