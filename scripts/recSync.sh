#export REMOTE_SUB=nanosub@192.168.2.10

rsync -avzu --progress --remove-source-files --exclude=".git" --include="*/"  --include="*.pkl" --include="*.bin" --exclude="*" $REMOTE_SUB:/home/nanosub/proj/RovVision2/records $HOME/proj/RovVision2/
sleep 2

