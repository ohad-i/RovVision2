# -*- coding: utf-8 -*-
"""
Created on Wed Feb 21 11:49:08 2018

@author: taboon
"""
import os
import numpy as np
import sys
import time
import cv2
import zmq
import pickle

sys.path.append('..')
sys.path.append('../utils')
sys.path.append('../onboard')
import zmq_wrapper 
import zmq_topics
import config
import mixer
from joy_mix import Joy_map  

import argparse


parser = argparse.ArgumentParser(description='of module...', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-e', '--runRec', action='store_true', help='run of record')
parser.add_argument('-t', '--runSim', action='store_true', help='run of sim (with debug)')
parser.add_argument('-r', '--recPath', default=None, help=' path to record, avi file')
parser.add_argument('-s', '--skipFrame', type=int, default=-1, help='start of parsed frame, by frame counter not file index')

args = parser.parse_args()


missionState = {'cupWP':0,
                'wps'  :[[0,  10, -1],
                         [10, 10, -1],
                         [10, 0,  -1],
                         [0,  0,  -1]],        #[X, Y, ALT] [ [m], [m], [m] ]
                'maxDepth':         10,           # [m]
                'missionAlt':       2,            # [m]
                'missionHeading':   90,           # yaw [Deg]
                'missionPitch':     -30,          # pitch [Deg]
                'localPos':         [None, None], #[ [m], [m] ]
                'stage':     'idle'        # 'missionInit', 'onNav'
                }

missionCmd = {
                'dDepth': None,         # [m]
                'dPitch': None,         # [deg]
                'dYaw':   None,         # [deg]
                'navVel': [None, None]  # [xDir [-1:1], yDir [-1:1]]
              }

missionPitchOk   = False
missionHeadingOk = False
missionAltOk     = False
curWP            = 0
lastMsgSent      = time.time()
minMsgInerval    = 0.1 # [s]

def missionInit(mState):
    global missionState, missionPitchOk, missionHeadingOk, missionAltOk, curWP

    missionState['curWP']         = 0
    missionState['stage']  =  "initMission"

    missionPitchOk   = False
    missionHeadingOk = False
    missionAltOk     = False
    curWp            = 0


def sendMissionCmd(pub, dDepth, dPitch, dYaw, navVel):
    global lastMsgSent
    if time.time() - lastMsgSent >= minMsgInerval:
        ts = time.time()
        missionCmd = {
                    'ts':     ts,
                    'dDepth': dDepth, # [m]
                    'dPitch': dPitch, # [deg]
                    'dYaw':   dYaw,   # [deg]
                    'navVel': navVel  # [xDir [-1:1], yDir [-1:1]]
                }
        pub.send_multipart([zmq_topics.topic_mission_cmd, pickle.dumps(missionCmd)])
        lastMsgSent = time.time()





def missionHandler(missionPub, depth, alt, pitch, yaw):
    global missionState, missionPitchOk, missionHeadingOk, missionAltOk, curWP
    
    gAlt = np.sin(np.deg2rad(pitch))*cAlt # alt above ground
    dVel = [0, 0]

    if missionState['stage'] == 'initMission':
        if abs(pitch - missionState['missionPitch']) < 0.1: #[deg]
            missionPitchOk = True
        if abs(yaw - missionState['missionHeading']) < 1: #[deg]
            missionHeadingOk = True
        if abs(alt - missionState['missionAlt']) < 0.1: # [m]
            missionAltOk = True
        if missionAltOk and missionPitchOk and missionHeadingOk:
            missionState['stage'] = 'onNav'
    elif missionState['stage'] == 'onNav':
        # calc nav command
        pass


    deltaAlt = gAlt - missionState['missionAlt']
    dDepth   = depth + deltaAlt
    depthCmd = min(dDepth, missionState['maxDepth'])
    dPitch   = missionState['missionPitch']
    dYaw     = missionState['missionHeading']
    sendMissionCmd(missionPub, depthCmd, dPitch, dYaw, dVel )
            

if __name__=='__main__':


    subs_socks=[]
    
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_imu],             zmq_topics.topic_imu_port))
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_system_state],    zmq_topics.topic_controller_port) )
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_depth],           zmq_topics.topic_depth_port) )
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_sonar],           zmq_topics.topic_sonar_port) )
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_of_data],         zmq_topics.topic_of_port) )
    
    missPub = zmq_wrapper.publisher(zmq_topics.topic_mission_port)


    setInitMission = True
    cAlt     = None # sonar reading
    gAlt     = -1   # alt above bathimetry
    curPitch = None   
    curdepth = None
    curYaw   = None
    curDepth = None

    while True:
        time.sleep(0.001)

        socks=zmq.select(subs_socks,[],[],0.005)[0]
        for sock in socks:
            ret=sock.recv_multipart()
            topic, data = ret[0],pickle.loads(ret[1])
            
            if topic == zmq_topics.topic_system_state:
                if 'MISSION' in data['mode']:
                    if setInitMission:
                        #init position
                        setInitMission = False
                            
                elif not setInitMission:
                    setInitMission = True
            elif topic == zmq_topics.topic_sonar:
                if data['confidence'] > 90: #[%]
                    cAlt = data['distance_mm']/1000
                else:
                    cAlt = None

            elif topic == zmq_topics.topic_imu:
                curPitch = data['pitch']
                curYaw   = data['yaw']

            elif topic == zmq_topics.topic_depth:
                curDepth = data['depth']
            

        if cAlt is not None and curPitch is not None and curDepth is not None:
            missionHandler(missPub, curDepth, cAlt, curPitch, curYaw)



        
        





        
        
                    
            
        
