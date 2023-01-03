function init_docker_image {
tmux send-keys "cd $DRONESIMLAB_PATH/dockers/python3_dev && ./run_image.sh" ENTER
}

function new_2_win {
tmux split-window -h
tmux select-pane -t 0
}

function new_4_win {
tmux split-window -h
tmux select-pane -t 0
tmux split-window -v
tmux select-pane -t 2
tmux split-window -v
}


function new_6_win {
tmux split-window -h
tmux select-pane -t 0
tmux split-window -v
tmux select-pane -t 2
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v
tmux select-pane -t 3
tmux split-window -v
}


if [ ! -v SIM ]
then 

function run { #pane number, path, script
tmux select-pane -t $1 
#init_docker_image
#tmux send-keys "bash" ENTER
#tmux send-keys "printf '\033]2;%s\033\\' '$3'" ENTER
tmux send-keys "cd $PROJECT_PATH/$2" ENTER
tmux send-keys "export ROV_TYPE=$ROV_TYPE" ENTER
tmux send-keys "python3 $3" ENTER
}

function runLoop { #pane number, path, script
tmux select-pane -t $1 
#init_docker_image
#tmux send-keys "bash" ENTER
#tmux send-keys "printf '\033]2;%s\033\\' '$3'" ENTER
tmux send-keys "cd $PROJECT_PATH/$2" ENTER
tmux send-keys "export ROV_TYPE=$ROV_TYPE" ENTER
tmux send-keys "for(( ; ; )) ; do python3 $3 ; sleep 1 ; done" ENTER

}

function runShell { #pane number, path, script
tmux select-pane -t $1 
#init_docker_image
#tmux send-keys "bash" ENTER
#tmux send-keys "printf '\033]2;%s\033\\' '$3'" ENTER
tmux send-keys "cd $PROJECT_PATH/$2" ENTER
tmux send-keys "export ROV_TYPE=$ROV_TYPE" ENTER
tmux send-keys "$3" ENTER

}

else
### simulation
function run { #pane number, path, script
tmux select-pane -t $1 
[ ! -z "$RESIZE_VIEWER" ] && tmux send-keys "export RESIZE_VIEWER=$RESIZE_VIEWER" ENTER
tmux send-keys "printf '\033]2;%s\033\\' '$3'" ENTER
#tmux send-keys "conda activate 3.6" ENTER
tmux send-keys "cd $PROJECT_PATH/$2" ENTER
tmux send-keys "python3 $3" ENTER
}




fi
#tmux send-keys "python drone_main.py" ENTER


