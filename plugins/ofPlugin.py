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

class ofTracker:
    def __init__(self, debug=False):
        print('init of tracker...')
        
        self.grids = {  1:range(0,1), 
                        4:range(-1,1), 
                        9:range(-1,2), 
                        16:range(-2,2), 
                        25:range(-2,3), 
                        49:range(-3,4),
                        81:range(-4,5),
                        121:range(-5,6),
                        169:range(-6,7),
                        225:range(-7,8),
                        289:range(-8,9),
                        361:range(-9,10),
                        441:range(-10,11),
                        529:range(-11,12),
                        625:range(-12,13),
                    }
        
        self.gridPts        = -1
        self.prevFrame      = None
        self.keyFrame       = None
        self.initKeyPts     = [] # init pts are around the center of the image, after receiving the first frame the nwe coordinates are calculated
        self.frameOffsets   = []
        self.curPts         = []

        self.horizenLevel = 0 # whole frame
        self.minPtsForEstimation = -1

        self.memSetPnt   = None
        self.genSetPoint = None
        

        self.searchRadius = 10
        
        self.lk_params = {} #dict(winSize = (15,15),
                            #  maxLevel = 4,
                            #  criteria = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 10, 0.03) )

        self.name       = ''

        self.useGftt = True
        self.gfttMask = None

        if self.useGftt:
            # in case of improving track point using goodfeature to track        
            self.feature_params = None

        self.debug   = debug
        self.saveRes = True
        self.writer  = None

        

        
        
        
    def init(self, name = '<ofTracker>', 
                    girdPts = 81, 
                    winSize = 40, 
                    maxLevel = 5, 
                    criteriaCount = 50, 
                    criteriaEPS =  0.01):

        self.name       = name
        self.lk_params  = dict(winSize = (winSize, winSize),
                          maxLevel = maxLevel,
                          criteria = (cv2.TERM_CRITERIA_COUNT | 
                                      cv2.TERM_CRITERIA_EPS, 
                                      criteriaCount, criteriaEPS) )

        if girdPts not in self.grids.keys():
            print('Error: invalid girdPts, should be in', self.grids.keys())
            girdPts = 81
            print('using default girdPts %d'%girdPts)
        
        self.gridPts    = girdPts

        if self.useGftt:
            self.feature_params = dict(maxCorners = self.gridPts,
                                        qualityLevel = 0.1,
                                        minDistance = 50,
                                        blockSize = 20,
                                        )#useHarrisDetector = True)



        '''
        # with predicted track
        self.lk_params = dict(winSize = (winSize, winSize),
                              maxLevel = maxLevel,
                              criteria = (cv2.TERM_CRITERIA_COUNT | 
                              cv2.TERM_CRITERIA_EPS | 
                              cv2.OPTFLOW_USE_INITIAL_FLOW, 
                              criteriaCount, criteriaEPS) )
        '''

    def setJoyOffset(self, ofX, ofY):
        self.genSetPoint = self.memSetPnt + np.array([ofX, ofY])*-100 # 70 -> pixels
        
    def initKeyFrame(self, frame):
        print('init key frame...')
        self.prevFrame   = np.copy(frame)
        self.keyFrame    = np.copy(frame)
        self.lk_params['winSize'] = (40, 40) # init search value
        
        if not self.useGftt:
            self.curPts     = np.copy(self.initKeyPts)
        else:
            p0 = cv2.goodFeaturesToTrack(frame, mask=self.gfttMask, **self.feature_params)
            self.curPts = p0

            self.minPtsForEstimation = len(self.curPts)*0.2
            print('num of corners detected: %d'%len(self.curPts))
        
        self.genSetPoint = np.array([self.curPts[:,:,0].mean(), self.curPts[:,:,1].mean()])
        self.memSetPnt = self.genSetPoint
        
        if self.debug:
            self.plotPts(self.keyFrame, self.curPts, None, self.genSetPoint, cvName="initKey")

            if self.saveRes:
                if self.writer is None:
                    fourcc = cv2.VideoWriter_fourcc(*'RGBA')
                    self.writer = cv2.VideoWriter('ofTrackerRes.avi',
                                    fourcc, 10,
                                    (frame.shape[1], frame.shape[0]),
                                    True)

        return 

    def initUniformGrid(self, frame = None):
        
        # use in case of updating horizenLevel
        # can be optimized...
        for i in self.grids[self.gridPts]: #range(-2,3):
            for j in self.grids[self.gridPts]: #range(-2,3):
                pt = np.array([i,j])*self.searchRadius + np.array(self.frameOffsets)
                self.initKeyPts.append(pt)
                
        self.minPtsForEstimation = len(self.initKeyPts)*0.55
        self.initKeyPts          = np.float32(self.initKeyPts).reshape(-1,1,2)

        if 0:
            genSetPoint = [self.initKeyPts[:,:,0].mean(), self.initKeyPts[:,:,1].mean()]
            
            if 1 and frame is not None:
                showImg = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                for pt in self.initKeyPts[:,0,:]:
                    cv2.circle(showImg, (int(pt[0]), int(pt[1])), 2, (0, 0, 255), -1 )
                
                cv2.circle(showImg, (int(genSetPoint[0]), int(genSetPoint[1])), 10, (255, 255, 255), 1 )

                cv2.imshow('<ofTracker_initPts>', showImg)
                cv2.waitKey(10)
        
    
    def plotPts(self, image, pts, meanPts = None, pPoint = None, cvName='<ofTracker pts>'):
        showImg = np.copy(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR))
        for pt in pts:
            cv2.circle(showImg, (int(pt[0][0]), int(pt[0][1])), 2, (0, 0, 255), -1 )
        '''
        for pt in self.initKeyPts:
            cv2.circle(showImg, (int(pt[0][0]), int(pt[0][1])), 2, (0, 255, 255), -1 )
        '''

        if meanPts is not None:
            cv2.circle(showImg, (int(meanPts[0]), int(meanPts[1])), 10, (255, 0, 0), 2 )
        if pPoint is not None:
            cv2.circle(showImg, (int(pPoint[0]), int(pPoint[1])), 10, (0, 255, 255), 2 )

        if self.writer is not None:
            self.writer.write(showImg)
        cv2.imshow(cvName, showImg)
        cv2.waitKey(10)

                        
    def ofTrack(self, inImg = None):
        ts = time.time()
        if inImg is not None:
            image = np.copy(inImg)
            if self.keyFrame is not None:
                
                p1 = None
                #print '1', self.prevFrame.shape
                #print '2', image.shape
                #print '3', p0.shape
                #print '4', p1.shape
                #cv2.imshow('key', self.keyFrame)
                #cv2.imshow('cur', image)
                predPntA, stA, err = cv2.calcOpticalFlowPyrLK(self.prevFrame, 
                                                             image, 
                                                             self.curPts, 
                                                             p1, 
                                                             **self.lk_params)

                self.prevFrame = np.copy(image)
                #import ipdb; ipdb.set_trace()
                stA[err>30] = 0
                
                self.curPts = predPntA[stA == 1]
                #predPntA = predPntA[stA == 1]
                                
                #self.curPts = predPntA
                self.curPts = np.float32(self.curPts).reshape(-1,1,2)
                newPoint = np.array([self.curPts[:,:,0].mean(), self.curPts[:,:,1].mean()])
                
                #print('motion estimation: ', newPoint-self.genSetPoint)

                keyFrameDistance = np.sqrt((newPoint[0]-self.genSetPoint[0])**2 + (newPoint[1]-self.genSetPoint[1])**2)
                
                newKeyFrame = False
                if len(self.curPts) < self.minPtsForEstimation: # or keyFrameDistance > self.frameOffsets[0]/4:
                    print('low features count %d, init key frame'%len(self.curPts))
                    self.initKeyFrame(image)
                    newKeyFrame = True
                    return None

                else:
                    #print('2 num fo features: ', self.curPts.shape[0])
                    if self.debug:
                        predPntA = np.float32(predPntA).reshape(-1,1,2)
                        self.plotPts(image, predPntA, newPoint, self.genSetPoint)


                    ofRet = {
                             'ts':ts,
                             'isNewKeyFrame': newKeyFrame,
                             'genSetPoint': self.genSetPoint,
                             'curSetPoint': newPoint,
                             'curPts': self.curPts,
                            }

                    return ofRet
     
                                    
               
            else:
                # find frame ofsets and calculate the init pts

                self.horizenLevel = 150 #230 #image.shape[0]//2 
                #the horizen level needs to be calculated using the pitch of the camera

                #self.searchRadius = [image.shape[1]//(self.gridPts**0.5), image.shape[0]//(self.gridPts**0.5)] # non-symetric
                self.searchRadius = [image.shape[0]//(self.gridPts**0.5), (image.shape[0]-self.horizenLevel)//(self.gridPts**0.5)] # symetric to hight dimension
                self.frameOffsets = [image.shape[1]//2, image.shape[0]//2+(self.horizenLevel//2)]
                
                if not self.useGftt:
                    self.initUniformGrid(image)
                else:
                    self.gfttMask = np.zeros(image.shape[:2], dtype = np.uint8)
                    self.gfttMask[int(self.horizenLevel):-200, :] = 255
                    #cv2.imshow('<mask>', self.gfttMask)
                    #cv2.waitKey(10)

                self.initKeyFrame(image)
                
                return None

                    

if __name__=='__main__':

    im      = None
    imTt    = None
    winName = 'Of'

    ofTrck  = ofTracker(args.runRec )
    ofTrck.init(girdPts=169)

    cnt = 0.0
    frameId = 0
    tic = time.time()
    mmAvi = None
    
    jm=Joy_map()

    if args.runSim:
        ptt = 0
    else:
        ptt = 2 # plane to track

    if not args.runRec:
        subs_socks=[]
        subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_stereo_camera],   zmq_topics.topic_camera_port)     )
        subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_imu],             zmq_topics.topic_imu_port))
        subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_system_state, 
                                                 zmq_topics.topic_tracker_cmd],     zmq_topics.topic_controller_port) )
        subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_axes],       zmq_topics.topic_joy_port))

        ofDataPub = zmq_wrapper.publisher(zmq_topics.topic_of_port)

        thrustersSource = zmq_wrapper.push_source(zmq_topics.thrusters_sink_port)
        
        setInitPos = True
        gFrame = None

        startManuver = False
        while True:
            time.sleep(0.0001)
            
            if time.time() - tic >= 5:
                fps = cnt/(time.time()-tic)
                print('cur fps: %0.2f'%(fps))
                cnt = 0.0
                tic = time.time()

            socks=zmq.select(subs_socks,[],[],0.005)[0]
            for sock in socks:
                ret=sock.recv_multipart()
                topic, data = ret[0],pickle.loads(ret[1])
                if topic==zmq_topics.topic_axes:
                    #print('joy ',ret[jm.yaw])
                    jm.update_axis(data)
                    joy = jm.joy_mix()
                    try: 
                        ofTrck.setJoyOffset(joy['lr'], joy['fb'])
                    except:
                        pass

                elif topic==zmq_topics.topic_stereo_camera:

                    frameCnt, shape,ts, curExp, hasHighRes = pickle.loads(ret[1])
                    frame = np.frombuffer(ret[-2],'uint8').reshape( (shape[0]//2, shape[1]//2, 3) ).copy()

                    gFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)[:,:,ptt]
                    ofRes = ofTrck.ofTrack(gFrame)
                    
                    cnt += 1

                    if ofRes is not None:
                        ofDataPub.send_multipart([zmq_topics.topic_of_data, pickle.dumps(ofRes)])

                        ofMinimal = {'genSetPoint': ofRes['genSetPoint'],'curSetPoint': ofRes['curSetPoint']}
                        ofDataPub.send_multipart([zmq_topics.topic_of_minimal_data, pickle.dumps(ofMinimal)])

                        if startManuver:

                            roll = 0
                            pitch = 0
                            yaw = 0
                            upDown = 0

                            err = ofRes['curSetPoint'] - ofRes['genSetPoint']
                            
                            rightLeft = 0 
                            backForward = 0

                            if abs(err[0]) > 10:
                                rightLeft = min(1, max(-1, err[0]/100) ) 
                            
                            if abs(err[1]) > 10:
                                backForward = min(1, max(-1, err[1]/100) ) 

                            print(err, '-<>', rightLeft, backForward )

                            thrusterOfCmd = np.array(mixer.mix(upDown, rightLeft, backForward,roll ,pitch ,yaw ,0 ,0))
                            thrustersSource.send_pyobj(['of', time.time(), thrusterOfCmd])
                        else:
                            thrustersSource.send_pyobj(['of', time.time(), mixer.zero_cmd()])
                        

                elif topic == zmq_topics.topic_system_state:
                    if 'POSITION' in data['mode']:
                        if setInitPos:
                            #init position
                            if gFrame is not None:
                                print("init key...")
                                ofTrck.initKeyFrame(gFrame)
                                setInitPos = False
                                startManuver = True
                    elif not setInitPos:
                        setInitPos = True
                        startManuver = False
                        
                if args.runSim:
                    key = cv2.waitKey(10)
                    if key&0xff == 27 or key&0xff == ord('q'):
                        sys.exit(0)
                    if key&0xff == ord('k'):
                        print('init kay by command...')
                        ofTrck.initKeyFrame(gFrame)

        
        
    else:

        def startTrack(event,x,y,flags,param):
            global trackPnt, trackerInit
            if event == cv2.EVENT_LBUTTONDOWN:
                print('start tracker: ', x, y)
                
            if event == cv2.EVENT_MBUTTONDOWN:
                print('stop tracker')
                
        cv2.namedWindow(winName, 0)
        cv2.setMouseCallback(winName, startTrack)
        
        #fileName = r'jellyFish_realTracker.avi'
        ## pool
        #fileName = r'/home/ohadi/rovRecs/newEspRec/outLowRes.avi'
        #fileName = r'/home/ohadi/proj/RovVision2/records/20230904_095709/outLowRes.avi
        fileName = r'/home/ohadi/proj/RovVision2/records/20230905_103230/outLowRes.avi'
        #fileName = r'outLowRes.avi'
        #fileName = r'oriSamples/vid_l.mp4'
        cap = cv2.VideoCapture(fileName)
        ret, im = cap.read()
        
        wait = 0 #200 # ms, 0->infinite
        
        writer = None

        skipFrame = 100
        for _ in range(skipFrame):
            ret, im = cap.read()
            frameId += 1
        
        imTt = cv2.cvtColor(im, cv2.COLOR_BGR2YUV)
        

        try:
            while ret:
                frameId += 1 
                cnt += 1
                if time.time() - tic >= 5:
                    fps = cnt/(time.time()-tic)
                    print('cur fps: %0.2f, wait=%d ms'%(fps, wait))
                    cnt = 0.0
                    tic = time.time()

                trckRes = ofTrck.ofTrack(imTt[:,:,ptt])
                
                ''' 
                if writer is None:
                    fourcc = cv2.VideoWriter_fourcc(*'RGBA')
                    writer = cv2.VideoWriter('trackRes.avi', fourcc, 10, (im.shape[1], im.shape[0]), True)
                else:
                    writer.write(im)
                '''
            
                cv2.imshow(winName, im)
                key = cv2.waitKey(wait)
                if key&0xff == 27 or key&0xff == ord('q'):
                    break
                if key&0xff == ord('k'):
                    print('init kay by command...')
                    ofTrack.initKeyFrame()
                if key&0xff == ord('+'):
                    wait = max(10, wait-10)
                if key&0xff == ord('-'):
                    wait = wait+10
                if key&0xff == ord(' '):
                    wait = 0
                    cv2.waitKey(wait)
                if key&0xff == ord('a'):
                    print('add frame to edited avi... %d'%frameId)
                    if mmAvi is None:
                        fourcc = cv2.VideoWriter_fourcc(*'RGBA')
                        mmAvi = cv2.VideoWriter('mm.avi', fourcc, 25, (im.shape[1], im.shape[0]), True)
                    mmAvi.write(im)
                    wait = 0
                    cv2.waitKey(wait)

                ret, im = cap.read()
                imTt = cv2.cvtColor(im, cv2.COLOR_BGR2YUV)
                #im = im-np.mean(im)
                '''
                cv2.imshow('0', imTt[:,:,0])
                cv2.imshow('1', imTt[:,:,1])
                cv2.imshow('2', imTt[:,:,2])
                '''
                #import ipdb; ipdb.set_trace()
                #im = (im+np.min(im)).astype('uint8')
        except:
            import traceback
            traceback.print_exc()
        finally:
            if writer is not None:
                writer.release()
            if mmAvi is not None:
                mmAvi.release()
            print('done...')
