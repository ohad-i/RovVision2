#!/bin/bash
source run_common.sh

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
new_4_win
#run 0 onboard controller.py
#run 0 onboard sensors_gate.py
sleep 1
run 1 plugins manual_plugin.py
run 2 plugins depth_hold_plugin.py
run 3 plugins att_hold_plugin.py
#run 5 plugins tracker_plugin.py

#tmux new-window
#new_6_win
#run 0  plugins pos_hold_plugin.py
#run 1  onboard hw_stats.py

#only hw from here
if [ ! -v SIM ]
then 
tmux new-window
new_6_win
run 0 utils detect_usb.py
sleep 1
run 0 hw hw_gate.py
run 1 hw idsGst_proxy.py
run 2 hw vnav.py
run 3 utils recorder.py
#run 4 hw sonar.py
tmux att
fi
