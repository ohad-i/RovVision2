# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import zmq
import sys
import asyncio
import time
import pickle
import traceback

sys.path.append('..')
sys.path.append('../utils')
sys.path.append('../onboard')
import zmq_wrapper 
import zmq_topics
import config

from tracker import simpleTracker as sTracker

async def recv_and_process():
    keep_running=True
    tracker = sTracker.tracker()
    tracker.init()
    imBuffer = {}
    maxImBuffer = 20
    
    
    system_state={'mode':[]}
    trackerInitiated = False
    
    while keep_running:
        socks=zmq.select(subs_socks,[],[],0.005)[0]
        for sock in socks:
            ret=sock.recv_multipart()
            topic, data = ret[0],pickle.loads(ret[1])

            if topic==zmq_topics.topic_stereo_camera:
                frameCnt, shape,ts, curExp, hasHighRes=pickle.loads(ret[1])
                frame = np.frombuffer(ret[-2],'uint8').reshape( (shape[0]//2, shape[1]//2, 3) ).copy()

                if 'IM_TRACKER_MODE' in system_state['mode'] and trackerInitiated:
                    trackRes = tracker.track(frame)
                    #print('--->', trackRes)
                    
                    if tracker.trackerInit:
                        if trackRes is not None:
                            msg = [zmq_topics.topic_tracker_result, pickle.dumps([frameCnt, trackRes])]
                            sock_pub.send_multipart(msg)
                    else:
                        trackerInitiated = False
                        sock_pub.send_multipart([zmq_topics.topic_tracker_result, pickle.dumps([frameCnt, trackRes]) ])
                        
                 
                
            elif topic == zmq_topics.topic_tracker_cmd:
                #print('-->', data)
                if data['frameId'] == -1:
                    tracker.stopTracker()
                    trackerInitiated = False
                    sock_pub.send_multipart([zmq_topics.topic_tracker_result, pickle.dumps([-1, [-1,-1]]) ])
                    print('got kill tracker...')
                else:
                    trackerInitiated = tracker.initTracker(data['trackPnt'])
                    trackRes = tracker.track(frame)
                    print('--->', trackerInitiated, data['trackPnt'] )
            if topic==zmq_topics.topic_system_state:
                system_state=data
                
             
                

        await asyncio.sleep(0.001)
 

async def main():
    await asyncio.gather(
            recv_and_process(),
            )

if __name__=='__main__':
    ### plugin inputs
    subs_socks=[]
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_stereo_camera], zmq_topics.topic_camera_port)     )
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_system_state, 
                                             zmq_topics.topic_tracker_cmd],   zmq_topics.topic_controller_port) )
    
    ### plugin outputs
    sock_pub=zmq_wrapper.publisher(zmq_topics.topic_tracker_port)
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())
    #asyncio.run(main())


