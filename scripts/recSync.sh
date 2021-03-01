#export REMOTE_SUB=nanosub@192.168.2.10

rsync -avzu --exclude=".git" --include="*/"  --include="*.pkl" --exclude="*" $REMOTE_SUB:/home/nanosub/proj/RovVision2/records $HOME/proj/RovVision2/
sleep 2

