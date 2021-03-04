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
showImage = args.showVideo


print(usageDescription)

if recPath == None:
    sys.exit(1)


def CallBackFunc(event, x, y, flags, params):

     if  ( event == cv2.EVENT_LBUTTONDOWN ):
          if x > imWidth:
              x = x-imWidth
          print("---> %d %d %d"%(x, y, im[y,x]) )
     elif  ( event == cv2.EVENT_RBUTTONDOWN ):
         pass
     elif  ( event == cv2.EVENT_MBUTTONDOWN ):
         pass
     elif ( event == cv2.EVENT_MOUSEMOVE ):
         pass

winName = 'player'
cv2.namedWindow(winName, 0)



cv2.setMouseCallback(winName, CallBackFunc)


frameId = 0
curDelay = 0

###
font = cv2.FONT_HERSHEY_COMPLEX_SMALL
org = (10, 30)
fontScale = 0.65
color = (255, 255, 255)
thickness = 1
##

imgsPath = None
writer = None


def vidProc(im, imPub = None):
    global curDelay, imgsPath, writer
    
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    
    showIm = np.copy(im)
    
    showIm = cv2.putText(showIm, '%04d '%(frameId), org, font,
               fontScale, color, thickness, cv2.LINE_AA)

    if writer is None:
        (h, w) = showIm.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        writer = cv2.VideoWriter('out.avi', fourcc, 10,
                                             (w, h), True)
    else:
        writer.write(showIm)

    
    if imgsPath is None:
        imgsPath = os.path.join(recPath, 'imgs')
        if not os.path.exists(imgsPath):
            os.system('mkdir -p %s'%imgsPath)

    is saveTiff:
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
    return True


if __name__=='__main__':
    
    try:
        pubList = []
        topicPubDict = {}
        
        for topic in topicsList:
            if topic[1] in pubList: # port already exist
                pass
            else:
                print('creats publisher on port: %d'%topic[1])
                topicPubDict[topic[0]] = utils.publisher(topic[1])

        if recPath is not None:
            vidPath = os.path.join(recPath, 'video.bin')
            telemPath = os.path.join(recPath, 'telem.pkl')
            with open(vidPath, 'rb') as vidFid:
                with open(telemPath, 'rb') as telFid:

                    while True:
                        data = pickle.load(telFid)

                        curTopic = data[1][0]
                        print('curTopic',curTopic)

                        if curTopic == zmqTopics.topic_stereo_camera:
                            frameId += 1
                            ## handle image
                            metaData = pickle.loads(data[1][1])
                            imShape = metaData[1]

                            # load image
                            imRaw = np.fromfile(vidFid, count=imShape[1]*imShape[0], dtype = 'uint8').reshape(imShape)
                            vidProc(imRaw)
                            #topicPubDict[curTopic].send_multipart(data[1])
                        else:
                            topicPubDict[curTopic].send_multipart(data[1])
                
                      
    except:
        import traceback
        traceback.print_exc()
    finally:
        if writer is not None:
            writer.release()
        print("done...")            
        
