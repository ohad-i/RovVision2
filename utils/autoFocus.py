#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  6 11:16:25 2021

@author: ohadi
"""
import numpy as np
import zmq
import sys
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

subs_socks=[]
subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_stereo_camera], zmq_topics.topic_camera_port))
subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_system_state], zmq_topics.topic_controller_port))

autoFocusPublisher = zmq_wrapper.publisher(zmq_topics.topic_autoFocus_port)



if __name__=='__main__':
    
    doResize = True
    sx,sy=config.cam_res_rgbx,config.cam_res_rgby
    
    imgCnt  = 0.0
    tic = time.time()
    keep_running = True
    curFocusVal = -1
    
    margin = 100
    ##af = None
    
    curFocus = 850
    data = pickle.dumps(curFocus, protocol=3)
    autoFocusPublisher.send_multipart( [zmq_topics.topic_autoFocus, data])
    
    #jumps = [50, 10, 5]
    jumps = [200, 50, 5]

    curIter = 0
    jump = jumps[curIter]
    maxFocusVal = 2250
    maxFocusSate = {'maxFm':-1, 'maxFocusValue':-1}
    done1st = False
    
    focusValue = -1
    
    cnt = 1
    while keep_running:
        time.sleep(0.01)
        socks=zmq.select(subs_socks,[],[],0.005)[0]
        for sock in socks:
            ret=sock.recv_multipart()
            topic = ret[0]
            if topic == zmq_topics.topic_system_state:
                focusValue = pickle.loads(ret[1])['focus']
                
            if topic == zmq_topics.topic_stereo_camera:
                imgCnt += 1
                cnt += 1
                
                if cnt%4 == 0:
                    if focusValue == curFocus:
                        frame_cnt,shape,ts=pickle.loads(ret[1])
                        
                        imgl=np.frombuffer(ret[2],'uint8').reshape(shape).copy()
                        if doResize:
                            imgl = cv2.resize(imgl, (sx,sy))
                        #cv2.imshow('aa', imgl)
                        #cv2.waitKey(10)
                        
                        gray = cv2.cvtColor(imgl, cv2.COLOR_BGR2GRAY)
                        gray = gray[margin:-margin, margin:-margin]
                        fm = cv2.Laplacian(gray, cv2.CV_64F).var()
            
                        if fm > maxFocusSate['maxFm']:
                            maxFocusSate['maxFm'] = fm
                            maxFocusSate['maxFocusValue'] = curFocus
                            print('--- best vals so far --->', maxFocusSate )
                        
                        
                        curFocus = curFocus+jump
                        if curFocus > maxFocusVal:
                            print('next iteration --->', maxFocusSate, jump )
                            curIter += 1
                            if curIter < len(jumps):
                                curFocus = maxFocusSate['maxFocusValue']-jump
                                maxFocusVal = maxFocusSate['maxFocusValue']+jump
                                jump = jumps[curIter]
                            else:
                                keep_running = False
                            
                        print(curFocus, jump, fm)
                        data = pickle.dumps(curFocus, protocol=3)
                        autoFocusPublisher.send_multipart( [zmq_topics.topic_autoFocus, data])
                    else:
                        data = pickle.dumps(curFocus, protocol=3)
                        autoFocusPublisher.send_multipart( [zmq_topics.topic_autoFocus, data])
                        
                    
                
        if time.time() - tic >= 3:
            inImgFPS = imgCnt/(time.time() - tic)
            print(tic, 'auto focus %.2f FPS'%(inImgFPS))
            imgCnt = 0.0
            tic = time.time()
        
    print('--- done focus, autofocus sets to: ', maxFocusSate)
    data = pickle.dumps(maxFocusSate['maxFocusValue'], protocol=3)
    autoFocusPublisher.send_multipart( [zmq_topics.topic_autoFocus, data])
    