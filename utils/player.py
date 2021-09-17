import os
import cv2
import sys
import glob
import numpy as np
import argparse
import time
import sys
sys.path.append('../')

import zmq
import zmq_topics
import pickle
import zmq_wrapper as utils

import recorder 
topicsList = recorder.topicsList


usageDescription = 'usage while playing: \n\t(-) press space to run frame by frame \n\t(-) press r ro run naturally, ~10Hz \n\t(-) press +/- to increase/decrease playing speed'

parser = argparse.ArgumentParser(description='synced record parser, %s'%usageDescription, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-r', '--recPath', default=None, help=' path to record ')
parser.add_argument('-s', '--skipFrame', type=int, default=-1, help='start of parsed frame, by frame counter not file index')
parser.add_argument('-t', '--saveTiff', action='store_true', help='save tiffs files to record folder')
parser.add_argument('-q', '--showVideo', action='store_false', help='quite run, if -q - parse only, no show')
parser.add_argument('-f', '--freeRun', action='store_true', help='Not true realtime')
parser.add_argument('-V', '--saveAvi', action='store_true', help='quite run, if -V - create avi files')

args = parser.parse_args()


recPath = args.recPath
skipFrame = args.skipFrame 
saveTiff = args.saveTiff
showVideo = args.showVideo
saveAvi = args.saveAvi
highSpeed = args.freeRun


print(usageDescription)

if recPath == None:
    sys.exit(1)


def CallBackFunc(event, x, y, flags, params):

     if  ( event == cv2.EVENT_LBUTTONDOWN ):
          print("---> %d %d %d"%(x, y, -11) )
     elif  ( event == cv2.EVENT_RBUTTONDOWN ):
         pass
     elif  ( event == cv2.EVENT_MBUTTONDOWN ):
         pass
     elif ( event == cv2.EVENT_MOUSEMOVE ):
         pass

if showVideo:
    winName = 'player'
    winNameLowRes = 'player - low Res'
    cv2.namedWindow(winNameLowRes, 0)
    #cv2.setMouseCallback(winName, CallBackFunc)


frameId = 0
curDelay = 0

###
font = cv2.FONT_HERSHEY_COMPLEX_SMALL
org = (30, 30)
fontScale = 2 #0.65
color = (255, 255, 255)
thickness = 2
##

imgsPath = None
writer = None
writerLowRes = None


def vidProc(im, imLowRes, imPub = None):
    global curDelay, highSpeed, imgsPath, writer, writerLowRes
    

    if im is not None:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    
        showIm = np.copy(im)
    
        showIm = cv2.putText(showIm, '%04d '%(frameId), org, font,
                   fontScale, color, thickness, cv2.LINE_AA)


        if saveAvi and writer is None and im is not None:
            (h, w) = showIm.shape[:2]
            ### option for uncompressed raw
            #fourcc = cv2.VideoWriter_fourcc(*'DIB ')
            #fourcc = cv2.VideoWriter_fourcc(*'3IVD')
            fourcc = cv2.VideoWriter_fourcc(*'RGBA')
            #fourcc = cv2.VideoWriter_fourcc(*'DIVX')
            #import ipdb; ipdb.set_trace()
            vidFileName = os.path.join(recPath, 'out.avi')
            writer = cv2.VideoWriter(vidFileName, fourcc, 2,
                                             (w, h), True)
            writer.write(showIm)
        elif saveAvi and im is not None:
            writer.write(showIm)

    
        if imgsPath is None:
            imgsPath = os.path.join(recPath, 'imgs')
            if not os.path.exists(imgsPath):
                os.system('mkdir -p %s'%imgsPath)

        if saveTiff:
            curImName = '%08d.tiff'%frameId
            #cv2.imwrite( os.path.join(imgsPath, curImName), im,  [cv2.IMWRITE_JPEG_QUALITY, 100] )
            cv2.imwrite( os.path.join(imgsPath, curImName), im )
            #curImName = '%08d.jpg'%frameId
            #cv2.imwrite( os.path.join(imgsPath, curImName), im,  [cv2.IMWRITE_JPEG_QUALITY, 100] )
            
        if showVideo and 0:
            cv2.namedWindow(winName, 0)
            cv2.imshow(winName, showIm) #im[:200,:])
            

    if imLowRes is not None:
        imLowRes = cv2.cvtColor(imLowRes, cv2.COLOR_BGR2RGB)
        showImLow = np.copy(imLowRes)
        showImLow = cv2.putText(showImLow, '%04d '%(frameId), org, font,
                   fontScale/2, color, thickness, cv2.LINE_AA)

        if saveAvi and writerLowRes is None:
            (h, w) = showImLow.shape[:2]
            ### option for uncompressed raw
            #fourcc = cv2.VideoWriter_fourcc(*'DIB ')
            #fourcc = cv2.VideoWriter_fourcc(*'3IVD')
            fourcc = cv2.VideoWriter_fourcc(*'RGBA')
            #fourcc = cv2.VideoWriter_fourcc(*'DIVX')
            #import ipdb; ipdb.set_trace()
            vidFileName = os.path.join(recPath, 'outLowRes.avi')
            writerLowRes = cv2.VideoWriter(vidFileName, fourcc, 10,
                                                (w, h), True)
            writerLowRes.write(showImLow)
        elif saveAvi:
            writerLowRes.write(showImLow)
            
        if showVideo:
            cv2.imshow(winNameLowRes, showImLow) #im[:200,:])

            

    if showVideo:
        key = cv2.waitKey(curDelay)&0xff
        if key == ord('q'):
            return False
        elif key == ord(' '):
            curDelay = 0
        elif key == ord('+'):
            highSpeed = True
            curDelay = max(1, curDelay-5 )
        elif key == ord('-'):
            highSpeed = True
            curDelay = min(1000, curDelay+5 )
        elif key == ord('r'):
            highSpeed = False
            curDelay = 1
    else:
        pass 
        #print('current frame process %d'%frameId)

    return True


'''
cv2.namedWindow('low', 0)
cv2.namedWindow('high', 0)
'''
if __name__=='__main__':
    
    try:
        pubList = []
        topicPubDict = {}
        revTopicPubDict = {}
        for topic in topicsList:
            if topic[1] in pubList: # port already exist
                print('reuse publisher port: %d %s'%(topic[1], topic[0]) )  
                topicPubDict[topic[0]] = topicPubDict[revTopicPubDict[topic[1]]]
            else:
                print('creats publisher on port: %d %s'%(topic[1], topic[0]) )
                topicPubDict[topic[0]] = utils.publisher(topic[1])
                revTopicPubDict[topic[1]] = topic[0]
                pubList.append(topic[1])
        
        fpsTic = time.time()
        fpsCnt = 0.0
        
        if recPath is not None:
            vidPath = os.path.join(recPath, 'video.bin')
            vidQPath = os.path.join(recPath, 'videoQ.bin')
            telemPath = os.path.join(recPath, 'telem.pkl')
            imgCnt = 0
            imRaw = None
            highResEndFlag = False
            lowResEndFlag = False
            telemRecEndFlag = False
            
            telFid  = None
            vidFid  = None
            vidQFid = None
            
            if os.path.exists(telemPath):
                telFid = open(telemPath, 'rb')
            if os.path.exists(vidPath):
                vidFid = open(vidPath, 'rb')
            if os.path.exists(vidQPath):
                vidQFid = open(vidQPath, 'rb')
            
            telId = 0
            # skip frame loop 
            while frameId < skipFrame:
               
                curData = pickle.load(telFid)
                telId += 1                
                curTopic = curData[1][0]

                if curTopic == zmq_topics.topic_stereo_camera:
                    frameId += 1
                    hasHighRes = curData[1][-1]
                    metaData = pickle.loads(curData[1][1])
                    
                    imShape  = metaData[1]
                
                    try:
                        imLowRes = np.fromfile(vidQFid, count=imShape[1]//2*imShape[0]//2*imShape[2], 
                                           dtype = 'uint8').reshape((imShape[0]//2, imShape[1]//2, imShape[2] ))

                        if hasHighRes:
                            imRaw = np.fromfile(vidFid, count=imShape[1]*imShape[0]*imShape[2], dtype = 'uint8').reshape(imShape)
                    except:
                        pass
            else:
                curData = pickle.load(telFid)
            nextData = pickle.load(telFid)
            nextTicToc = 0.9*(nextData[0] - curData[0]) 

            #import ipdb; ipdb.set_trace()
            
            while True:
                
                time.sleep(0.0001)
                try:
                    data = curData #pickle.load(telFid)
                    telId += 1
                except:
                    if not telemRecEndFlag:
                        print('record Ended...')
                        telemRecEndFlag = True
                        break
                    

                curTopic = data[1][0]
                if curTopic == zmq_topics.topic_stereo_camera:
                    fpsCnt+=1
                    if time.time() - fpsTic >= 5:
                        fps = fpsCnt/(time.time() - fpsTic)
                        print('player video fps %0.2f'%fps)
                        fpsCnt = 0.0
                        fpsTic = time.time()
                        
                    frameId += 1
                    ## handle image
                    metaData = pickle.loads(data[1][1])
                    hasHighRes = data[1][-1]
                    
                    imShape  = metaData[1]
                    imgCnt  += 1
                    # load image
                    
                    if not lowResEndFlag:
                        
                        try:
                            imLowRes = np.fromfile(vidQFid, count=imShape[1]//2*imShape[0]//2*imShape[2], 
                                                   dtype = 'uint8').reshape((imShape[0]//2, imShape[1]//2, imShape[2] ))
                        except:
                            imLowRes = None
                            if not lowResEndFlag:
                                print('low res video ended')
                                lowResEndFlag = True
                                showVideo = False
                                continue
                        if hasHighRes:
                            try:
                                imRaw = np.fromfile(vidFid, count=imShape[1]*imShape[0]*imShape[2], dtype = 'uint8').reshape(imShape)
                            except:
                                imRaw = None
                                if not highResEndFlag:
                                    print('high res video ended')
                                    highResEndFlag = True
                                    continue
                        else:
                            imRaw = None
                        
                        ret = vidProc(imRaw, imLowRes)
                       
                        if not ret:
                            break
    
                        #import ipdb; ipdb.set_trace()
                        videoMsg = [zmq_topics.topic_stereo_camera,
                                            pickle.dumps((metaData[0], imLowRes.shape, metaData[2])),
                                                imLowRes.tobytes()] # [topic, (frameId, frameShape, ts) rawFrame]
                        #print('-->', curTopic)
                        topicPubDict[curTopic].send_multipart(videoMsg)
                        
                else:
                    #recTs = data[0]
                    telData = pickle.loads(data[1][1])
                    topicPubDict[curTopic].send_multipart([curTopic, pickle.dumps(telData)] )
                    
                    #pass
                    #topicPubDict[curTopic].send_multipart(data[1])
            
                curData = nextData
                nextData = pickle.load(telFid)
                    
                if not highSpeed:
                    time.sleep(nextTicToc)
                    nextTicToc = 0.6*(nextData[0] - curData[0])
                    ### workaround - overcome a problem of serialization of telemetry
                    # next step is calculated by the telemtry time stamp - which can 
                    #recorded not in the right order, the player should be run initially by the recorder ts
                    ###
                    if nextTicToc<0:
                        nextTicToc = 0
                        print('--err--> next sleep err: %.5f'%(nextData[0]-curData[0] ) )
                    ###############################################################
                      
    except:
        import traceback
        traceback.print_exc()
    finally:
        print("--->",frameId, telId)
        if writer is not None:
            writer.release()
        if writerLowRes is not None:
            writerLowRes.release()
        print("done...")            
        
