#!/bin/bash

CMD="cd proj/RovVision2/scripts && ./run_onboard.sh"
./sync_onboard.sh && sleep 1 && ssh -t $REMOTE_SUB $CMD
