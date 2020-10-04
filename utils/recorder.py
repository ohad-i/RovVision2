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

from select import select


current_command=[0 for _ in range(8)] # 8 thrusters
keep_running=True

topicsList = [ [zmq_topics.topic_thrusters_comand, zmq_topics.topic_thrusters_comand_port],
               [zmq_topics.topic_lights,           zmq_topics.topic_controller_port],
               [zmq_topics.topic_focus,            zmq_topics.topic_controller_port],
               [zmq_topics.topic_depth,            zmq_topics.topic_depth_port],
               [zmq_topics.topic_imu,              zmq_topics.topic_imu_port],
               [zmq_topics.topic_stereo_camera,    zmq_topics.topic_camera_port],
               [zmq_topics.topic_stereo_camera_ts, zmq_topics.topic_camera_port]
        ]

subs_socks=[]
for topic in topicsList:
    subs_socks.append( utils.subscribe( [ topic[0] ], topic[1] ) )
   

rov_type = int(os.environ.get('ROV_TYPE','1'))

class MPS:
    def __init__(self, topic):
        self.tic = time.time()
        self.cnt = 0.0
        self.topic = topic
        
    def calcMPS(self):
        self.cnt += 1.0
        if time.time() - self.tic >= 3:
            mps = self.cnt/(time.time() - self.tic)
            print("%s messages MPS: %0.2f"%(self.topic, mps))
            self.cnt = 0.0
            self.tic = time.time()
            
recordsPath = "../records/"
def initRec():
    if not os.path.exists(recordsPath):
        os.system('mkdir %s'%recordsPath)
    recName = time.strftime("%Y%m%d_%H%M%S", time.localtime()) + '.pkl'
    ret = os.path.join(recordsPath, recName)
    print(ret)
    return ret


def recorder():
    recPath = initRec()
    mpsDict = {}
    for topic in topicsList:
        mpsDict[topic[0]] = MPS(topic[0])
        
    while True:
        socks = zmq.select(subs_socks, [], [], 0.005)[0]
        for sock in socks:
            ret=sock.recv_multipart()
            #topic,data=ret[0],pickle.loads(ret[1])
            topic = ret[0]
            mpsDict[topic].calcMPS()
            
            with open(recPath, 'ab') as fid:
                for data in ret:
                    pickle.dump(data, fid)

if __name__=='__main__':
    if rov_type == 4:
        recorder()
