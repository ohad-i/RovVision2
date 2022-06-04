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
import os

sys.path.append('..')
sys.path.append('../utils')
import zmq_wrapper as utils

import zmq_topics
import config
import cv2
import mps
import socket
from select import select

import argparse

parser = argparse.ArgumentParser(description='UDP gate: zmq pub-sub to/from UDP', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-g', '--ground', action='store_true', help='Is ground control')
args = parser.parse_args()

isGround = args.ground
print('is Ground:', isGround)
iniTic = time.time()
if isGround:
    udpSendPort = config.toROVudpPort
    udpRecvPort = config.fromROVudpPort
    # topic to send over udp
    topicsDict = { 
                    zmq_topics.topic_gui_controller:         { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic }, #rate -> (ms) min ms between msgs
                    zmq_topics.topic_gui_diveModes:          { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_gui_focus_controller:   { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_gui_depthAtt:           { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_gui_autoFocus:          { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic }, 
                    zmq_topics.topic_gui_start_stop_track:   { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_gui_toggle_auto_exp:    { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_gui_inc_exp:            { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_gui_dec_exp:            { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_gui_exposureVal:        { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_gui_toggle_auto_gain:   { 'port': zmq_topics.topic_gui_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_button:                 { 'port': zmq_topics.topic_joy_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_axes:                   { 'port': zmq_topics.topic_joy_port,                    'rate':0.0001, 'lmt':iniTic },
                    zmq_topics.topic_hat:                    { 'port': zmq_topics.topic_joy_port,                    'rate':0.0001, 'lmt':iniTic }, 
                    zmq_topics.topic_check_thrusters_comand: { 'port': zmq_topics.topic_check_thrusters_comand_port, 'rate':0.0001, 'lmt':iniTic },
                   }
    udpTelemIpPort = (os.environ["REMOTE_SUB"].split('@')[1], int(udpSendPort))
    
else:
    
    # topic to send over udp
    udpSendPort = config.toGroundUdpPort
    udpRecvPort = config.fromGroundUdpPort
    
    topicsDict = { zmq_topics.topic_thrusters_comand:   { 'port': zmq_topics.topic_thrusters_comand_port, 'rate':0.05, 'lmt': iniTic}, #rate -> (ms) min ms between msgs
                   zmq_topics.topic_lights:             { 'port': zmq_topics.topic_controller_port,       'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_focus:              { 'port': zmq_topics.topic_controller_port,       'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_depth:              { 'port': zmq_topics.topic_depth_port,            'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_volt:               { 'port': zmq_topics.topic_volt_port,             'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_imu:                { 'port': zmq_topics.topic_imu_port,              'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_system_state:       { 'port': zmq_topics.topic_controller_port,       'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_att_hold_roll_pid:  { 'port': zmq_topics.topic_att_hold_port,         'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_att_hold_pitch_pid: { 'port': zmq_topics.topic_att_hold_port,         'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_att_hold_yaw_pid:   { 'port': zmq_topics.topic_att_hold_port,         'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_depth_hold_pid:     { 'port': zmq_topics.topic_depth_hold_port,       'rate':0.05, 'lmt': iniTic},
                   zmq_topics.topic_motors_output:      { 'port': zmq_topics.topic_motors_output_port,    'rate':0.05, 'lmt': iniTic},
                   }
    udpTelemIpPort = (config.groundIp, int(udpSendPort))





subs_socks=[]
mpsDict = {}

for topic in topicsDict.keys():
    #import ipdb; ipdb.set_trace()
    mpsDict[topic] = mps.MPS(topic)
    subs_socks.append( utils.subscribe( [topic] , topicsDict[topic]['port'] ) )

keep_running=True

udpSendSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
udpRcvSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 

pubsDict = {}

async def recvZmqSendUdp():
    global pubsDict
    sumData = 0
    tic = time.time()
    u=interval = 5 #secs
    while keep_running:
        socks = zmq.select(subs_socks,[],[],0.005)[0]
        for sock in socks:
            ret = sock.recv_multipart()
            topic = ret[0]
            if topic in pubsDict.keys():
                continue
            
            if topic not in mpsDict.keys():
                mpsDict[topic] = mps.MPS(topic)
                
            mpsDict[topic].calcMPS()
            
            if time.time() - topicsDict[topic]['lmt'] > topicsDict[topic]['rate']:
                udpMsg = pickle.dumps( {'exPort':topicsDict[topic]['port'], 'payload':ret} )
                if len(udpMsg) <= 64*1024:
                    sumData += len(udpMsg)
                    if time.time() - tic >= interval:
                        kbps = (sumData*8/interval)/1024
                        print('udpGate rate is %0.2fkbps'%kbps)
                        tic = time.time()
                        sumData = 0
                    udpSendSock.sendto(udpMsg, udpTelemIpPort)
                    topicsDict[topic]['lmt'] = time.time()
                else:
                    print('message too long... (%s)'%topic)

        await asyncio.sleep(0.001)
        
async def recvUdpSendZmq():
    global pubsDict
    udpRcvSock.bind(('', udpRecvPort))
    pubsDict = {}
    revTopicPubDict = {}
    portsList = []
    while keep_running:
        socks = select([udpRcvSock],[],[],0.005)[0]
        if len(socks) > 0:
            ret = udpRcvSock.recvfrom(1024*64)
            udpMsg = pickle.loads(ret[0])
            topic = udpMsg['payload'][0]
            zmqPort = udpMsg['exPort']
            if topic not in pubsDict.keys():
                if zmqPort not in portsList:
                    print('creats publisher on port: %d %s'%(zmqPort, topic) )
                    pubsDict[topic] = utils.publisher(zmqPort)
                    revTopicPubDict[zmqPort] = pubsDict[topic]
                    portsList.append(zmqPort)
                else:
                    pubsDict[topic] = revTopicPubDict[zmqPort]
        
            try:
                pubsDict[topic].send_multipart( udpMsg['payload'] )
            except:
                import traceback; traceback.print_exc()
                #import ipdb; ipdb.set_trace()
                
            
        await asyncio.sleep(0.001)
 
async def main():
    await asyncio.gather(
            recvZmqSendUdp(), recvUdpSendZmq()
            )

if __name__=='__main__':
    #asyncio.run(main())
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())




