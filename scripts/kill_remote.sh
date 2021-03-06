#!/bin/bash

CMD="cd proj/RovVision2/scripts && ./run_onboard.sh kill"
ssh -t $REMOTE_SUB $CMD
