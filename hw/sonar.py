import time,sys
import os,zmq
sys.path.append('..')
sys.path.append('../utils')
import zmq_wrapper as utils
print('done import 2')
import zmq_topics
import asyncio,pickle

from brping import Ping1D
import detect_usb
dev=detect_usb.devmap['SONAR_USB']

myPing = Ping1D()
myPing.connect_serial(dev, 115200)

if myPing.initialize() is False:
    print("Failed to initialize Ping!")
    exit(1)

pub_imu = utils.publisher(zmq_topics.topic_sonar_port)
cnt=0

mpsCnt = 0.0
mpsTic = time.time()

while 1:
    time.sleep(0.0001)
    #data = myPing.get_distance()
    data = myPing.get_distance_simple()
    ts = time.time()
    if cnt%30==0:
        print(ts, 'sonar, distance',data['distance']/1000)
    tosend = pickle.dumps({'ts':ts, 'distance_mm':data['distance'], 'confidence':data['confidence']} )
    pub_imu.send_multipart([zmq_topics.topic_sonar, tosend])
    cnt+=1
    mpsCnt += 1
    if time.time()-mpsTic>3:
        mps = mpsCnt/(time.time()-mpsTic)
        print('---> sonar rate: %.2fHz'%mps)
        mpsCnt = 0.0
        mpsTic = time.time()
#
