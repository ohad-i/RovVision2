#!/bin/bash
source run_common.sh


#tmux select-pane -t 1
#tmux send-keys C-c ENTER
#sleep 0.5
#tmux send-keys C-c ENTER
#tmux send-keys ENTER
## Kill camera
pkill -f ids
sleep 3


tmux kill-ser


if [ "$1" = "kill" ]; then
    echo "kill run_onboard"
    exit 1 
fi

if [ ! -v SIM ]
then
tmux kill-session -t dronelab
tmux new-session -d -s dronelab
PROJECT_PATH=../
else
PROJECT_PATH=/home/nanosub/proj/RovVision2/
#PYTHON=/miniconda/bin/python 
tmux new-window
fi 

#common for sim and hw
new_6_win
run 0 onboard controller.py
#run 1 onboard sensors_gate.py
run 1 onboard "imGate.py -l"
sleep 1
runLoop 2 plugins manual_plugin.py
runLoop 3 plugins depth_hold_plugin.py
runLoop 4 plugins att_hold_plugin.py
#run 5 plugins tracker_plugin.py

#tmux new-window
#new_6_win
#run 0  plugins pos_hold_plugin.py
#run 1  onboard hw_stats.py

#only hw from here
if [ ! -v SIM ]
then 

FILE="/tmp/devusbmap.pkl"

while [ ! -f $FILE ];
do
   echo "detect usb connections"
   python3 ../utils/detect_usb.py
   sleep 1
done


tmux new-window
new_6_win

run 0 sim pybullet_bridge.py
run 1 utils recorder.py
run 2 ground_control rovViewer.py
run 3 ground_control joy_rov.py
#runShell 5 . jtop
#tmux att
fi

