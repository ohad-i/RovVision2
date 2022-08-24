#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  1 12:38:20 2022

@author: ohadi
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
#resposible for recording/preprossesing/distributing sensor data
import numpy as np
import zmq
import sys
import asyncio
import time
import pickle
import cv2


sys.path.append('..')
sys.path.append('../utils')
import zmq_wrapper
import zmq_topics
import config
import cv2
import socket

import argparse



topicsDict = { zmq_topics.topic_thrusters_comand:   {'port': zmq_topics.topic_thrusters_comand_port, 'rate':-1},
               zmq_topics.topic_lights:             {'port': zmq_topics.topic_controller_port, 'rate':-1},
               zmq_topics.topic_focus:              {'port': zmq_topics.topic_controller_port, 'rate':-1},
               zmq_topics.topic_depth:              {'port': zmq_topics.topic_depth_port, 'rate':-1},
               zmq_topics.topic_volt:               {'port': zmq_topics.topic_volt_port, 'rate':-1},
               zmq_topics.topic_imu:                {'port': zmq_topics.topic_imu_port, 'rate':-1},
               zmq_topics.topic_stereo_camera:      {'port': zmq_topics.topic_camera_port, 'rate':-1},
               zmq_topics.topic_system_state:       {'port': zmq_topics.topic_controller_port, 'rate':-1},
               zmq_topics.topic_att_hold_roll_pid:  {'port': zmq_topics.topic_att_hold_port, 'rate':-1},
               zmq_topics.topic_att_hold_pitch_pid: {'port': zmq_topics.topic_att_hold_port, 'rate':-1},
               zmq_topics.topic_att_hold_yaw_pid:   {'port': zmq_topics.topic_att_hold_port, 'rate':-1},
               zmq_topics.topic_depth_hold_pid:     {'port': zmq_topics.topic_depth_hold_port, 'rate':-1},
               zmq_topics.topic_motors_output:      {'port': zmq_topics.topic_motors_output_port, 'rate':-1},
               }

subs_socks=[]
mpsDict = {}

for topic in topicsDict.keys:
    mpsDict[topic] = mps.MPS(topic)
    subs_socks.append( utils.subscribe( [ topic , topicsDict[topic]['port']) )

keep_running=True

udpTelemIpPort = (config.groundIp, int(config.udpTelemPort))


async def recv_and_process():
    global current_command, inImgCnt, sentImgCnt, jpgQuality
    tic = time.time()
    udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    
    while keep_running:
        socks = zmq.select(subs_socks,[],[],0.005)[0]
        for sock in socks:
            ret = sock.recv_multipart()
            import ipdb; ipdb.set_trace()
            

        await asyncio.sleep(0.001)
 
async def main():
    await asyncio.gather(
            recv_and_process(),
            )

if __name__=='__main__':
    #asyncio.run(main())
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())




