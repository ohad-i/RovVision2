import os

import sys
import glob
import numpy as np
import argparse
import time
import sys
sys.path.pop(1)
import cv2

'''
sys.path.append('../')

import zmq
import zmq_topics
import zmq_wrapper as utils

import recorder 

'''
import pickle

usageDescription = 'just run it with a valid record path'

parser = argparse.ArgumentParser(description='synced record parser, %s'%usageDescription, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-r', '--recPath', default=None, help=' path to record ')

args = parser.parse_args()


recPath = args.recPath


print(usageDescription)

if recPath == None:
    sys.exit(1)



frameId = 0


if __name__=='__main__':
    focus = 0
    frameFocus = 0 
    frameTs = -1
    
    try:
        fpsTic = time.time()
        fpsCnt = 0.0
        
        if recPath is not None:
            telemPath = os.path.join(recPath, 'telem.pkl')
            imgCnt = 0
            telemRecEndFlag = False
            
            telFid  = None
            if os.path.exists(telemPath):
                telFid = open(telemPath, 'rb')
            
            curData = pickle.load(telFid)
            nextData = pickle.load(telFid)
            
            while True:
                
                time.sleep(0.0001)
                try:
                    data = curData #pickle.load(telFid)
                except:
                    if not telemRecEndFlag:
                        print('record Ended...')
                        telemRecEndFlag = True
                        break
                    

                curTopic = data[1][0]
                
                if curTopic == b'topic_stereo_camera': 
                    fpsCnt+=1
                    if time.time() - fpsTic >= 5:
                        fps = fpsCnt/(time.time() - fpsTic)
                        print('player video fps %0.2f'%fps)
                        fpsCnt = 0.0
                        fpsTic = time.time()
                        
                    metaData = pickle.loads(data[1][1])
                    frameFocus = metaData[0]
                    frameTs = metaData[2]
                
                elif curTopic == b'system_state':
                    sysState = pickle.loads(data[1][1])
                    curFocus = sysState['focus']
                    if curFocus != focus:
                        focus = curFocus
                        print('focus value: %d (frame: %d, record ts: %f frame ts: %f)'%(focus, frameFocus, data[0], frameTs) )

                    
                        
                else:
                    telData = pickle.loads(data[1][1])
                    
            
                curData = nextData
                nextData = pickle.load(telFid)
                    
                time.sleep(0.0001)

                      
    except:
        import traceback
        traceback.print_exc()
    finally:
        print("done...")            
        
