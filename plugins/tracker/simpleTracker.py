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

from threading import Lock, Thread


class tracker:
    def __init__(self):
        print('init lk tracker...')
        self.trackerInit = False
        self.trackPnt = None
        
        self.Preds = 16
        
        self.lk_params = {} #dict(winSize = (15,15),
                            #  maxLevel = 4,
                            #  criteria = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 10, 0.03) )

        self.prevFrame = None
        self.name = ''
        self.outQueue = None
        
        self.signal = Lock()
        self.trackerInit = False
        
        '''
        # in case of improving track point using goodfeature to track        
        self.feature_params = dict(maxCorners = 100,
                                   qualityLevel = 0.3,
                                   minDistance = 7,
                                   blockSize = 7 )
        '''
        
        
        
    def init(self, name = '<tracker>', winSize = 40, maxLevel = 5, criteriaCount = 50, criteriaEPS =  0.01):
        
        self.name = name
        self.lk_params = dict(winSize = (winSize, winSize),
                          maxLevel = maxLevel,
                          criteria = (cv2.TERM_CRITERIA_COUNT | 
                                      cv2.TERM_CRITERIA_EPS | 
                                      cv2.OPTFLOW_USE_INITIAL_FLOW, 
                                      criteriaCount, criteriaEPS) )


    def initTracker(self, trackPnt):
        #print self.name,' got init track...', trackPnt, startImId
        
        with self.signal:
            self.trackPnt = trackPnt
            self.trackPntAr = [trackPnt]* self.Preds # list [x, y]
            self.offsetVec = []
            self.searchRadius = 10
            for i in range(-2,2):
                for j in range(-2,2):
                    self.offsetVec.append(np.array([i,j])*self.searchRadius)
            
            
            self.prevFrame = None
            self.trackerInit = True
            
        return self.trackerInit
        
    def stopTracker(self): ## safe
        #print 'stop tracking I....'
        with self.signal:
            self.trackerInit = False
            self.prevFrame = None        
            
            #print 'stop tracking II ....'
            self.trackPnt = None
            
        print('stop tracking.... ext.')
    
    def intenalStopTracker(self): 
        #print 'stop tracking I....'
        self.trackerInit = False
        self.prevFrame = None        
        
        #print 'stop tracking II ....'
        self.trackPnt = None
        
        
        print('stop tracking.... int.')
    
    
                        
    def track(self, inImg):
        
        flag = self.trackerInit
        #import ipdb; ipdb.set_trace() 
        
        if flag or (self.trackPnt is not None):
            if inImg is not None:
                image = np.copy(inImg)
                if self.prevFrame is not None:
                    
                    with self.signal:
                        guess = self.offsetVec + np.array(self.trackPntAr)
                        p0 = np.float32(self.trackPntAr).reshape(-1,1,2)
                        p1 = np.float32(guess).reshape(-1,1,2)
                        
                        #print '1', self.prevFrame.shape
                        #print '2', image.shape
                        #print '3', p0.shape
                        #print '4', p1.shape
                        predPntA, stA, err = cv2.calcOpticalFlowPyrLK(self.prevFrame, image, p0, p1, **self.lk_params)
                        err[stA==0] = 10000000
                        idx = np.argmin(err)
                        #print '--->', err[idx], stA[idx]
                        st = stA[idx]
                        predPnt = predPntA[idx]
                        
                        if (st is not None ) and ( len(st.nonzero()) > 0 ) and (err[idx] < 40):
                            try:
                                #print '--------', len(st.nonzero()[0]), st.nonzero()[0]
                                self.trackPnt = predPnt[0] #[0][0]
                                #print self.name, '--->', self.trackPnt, predPnt
                                
                                self.trackPntAr = [self.trackPnt]* self.Preds
                                #showImg = cv2.cvtColor(image, cv2.cv.CV_GRAY2BGR)
                                #cv2.circle(showImg, (int(self.trackPnt[0]), int(self.trackPnt[1])), 2, (255,255,255), -1 )
                                #cv2.imshow('<tracker>', showImg)
                                #cv2.waitKey(1)
                                
                                self.prevFrame = image
                                return self.trackPnt
                            except:
                                self.intenalStopTracker()
                                import traceback
                                traceback.print_exc()
                                print(self.name,' tarcker failed (exception)...'*3)
                                return None
                            
                        else:
                            self.intenalStopTracker()
                            print(self.name,' tarcker failed, prediction didnt detected...'*3)
                            return None
                        
                else:
                    self.prevFrame = image
                    return None
                    

if __name__=='__main__':

    winName = 'tracker'
    trck = tracker()
    trck.init()
    trackPnt = None
    trackerInit = False


    def startTrack(event,x,y,flags,param):
        global trackPnt, trackerInit
        if event == cv2.EVENT_LBUTTONDOWN:
            print('start tracker: ', x, y)
            trackPnt = [x, y]
            trck.initTracker(trackPnt)
            trackerInit = True
        if event == cv2.EVENT_MBUTTONDOWN:
            print('stop tracker')
            trackerInit = False
            trck.stopTracker()

    cv2.namedWindow(winName, 0)
    cv2.setMouseCallback(winName, startTrack)
    
    fileName = r'outLowRes.avi'
    cap = cv2.VideoCapture(fileName)
    ret, im = cap.read()
    wait = 0 #200 # ms, 0->infinite
    

    cnt = 0.0
    tic = time.time()
    while ret:
        cnt += 1
        if time.time() - tic >= 5:
            fps = cnt/(time.time()-tic)
            print('cur fps: %0.2f, wait=%d ms'%(fps, wait))
            cnt = 0.0
            tic = time.time()

        if trackerInit:
            trckRes = trck.track(im)
            if trckRes is not None:
                #print('track res: ', trckRes)
                cv2.circle(im, (trckRes[0], trckRes[1]), 10, (0,0,255), -1)

        cv2.imshow(winName, im)
        key = cv2.waitKey(wait)
        if key&0xff == 27 or key&0xff == ord('q'):
            break
        if key&0xff == ord('+'):
            wait = max(10, wait-10)
        if key&0xff == ord('-'):
            wait = wait+10
        if key&0xff == ord(' '):
            cv2.waitKey(0)

        ret, im = cap.read()
