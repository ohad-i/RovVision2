import numpy as np
import zmq
import sys
import time
import pickle
import struct
import os

sys.path.append('..')
sys.path.append('../utils')
import zmq_wrapper as utils
import zmq_topics
import config
import shutil
import mps
import cv2
from select import select


current_command=[0 for _ in range(8)] # 8 thrusters
keep_running=True

topicsList = [ [zmq_topics.topic_thrusters_comand, zmq_topics.topic_thrusters_comand_port],
               [zmq_topics.topic_lights,           zmq_topics.topic_controller_port],
               [zmq_topics.topic_focus,            zmq_topics.topic_controller_port],
               [zmq_topics.topic_depth,            zmq_topics.topic_depth_port],
               [zmq_topics.topic_volt,             zmq_topics.topic_volt_port],
               [zmq_topics.topic_imu,              zmq_topics.topic_imu_port],
               [zmq_topics.topic_stereo_camera,    zmq_topics.topic_camera_port],
               [zmq_topics.topic_system_state,     zmq_topics.topic_controller_port],
        ]

subs_socks=[]
mpsDict = {}

for topic in topicsList:
    mpsDict[topic[0]] = mps.MPS(topic[0])
    subs_socks.append( utils.subscribe( [ topic[0] ], topic[1] ) )
   

rov_type = int(os.environ.get('ROV_TYPE','1'))

doRec = False
telemFile = None
videoFile = None
videoQFile = None

recordsBasePath = "../records/"
def initRec():
    global telemFile, videoFile, videoQFile
    recName = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    recPath = os.path.join(recordsBasePath, recName)
    if not os.path.exists(recPath):
        os.system('mkdir -p %s'%recPath)
    
    telemFile = os.path.join(recPath, 'telem.pkl')
    videoFile = os.path.join(recPath, 'video.bin')
    videoQFile = os.path.join(recPath, 'videoQ.bin')
    print(recPath)
    return recPath

debugVideo = False

if debugVideo:
    cv2.namedWindow('low', 0)
    cv2.namedWindow('high', 0)

def recorder():
    global telemFile, videoFile, videoQFile, doRec
    
    
    cnt = 0
    imgCnt = 0
    imgDilution = 4 #save full frame each
    hasHighQuality = False
    while True:
        socks = zmq.select(subs_socks, [], [], 0.001)[0]
        ts = time.time()


        cnt += 1
        if cnt%200 == 0:
            total, used, free = shutil.disk_usage("/")
            if free//2**30 < 5:
                doRec = False
                print("***Low disk space - record Stopped! ******"*5)

        for sock in socks:
            ret=sock.recv_multipart()
            #topic,data=ret[0],pickle.loads(ret[1])
            topic = ret[0]
            if topic in mpsDict.keys():
                mpsDict[topic].calcMPS()
                if topic == zmq_topics.topic_system_state:
                    newDoRec = pickle.loads(ret[1])[1]['record']
                    if (newDoRec) and (not doRec):
                        recPath = initRec()
                        print('record started, %s'%recPath)
                        doRec = True
                    elif (not newDoRec) and doRec:
                        print('Stop recording...')
                        doRec = False
                    
                if doRec:
                    if topic == zmq_topics.topic_stereo_camera:
                        imgCnt += 1
                        if imgCnt%imgDilution == 0:
                            with open(videoFile, 'ab') as fid:
                                # write image raw data
                                fid.write(ret[-1])
                                hasHighQuality = True
                        
                        imShape = pickle.loads(ret[1])[1]
                        imRaw = np.frombuffer(ret[-1], dtype='uint8').reshape(imShape)
                        
                        low = cv2.resize(imRaw, (imShape[1]//2, imShape[0]//2))
                        #print('--->', low.shape, imRaw.shape)
                        if debugVideo:
                            cv2.imshow('high', imRaw)
                            cv2.imshow('low', low)
                            cv2.waitKey(1)
                        with open(videoQFile, 'ab') as fid:
                            # write image raw data
                            fid.write(low.tobytes())
                        with open(telemFile, 'ab') as fid:
                            # write image metadata
                            imMetaData = ret[:-1]
                            imMetaData.append(hasHighQuality)
                            pickle.dump([ts, imMetaData], fid)
                            hasHighQuality = False
                    else:
                        with open(telemFile, 'ab') as fid:
                            pickle.dump([ts, ret], fid)

if __name__=='__main__':
    if rov_type == 4:
        recorder()
