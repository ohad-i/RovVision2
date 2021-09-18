#!/bin/bash

MOUNT_PNT=~/gDrive/

if [ $# -eq 0 ]
  then
    echo "usage: "
    echo "To mount known google drive: " 
    echo "                         ./mountgDrive.sh label"
    echo "mount point is: $MOUNT_PNT"
    echo ""
    echo ""
    echo "To unount any drive: "
    echo "                         ./mountgDrive.sh Umnt"
    echo ""
    echo "need to set a label, currnt available lables are:"
    ls ~/.gdfuse | sort -n
    exit 1
fi

if [ "$1" = "Umnt" ]; then
    echo ""
    echo "unmount google drive..."
    echo ""
    fusermount -u $MOUNT_PNT 
    exit 1
fi
 
if [ ! -d "$MOUNT_PNT" ]; then
    echo "mount point doesnt exist, creats it..."
    mkdir -p $MOUNT_PNT
fi 
echo ""
echo "mounting drive to $MOUNT_PNT... To unount any drive: "
echo "                                   ./mountgDrive.sh Umnt"
 

google-drive-ocamlfuse -label $1 $MOUNT_PNT
