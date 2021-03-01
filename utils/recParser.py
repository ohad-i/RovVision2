import os
import numpy as np
import pickle
import sys
import cv2
import time
sys.path.append('../')

import zmq_topics
import zmq_wrapper as utils


import argparse

#https://github.com/espressif/esptool/wiki/ESP32-Boot-Mode-Selection
if 1 and __name__=="__main__":
    parser = argparse.ArgumentParser(description='''
                            recorder parser
                            ''')
    parser.add_argument("-i","--input", default='', help="recdord file path")
    args = parser.parse_args()
    
    recFile = args.input
    winName = 'input'
    cv2.namedWindow(winName, 0)
    delay = 0

    if os.path.exists(recFile):
        jpgPath = os.path.join('../records', os.path.split(recFile)[-1][:-4])
        if not os.path.exists(jpgPath):
            os.system('mkdir -p %s'%jpgPath)
            
            
        img = None
        
        fpsFrameCnt = 0.0
        fpsDepthCnt = 0.0
        fpsImuCnt = 0.0
        fpsthrustersCnt = 0.0
        fpsTic = time.time()
        with open(recFile, 'rb') as fid:
            while True:
                try:
                    sample = pickle.load(fid)
                    if sample == zmq_topics.topic_stereo_camera:
                        metaData = pickle.loads(pickle.load(fid))
                        #print('got frame ', metaData[0])
                        img = np.frombuffer(pickle.load(fid), dtype='uint8').reshape(1216,1936,3)
                        jpgName = os.path.join(jpgPath, '%d.jpg'%metaData[0])
                        cv2.imwrite(jpgName, img)
                        fpsFrameCnt += 1
    
                    elif sample == zmq_topics.topic_stereo_camera_ts:
                        frameTs = pickle.loads(pickle.load(fid))
                        
                        #print('got frame ts ', frameTs[0])
                    elif sample == zmq_topics.topic_depth:
                        dapth = pickle.loads(pickle.load(fid))
                        fpsDepthCnt += 1
                        #print('got depth msg ', dapth)
                    elif sample == zmq_topics.topic_imu:
                        imu = pickle.loads(pickle.load(fid))
                        fpsImuCnt += 1
                        #print('got imu msg ', imu)
                    elif sample == zmq_topics.topic_thrusters_comand:
                        thrusters = pickle.loads(pickle.load(fid))
                        fpsthrustersCnt += 1
                        #print('got thrusters msg ', thrusters)
                    else:
                        print(sample)
                        
                    if time.time()-fpsTic >= 3:
                        dt = time.time()-fpsTic
                        frameFps = fpsFrameCnt/dt
                        depthFps = fpsDepthCnt/dt
                        imuFps = fpsImuCnt/dt
                        thrustersFps = fpsthrustersCnt/dt
                        
                        print('frame fps: %0.2f depth fps: %0.2f imu fps: %0.2f thrusters fps: %0.2f '
                                %(frameFps, depthFps, imuFps, thrustersFps ))
                        
                        fpsFrameCnt = 0.0
                        fpsDepthCnt = 0.0
                        fpsImuCnt = 0.0
                        fpsthrustersCnt = 0.0
                        fpsTic = time.time()
                    
                    if img is not None:
                        cv2.imshow(winName, img)
                        key = cv2.waitKey(delay)
                        
                        if key == ord(' '):
                            delay = 0
                        if key == ord('r'):
                            delay = 1
                        if key == ord('q'):
                            break
                except EOFError:
                    print('record ended')
                    break
                

    else:
        print('error %s rec file not exist'%recFile)