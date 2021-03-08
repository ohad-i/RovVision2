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

args = parser.parse_args()


recPath = args.recPath
skipFrame = args.skipFrame 
saveTiff = args.saveTiff
showVideo = args.showVideo


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
    cv2.namedWindow(winName, 0)
    cv2.setMouseCallback(winName, CallBackFunc)


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
    global curDelay, imgsPath, writer, writerLowRes
    

    if im is not None:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    
        showIm = np.copy(im)
    
        showIm = cv2.putText(showIm, '%04d '%(frameId), org, font,
                   fontScale, color, thickness, cv2.LINE_AA)


        if writer is None and im is not None:
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
        elif im is not None:
            writer.write(showIm)

    
        if imgsPath is None:
            imgsPath = os.path.join(recPath, 'imgs')
            if not os.path.exists(imgsPath):
                os.system('mkdir -p %s'%imgsPath)

        if saveTiff:
            curImName = '%08d.tiff'%frameId
            #cv2.imwrite( os.path.join(imgsPath, curImName), im,  [cv2.IMWRITE_JPEG_QUALITY, 100] )
            cv2.imwrite( os.path.join(imgsPath, curImName), im )
    
        if showVideo:
            cv2.imshow(winName, showIm) #im[:200,:])

            key = cv2.waitKey(curDelay)&0xff
            if key == ord('q'):
                return False
            elif key == ord(' '):
                curDelay = 0
            elif key == ord('+'):
                curDelay = max(1, curDelay-5 )
            elif key == ord('-'):
                curDelay = min(1000, curDelay+5 )
            elif key == ord('r'):
                curDelay = 100
        else:
            print('current frame process %d'%frameId)

    if imLowRes is not None:
        imLowRes = cv2.cvtColor(imLowRes, cv2.COLOR_BGR2RGB)
        showImLow = np.copy(imLowRes)
        showImLow = cv2.putText(showImLow, '%04d '%(frameId), org, font,
                   fontScale/2, color, thickness, cv2.LINE_AA)

        if writerLowRes is None:
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
        else:
            writerLowRes.write(showImLow)


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
                print('reuse publisher port: %d'%topic[1])
                topicPubDict[topic[0]] = topicPubDict[revTopicPubDict[topic[1]]]
            else:
                print('creats publisher on port: %d'%topic[1])
                topicPubDict[topic[0]] = utils.publisher(topic[1])
                revTopicPubDict[topic[1]] = topic[0]
                pubList.append(topic[1])
        
        if recPath is not None:
            vidPath = os.path.join(recPath, 'video.bin')
            vidQPath = os.path.join(recPath, 'videoQ.bin')
            telemPath = os.path.join(recPath, 'telem.pkl')
            imgCnt = 0
            imRaw = None
            highResEndFlag = False
            lowResEndFlag = False
            telemRecEndFlag = False
            with open(vidPath, 'rb') as vidFid:
                with open(vidQPath, 'rb') as vidQFid:
                    with open(telemPath, 'rb') as telFid:
         
                        while True:
                            try:
                                data = pickle.load(telFid)
                            except:
                                if not telemRecEndFlag:
                                    print('record Ended...')
                                    telemRecEndFlag = True
                                    break
                                
        
                            curTopic = data[1][0]
                            #print('curTopic',curTopic)
        
                            if curTopic == zmq_topics.topic_stereo_camera:
                                frameId += 1
                                ## handle image
                                metaData = pickle.loads(data[1][1])
                                imShape = metaData[1]
                                imgCnt += 1
                                # load image
                                try:
                                    '''
                                    imLowRes = np.fromfile(vidQFid, count=imShape[1]//2*imShape[0]//2*imShape[2], 
                                                           dtype = 'uint8').reshape((imShape[1]//2, imShape[0]//2, imShape[2] ))
                                    '''
                                    imLowRes = None
                                    
                                    
                                except:
                                    imLowRes = None
                                    if not lowResEndFlag:
                                        print('low res video ended')
                                        lowResEndFlag = True
                                if imgCnt%4 == 0:
                                    try:
                                        imRaw = np.fromfile(vidFid, count=imShape[1]*imShape[0]*imShape[2], dtype = 'uint8').reshape(imShape)
                                    except:
                                        imRaw = None
                                        if not highResEndFlag:
                                            print('high res video ended')
                                            highResEndFlag = True
                                else:
                                    imRaw = None
                                ret = vidProc(imRaw, imLowRes)
                               
                                if not ret:
                                    break
                                topicPubDict[curTopic].send_multipart(data[1])
                            else:
                                #pass
                                topicPubDict[curTopic].send_multipart(data[1])
                    
                      
    except:
        import traceback
        traceback.print_exc()
    finally:
        if writer is not None:
            writer.release()
        print("done...")            
        
