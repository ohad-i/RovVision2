#!/bin/bash
source ./run_common.sh

SESSION=autoFocus
tmux kill-session -t $SESSION



if [ "$1" = "kill" ]; then
    echo "kill sonar"
    python ../hw/oculus/toggleSonar.py off
    exit 1 
fi



tmux new-session -d -s $SESSION

python ../hw/oculus/toggleSonar.py on

PROJECT_PATH=/home/nanosub/proj/RovVision2/
OCULUS_PATH=hw/oculus/fips-deploy/liboculus/linux-make-debug/
OCULUS=$PROJECT_PATH/hw/oculus/fips-deploy/liboculus/linux-make-debug/oc_client
while [ ! -f $OCULUS ];
do
   echo "build liboculus and oc_client app"
   cd $PROJECT_PATH/hw/oculus/liboculus/ && ./fips build
   sleep 1
done

PIPE="/home/nanosub/tmp/sonar.pipe"
while [ ! -p $PIPE ];
do
   echo "create fifo file"
   mkfifo $PIPE
   sleep 1
done

sleep 3
new_4_win
runShell 0 $OCULUS_PATH "./oc_client -p $PIPE -b 8 -r 1 -g 60"
run 1 hw/oculus/liboculus/python/ "parser.py  -p $PIPE"
#run 2 onboard sonGate.py

