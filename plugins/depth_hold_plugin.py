# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import zmq
import sys
import asyncio
import time
import pickle

sys.path.append('..')
sys.path.append('../utils')
sys.path.append('../onboard')
import mixer
import zmq_wrapper
import zmq_topics
from joy_mix import Joy_map
from config_pid import depth_pid
from pid import PID
from filters import ab_filt

import os
import commonPlugins

async def recv_and_process():
    global depth_pid
    
    keep_running=True
    pitch,roll=0,0
    target_depth=0
    pid=None
    ab=None
    rate=0
    system_state={'mode':[]}
    jm=Joy_map()
    
    tmpPIDS = "/tmp/tmpDepthConfigPid.json"

    while keep_running:
        socks=zmq.select(subs_socks,[],[],0.005)[0]
        for sock in socks:
            ret=sock.recv_multipart()
            topic,data=ret[0],pickle.loads(ret[1])
            
            if os.path.exists(tmpPIDS):
                _, _, _, depth_pid = commonPlugins.reloadPIDs(tmpPIDS)
                os.remove(tmpPIDS)
                pid = None
                print('Update pids and reset plugin...')

            if topic==zmq_topics.topic_depth:
                new_depth_ts, depth=data['ts'],data['depth']
                if ab is None:
                    ab=ab_filt([depth,0])
                else:
                    depth,rate=ab(depth,new_depth_ts-depth_ts)
                depth_ts=new_depth_ts

                if 'DEPTH_HOLD' in system_state['mode']:
                    if pid is None:
                        pid=PID(**depth_pid)
                    else:
                        ts = time.time()
                        ud_command = pid(depth,target_depth,rate,0)
                        debug_pid = {'ts':ts, 'P':pid.p,'I':pid.i,'D':pid.d,'C':ud_command,'T':target_depth,'N':depth,'TS':new_depth_ts}
                        pub_sock.send_multipart([zmq_topics.topic_depth_hold_pid, pickle.dumps(debug_pid,-1)])
                        thruster_cmd = mixer.mix(ud_command,0,0,0,0,0,pitch,roll)
                        thrusters_source.send_pyobj(['depth',time.time(),thruster_cmd])
                else:
                    if pid is not None:
                        print('turn off deptch hold')
                        pid.reset()
                        pid = None
                    thrusters_source.send_pyobj(['depth',time.time(),mixer.zero_cmd()])
                    target_depth=depth


            elif topic==zmq_topics.topic_axes:
                jm.update_axis(data)
                target_depth+=jm.joy_mix()['ud']/100.0

            elif topic==zmq_topics.topic_gui_depthAtt:
                if 'POSITION' not in system_state['mode']:
                    if data['dDepth'] is not None:
                        target_depth = data['dDepth'] 
                        print('set new depth: %.2f'%target_depth)
            
            elif topic == zmq_topics.topic_mission_cmd:
                if 'MISSION' in system_state['mode']:
                    if data['dDepth'] is not None:
                        target_depth = data['dDepth'] 
                        print('set new depth: %.2f'%target_depth)
                
            elif topic==zmq_topics.topic_imu:
                pitch,roll=data['pitch'],data['roll']

            elif topic==zmq_topics.topic_system_state:
                system_state=data

        await asyncio.sleep(0.001)

async def main():
    await asyncio.gather(
            recv_and_process(),
            )

if __name__=='__main__':
    ### plugin inputs
    subs_socks=[]
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_axes],            zmq_topics.topic_joy_port))
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_imu],             zmq_topics.topic_imu_port))
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_depth],           zmq_topics.topic_depth_port))
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_system_state],    zmq_topics.topic_controller_port))
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_gui_depthAtt],    zmq_topics.topic_gui_port))
    subs_socks.append(zmq_wrapper.subscribe([zmq_topics.topic_mission_cmd],     zmq_topics.topic_mission_port))

    ### plugin outputs
    thrusters_source = zmq_wrapper.push_source(zmq_topics.thrusters_sink_port)
    pub_sock = zmq_wrapper.publisher(zmq_topics.topic_depth_hold_port)


    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())
    #asyncio.run(main())
