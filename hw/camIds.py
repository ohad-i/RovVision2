import os
import sys
import zmq
sys.path.append('idsCam/')
from camera import Camera
from pyueye import ueye
import cv2
import time

sys.path.append('../')
sys.path.append('../utils')

import zmq_topics
import zmq_wrapper as utils
import pickle



socket_pub = utils.publisher(zmq_topics.topic_camera_port)
subSocks = [utils.subscribe([zmq_topics.topic_cam_toggle_auto_exp, 
                             zmq_topics.topic_cam_toggle_auto_gain,
                             zmq_topics.topic_cam_inc_exp,
                             zmq_topics.topic_cam_dec_exp,
                             zmq_topics.topic_cam_exp_val], zmq_topics.topic_cam_ctrl_port)]

cam = Camera(device_id=0, buffer_count=3)
#======================================================================
# Camera settings
#======================================================================
# TODO: Add more config properties (fps, gain, ...)
cam.init()
#cam.set_colormode(ueye.IS_CM_MONO8)
cam.set_colormode(ueye.IS_CM_SENSOR_RAW8)
#
ret = cam.set_aoi(0, 0, 2048, 2048)
cam.alloc()
#cam.set_aoi(0, 0, 800, 800)
print(f"INITIAL VALUES")
print(f'fps: {cam.get_fps()}')
print(f'Available fps range: {cam.get_fps_range()}')
print(f'Pixelclock: {cam.get_pixelclock()}')
#cam.set_pixelclock(30)

cam.set_fps(10)
print("")
print(f"MODIFIED VALUES")
print(f'fps: {cam.get_fps()}')
print(f'Available fps range: {cam.get_fps_range()}')
print(f'Pixelclock: {cam.get_pixelclock()}')

tic = time.time()
cnt = 0.0 
frameCnt = 0

gainCtl = 0
expCtl = 1
desExpVal = 50

camStateFile = '../hw/camSate.pkl'

camState = {}
desExpVal = -1
if os.path.exists(camStateFile):
    with open(camStateFile, 'rb') as fid:
        camState = pickle.load(fid)
        if 'aGain' in camState.keys():
            gainCtl = camState['aGain']
        if 'aExp' in camState.keys():
            expCtl = camState['aExp']
        if 'expVal' in camState.keys():
            desExpVal = camState['expVal']


if ('aExp' not in camState.keys() or camState['aExp'] == 0) and desExpVal > 0:
    newExp = cam.set_exposure(desExpVal)
    print('init exp value: ', newExp)
            
            
camState['aGain'] = gainCtl
camState['aExp'] = expCtl
camState['expVal'] = desExpVal


'''
with open(camStateFile, 'wb') as fid:
    pickle.dump(camState, fid)
'''

cam.set_exposure_auto(expCtl)
cam.set_gain_auto(gainCtl)

curExp = cam.get_exposure()
expJump = 0.3

while True:
    im0, ts = cam.capture_image() #, 110)
    
    if im0 is not None:
        cnt +=1
        frameCnt += 1
    
        imRaw = cv2.cvtColor(im0.astype('uint8'), cv2.COLOR_BAYER_BG2RGB)
        
        imShape = imRaw.shape
        
        QRes = cv2.resize(imRaw, (imShape[1]//2, imShape[0]//2))
        hasHighRes = True
        if frameCnt%4 == 0:
            socket_pub.send_multipart([zmq_topics.topic_stereo_camera,
            pickle.dumps((frameCnt, imShape, ts, camState, hasHighRes)), QRes.tobytes(),
                                                    imRaw.tobytes()])
        else:
            hasHighRes = False
            socket_pub.send_multipart([zmq_topics.topic_stereo_camera,
                                       pickle.dumps((frameCnt, imShape, ts, camState, hasHighRes)),
                                       QRes.tobytes(), b''])

        socket_pub.send_multipart( [zmq_topics.topic_stereo_camera_ts,
                                                pickle.dumps( (frameCnt, ts) )] )
        
    socks=zmq.select(subSocks, [], [], 0.002)[0]
    for sock in socks:
        ret=sock.recv_multipart()
        topic,data=ret
        
        if topic==zmq_topics.topic_cam_toggle_auto_exp:
            expCtl = pickle.loads(data)
            print('set auto exp. to: %d'%expCtl)
            cam.set_exposure_auto(expCtl)
        
        if topic==zmq_topics.topic_cam_toggle_auto_gain:
            gainCtl = pickle.loads(data)
            print('set auto gain to: %d'%gainCtl)
            cam.set_gain_auto(gainCtl)
        
        if topic==zmq_topics.topic_cam_inc_exp:
            curExp = cam.get_exposure()
            newExp = curExp + expJump
            print('set exp (inc) to: %.2f'%newExp)
            newExp = cam.set_exposure(newExp)
            print('--->', newExp)
            camState['expVal'] = newExp
            
        if topic==zmq_topics.topic_cam_dec_exp:
            curExp = cam.get_exposure()
            newExp = max(1, curExp - expJump )
            print('set exp (dec) to: %.2f'%newExp)
            newExp = cam.set_exposure(newExp)
            print('--->', newExp)
            camState['expVal'] = newExp
            
        if topic == zmq_topics.topic_cam_exp_val:
            curExp = cam.get_exposure()
            newExp = pickle.loads(data)
            print('set exp to: %.2f'%newExp)
            newExp = cam.set_exposure(newExp)
            print('--->', newExp)
            camState['expVal'] = newExp
            
            

        camState['aGain'] = gainCtl
        camState['aExp'] = expCtl
        
        with open(camStateFile, 'wb') as fid:
            pickle.dump(camState, fid)
        
        
    curExp = cam.get_exposure()
    camState['expVal'] = curExp
    
    if(time.time() - tic) > 3:
        fps = cnt/(time.time()-tic)
        print('current fps: %.2f currnet exp: %0.2f'%(fps, curExp) )
        cnt = 0.0
        tic = time.time()

