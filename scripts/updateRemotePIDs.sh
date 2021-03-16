#!/bin/bash

CMD="pkill -f plugin.py"
./sync_onboard.sh && sleep 2 && ssh -t $REMOTE_SUB $CMD

