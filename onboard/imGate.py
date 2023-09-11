# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
#resposible for recording/preprossesing/distributing sensor data
import numpy as np
import zmq
import sys
import asyncio
import time
import pickle
import cv2


sys.path.append('..')
sys.path.append('../utils')
import zmq_wrapper
import zmq_topics
import config
import cv2
import socket

import argparse

subs_socks=[]
subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_stereo_camera],zmq_topics.topic_camera_port))
keep_running=True

doResize = True
sx,sy=config.cam_res_rgbx,config.cam_res_rgby

parser = argparse.ArgumentParser(description='Image udp gate', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-l', '--localSend', action='store_true', help='Recieve raw video')
args = parser.parse_args()


if args.localSend:
    udpImIpPort = ('', int(config.udpPort))
else:
    udpImIpPort = (config.groundIp, int(config.udpPort))




jpgQuality = 75
maxImSize = 1024*63


inImgCnt = 0.0
sentImgCnt = 0.0

async def recv_and_process():
    global current_command, inImgCnt, sentImgCnt, jpgQuality
    tic = time.time()
    udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    
    while keep_running:
        socks=zmq.select(subs_socks,[],[],0.005)[0]
        for sock in socks:
            ret=sock.recv_multipart()
            if ret[0]==zmq_topics.topic_stereo_camera:
                inImgCnt += 1
                
                frame_cnt,shape,ts, camState, hasHighRes = pickle.loads(ret[1])
                imgl = np.frombuffer(ret[-2],'uint8').reshape( (shape[0]//2, shape[1]//2, 3) ).copy()
                
                if 0: #doResize:
                    imgl = cv2.resize(imgl, (sx,sy))
                #cv2.imshow('aa', imgl)
                #cv2.waitKey(10)
                
                ret, encIm = cv2.imencode('.jpg', imgl, [cv2.IMWRITE_JPEG_QUALITY, jpgQuality])
                doSend = True
                #print(imgl.shape, jpgQuality, len(encIm))
                if len(encIm) < 1024*55:
                    jpgQuality = min(100, jpgQuality+1)
                elif len(encIm) >= maxImSize:
                    print(len(encIm))
                    jpgQuality = max(10, jpgQuality-10)
                    doSend = False
                #import ipdb; ipdb.set_trace() 
                msg = pickle.dumps([frame_cnt, camState['expVal'], encIm])
                if doSend:
                    sentImgCnt += 1
                    udpSock.sendto(msg, udpImIpPort)

            if time.time() - tic >= 7:
                inImgFPS = inImgCnt/(time.time() - tic)
                sentFPS = sentImgCnt/(time.time() - tic)

                print(tic, 'input image %.2f FPS, sent %.2f FPS, jpgQual: %d'%(inImgFPS, sentFPS, jpgQuality))
                inImgCnt = 0.0
                sentImgCnt = 0.0
                tic = time.time()

        await asyncio.sleep(0.001)
 
async def main():
    await asyncio.gather(
            recv_and_process(),
            )

if __name__=='__main__':
    #asyncio.run(main())
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())




