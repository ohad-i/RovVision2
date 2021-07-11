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
import mixer

from pid import PID
from config_pid import yaw_pid, roll_pid, pos_pid_x, pitch_im_pid

print(pos_pid_x)
from tracker import simpleTracker as sTracker

async def recv_and_process():
    keep_running=True
    tracker = sTracker.tracker()
    tracker.init()
    imBuffer = {}
    maxImBuffer = 20
    
    
    system_state={'mode':[]}
    trackerInitiated = False
    
    curYaw, curPitch, curRoll = 0.0, 0.0, 0.0
    rates = [0]*3
    
    ## IDS
    fovX = 40.58 # deg.
    fovY = 30.23 # deg.
    
    pidY = None
    pidP = None
    pidR = None
    pidX = None
    
    tPitch = 0.0
    tRoll = 0.0
    tYaw = 0.0
    tX = 0.0
    
    
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
                            centerX = frame.shape[1]//2
                            centerY = frame.shape[0]//2
                            
                            iFovX = fovX/frame.shape[1]
                            iFovY = fovY/frame.shape[0]
                            
                            #import ipdb; ipdb.set_trace()
                            trckResCenteredX = (trackRes[0] - centerX)*iFovX
                            trckResCenteredY = -(trackRes[1] - centerY)*iFovY
                            
                            #print('--> dx=%f, dy=%f'%(trckResCenteredX-curYaw, trckResCenteredY+curPitch) )
                            
                            if pidX == None:
                                tYaw = curYaw
                                pidX = PID(**pos_pid_x)
                                pidY = PID(**yaw_pid)
                                pidP = PID(**pitch_im_pid)
                                pidR = PID(**roll_pid)
                            
                            tPitch = curPitch+trckResCenteredY
                            tX = centerX - trackRes[0] 
                            
                            print('--> dx=%f, dp=%f'%(trackRes[0]-centerX, tPitch-curPitch) )
                            pitchCmd = pidP(curPitch, tPitch, 0, 0)
                            rollCmd  = 0 #pidR(curRoll, tRoll, 0, 0)
                            yawCmd   = pidY(curYaw, tYaw, 0, 0)

                            ts=time.time()
                            debug_pid = {'P':pidR.p,'I':pidR.i,'D':pidR.d,'C':rollCmd,'T':tRoll,'N':curRoll, 'R':rates[0], 'TS':ts}
                            pub_sock.send_multipart([zmq_topics.topic_att_hold_roll_pid, pickle.dumps(debug_pid,-1)])
                            debug_pid = {'P':pidP.p,'I':pidP.i,'D':pidP.d,'C':pitchCmd,'T':tPitch,'N':curPitch, 'R':rates[1],'TS':ts}
                            pub_sock.send_multipart([zmq_topics.topic_att_hold_pitch_pid, pickle.dumps(debug_pid,-1)])
                            debug_pid = {'P':pidY.p,'I':pidY.i,'D':pidY.d,'C':yawCmd,'T':tYaw,'N':curYaw, 'R':rates[2], 'TS':ts}
                            pub_sock.send_multipart([zmq_topics.topic_att_hold_yaw_pid, pickle.dumps(debug_pid,-1)])
                        
                            xCmd = pidX(tX, 0)
                            print('xCmd: %f tx: %f'%(xCmd, tX), pidX.p, pidX.i, pidX.d)
                            
                            thrusterCmd = np.array(mixer.mix(0, xCmd, 0, rollCmd, pitchCmd, yawCmd, curPitch, curRoll))
                            #print( {'P':pidX.p,'I':pidX.i,'D':pidX.d,'C':xCmd,'T':tX,'N':0, 'TS':ts} )
                            
                            thrusterCmd += mixer.mix(0, 
                                                      0, 
                                                      0, 
                                                      0, 
                                                      -rates[1]*pidP.D,
                                                      -rates[2]*pidY.D, 
                                                      0, 
                                                      0)
                            
                            thrusters_source.send_pyobj(['trck',time.time(),thrusterCmd])
                            
                    else:
                        print('oitracker break...')
                        trackerInitiated = False
                        sock_pub.send_multipart([zmq_topics.topic_tracker_result, pickle.dumps([frameCnt, (-1,-1)]) ])
                        
                            
                        if pidX is not None:
                            print('kill controllers...')
                            pidY.reset(),pidP.reset(),pidX.reset()
                            
                            pidY = None
                            pidP = None
                            pidX = None
                        
                            thrusters_source.send_pyobj(['trck', time.time(), mixer.zero_cmd()])
                        
            if topic == zmq_topics.topic_imu:
                curYaw, curPitch, curRoll = data['yaw'],data['pitch'],data['roll']
                rates = [x/np.pi*180 for x in data['rates']]
                
                
            elif topic == zmq_topics.topic_tracker_cmd:
                #print('-->', data)
                if data['frameId'] == -1:
                    tracker.stopTracker()
                    trackerInitiated = False
                    sock_pub.send_multipart([zmq_topics.topic_tracker_result, pickle.dumps([-1, [-1,-1]]) ])
                    
                    if pidX is not None:
                        pidY.reset(),pidP.reset(),pidX.reset()
                        
                        pidY = None
                        pidP = None
                        pidX = None
                    
                        thrusters_source.send_pyobj(['trck', time.time(), mixer.zero_cmd()])
                    
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
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_stereo_camera],   zmq_topics.topic_camera_port)     )
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_imu],             zmq_topics.topic_imu_port))
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_system_state, 
                                             zmq_topics.topic_tracker_cmd],     zmq_topics.topic_controller_port) )
    
    ### plugin outputs
    sock_pub=zmq_wrapper.publisher(zmq_topics.topic_tracker_port)
    
    thrusters_source = zmq_wrapper.push_source(zmq_topics.thrusters_sink_port)
    pub_sock         = zmq_wrapper.publisher(zmq_topics.topic_imHoldPos_port)

    
    
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())
    #asyncio.run(main())


