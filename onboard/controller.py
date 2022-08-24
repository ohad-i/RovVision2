# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import zmq
import sys
import asyncio
import time
import pickle
import os

sys.path.append('..')
sys.path.append('../utils')
import zmq_wrapper as utils
import zmq_topics
from joy_mix import Joy_map

import json


pub_sock = utils.publisher(zmq_topics.topic_controller_port)
camPubSock = utils.publisher(zmq_topics.topic_cam_ctrl_port)

subs_socks=[]
subs_socks.append(utils.subscribe([zmq_topics.topic_axes,zmq_topics.topic_button],zmq_topics.topic_joy_port))
subs_socks.append(utils.subscribe([zmq_topics.topic_imu],zmq_topics.topic_imu_port))
subs_socks.append(utils.subscribe([zmq_topics.topic_gui_controller, 
                                   zmq_topics.topic_gui_diveModes, 
                                   zmq_topics.topic_gui_focus_controller, 
                                   zmq_topics.topic_gui_autoFocus,
                                   zmq_topics.topic_gui_start_stop_track,
                                   zmq_topics.topic_gui_toggle_auto_exp,
                                   zmq_topics.topic_gui_toggle_auto_gain,
                                   zmq_topics.topic_gui_inc_exp,
                                   zmq_topics.topic_gui_dec_exp, 
                                   zmq_topics.topic_gui_exposureVal,
                                   zmq_topics.topic_gui_update_pids],  zmq_topics.topic_gui_port))
subs_socks.append(utils.subscribe([zmq_topics.topic_autoFocus], zmq_topics.topic_autoFocus_port))
subs_socks.append(utils.subscribe([zmq_topics.topic_tracker_result], zmq_topics.topic_tracker_port))
                                   
thruster_sink = utils.pull_sink(zmq_topics.thrusters_sink_port)
subs_socks.append(thruster_sink)

focusResolution = 5


async def recv_and_process():
    keep_running=True
    thruster_cmd=np.zeros(8)
    timer10hz = time.time()+1/10.0
    timer20hz = time.time()+1/20.0
    
    thrustersRate = 50.0
    thrustersTimerHz = time.time()+1/thrustersRate
    
    timer0_1hz = time.time()+10
    
    initPwmFocus = 1400
    preFocusFileName = '../hw/focusState.bin'
    if os.path.exists(preFocusFileName):
        with open(preFocusFileName, 'r') as fid:
            initPwmFocus = int(fid.read(4))
            print('reset focus to:', initPwmFocus)
            
    gainCtl = -1
    expCtl = -1
    camStateFile = '../hw/camSate.pkl'
    if os.path.exists(camStateFile):
        try:
            with open(camStateFile, 'rb') as fid:
                camState = pickle.load(fid)
                if 'aGain' in camState.keys():
                    gainCtl = camState['aGain']
                if 'aExp' in camState.keys():
                    expCtl = camState['aExp']
        except:
            print('no cam state...')

    
    diskUsage = int(os.popen('df -h / | tail -n 1').readline().strip().split()[-2][:-1])
    system_state={'ts':time.time(), 
                  'arm':False,
                  'mode':[], 
                  'lights':0, 
                  'focus':initPwmFocus, 
                  'record':False, 
                  'diskUsage':diskUsage,
                  'autoGain':gainCtl,
                  'autoExp':expCtl} #lights 0-5
    
    thrusters_dict={}

    jm=Joy_map()

    def togle_mode(m):
        s=system_state
        if m in s['mode']:
            s['mode'].remove(m)
        else:
            s['mode'].append(m)


    def test_togle(b):
        return new_joy_buttons[b]==1 and joy_buttons[b]==0

    
    while keep_running:
        socks=zmq.select(subs_socks,[],[],0.002)[0]
        for sock in socks:
            if sock==thruster_sink:
                source,_,thruster_src_cmd=sock.recv_pyobj() 
                thrusters_dict[source]=thruster_src_cmd
            else:
                ret=sock.recv_multipart()
                topic,data=ret[0],pickle.loads(ret[1])
                
                if topic==zmq_topics.topic_button or topic==zmq_topics.topic_gui_diveModes:
                    
                    jm.update_buttons(data)
                    if jm.depth_hold_event():
                        print('Toggle depth hold...')
                        if ('IM_TRACKER_MODE' in system_state['mode']) and ('DEPTH_HOLD' in system_state['mode']):
                            print('failed to toggle to DEPTH_HOLD (needs to stay on DEPTH_HOLD) while IM_TRACKER_MODE')
                        else:
                            togle_mode('DEPTH_HOLD')
                    if jm.att_hold_event():
                        print('Toggle attitude hold...')
                        #if ('IM_TRACKER_MODE' in system_state['mode']) and ('ATT_HOLD' in system_state['mode']):
                        #    print('failed to toggle to ATT_HOLD (needs to stay on ATT_HOLD) while IM_TRACKER_MODE')
                        #else:
                        #    togle_mode('ATT_HOLD')
                        togle_mode('ATT_HOLD')
                    if jm.Rx_hold_event():
                        togle_mode('RX_HOLD')
                    if jm.Ry_hold_event():
                        togle_mode('RY_HOLD')
                    if jm.Rz_hold_event():
                        togle_mode('RZ_HOLD')
                    if jm.record_event():
                        system_state['record'] = not system_state['record']
                        print('record state', system_state['record'])
                    if jm.arm_event():
                        system_state['arm']=not system_state['arm']
                        print('state arm:', system_state['arm'])
                        if not system_state['arm']:
                            system_state['mode']=[]
                           
                elif topic==zmq_topics.topic_axes or topic==zmq_topics.topic_gui_controller:
                    jm.update_axis(data)
                    if jm.inc_lights_event():
                        system_state['lights']=min(5,system_state['lights']+1)
                        pub_sock.send_multipart([zmq_topics.topic_lights,pickle.dumps(system_state['lights'])])
                        print('lights set to ',system_state['lights'])
                    if jm.dec_lights_event():
                        system_state['lights']=max(0,system_state['lights']-1)
                        pub_sock.send_multipart([zmq_topics.topic_lights,pickle.dumps(system_state['lights'])])
                        print('lights set to ',system_state['lights'])
                    if jm.inc_focus_event():
                        system_state['focus']=min(2250,system_state['focus']+focusResolution)
                        pub_sock.send_multipart([zmq_topics.topic_focus,pickle.dumps(system_state['focus'])])
                        print('focus set to ',system_state['focus'])
                    if jm.dec_focus_event():
                        system_state['focus']=max(850,system_state['focus']-focusResolution)
                        pub_sock.send_multipart([zmq_topics.topic_focus,pickle.dumps(system_state['focus'])])
                        print('focus set to ',system_state['focus'])
                elif topic==zmq_topics.topic_gui_focus_controller or topic == zmq_topics.topic_autoFocus:
                    pwm = data
                    system_state['focus']=pwm
                    pub_sock.send_multipart([zmq_topics.topic_focus,pickle.dumps(system_state['focus'])])
                    print('focus set to value ',system_state['focus'])
                
                elif topic == zmq_topics.topic_gui_autoFocus:
                    os.system('../scripts/runAutofocus.sh')
                
                elif topic == zmq_topics.topic_gui_start_stop_track:
                    print('start/stop tracker... ', data)
                    '''
                    if 'ATT_HOLD' not in system_state['mode']:
                        togle_mode('ATT_HOLD')
                    '''
                    if 'DEPTH_HOLD' not in system_state['mode']:
                        togle_mode('DEPTH_HOLD')
                    
                    togle_mode('IM_TRACKER_MODE')
                    if 'IM_TRACKER_MODE' in system_state['mode']:
                        pub_sock.send_multipart([zmq_topics.topic_tracker_cmd, pickle.dumps(data)])
                    else:
                        pub_sock.send_multipart([zmq_topics.topic_tracker_cmd, pickle.dumps( {'frameId':-1, 'trackPnt':(-1,-1 ) } )])

                elif topic == zmq_topics.topic_tracker_result:
                    #print('--->', data)
                    if data[1][0] < 0:
                        if 'IM_TRACKER_MODE' in system_state['mode']:
                            print('Tracker ended...')
                            togle_mode('IM_TRACKER_MODE')
                elif topic == zmq_topics.topic_gui_toggle_auto_exp:
                    print('got auto exposure command')
                    if expCtl == 0:
                        expCtl = 1
                    else:
                        expCtl = 0
                    system_state['autoExp'] = expCtl 
                    camPubSock.send_multipart([zmq_topics.topic_cam_toggle_auto_exp, pickle.dumps(expCtl)])
                  
                
                elif topic == zmq_topics.topic_gui_toggle_auto_gain:
                    print('got auto gain command')
                    if gainCtl == 0:
                        gainCtl = 1
                    else:
                        gainCtl = 0
                    system_state['autoGain'] = gainCtl
                    camPubSock.send_multipart([zmq_topics.topic_cam_toggle_auto_gain, pickle.dumps(gainCtl)])
                    
                    
                elif topic == zmq_topics.topic_gui_inc_exp:
                    print('got camera inc exp.')
                    camPubSock.send_multipart([zmq_topics.topic_cam_inc_exp, pickle.dumps([0])])
                    
                                    
                elif topic == zmq_topics.topic_gui_dec_exp:
                    print('got camera dec exp.')
                    camPubSock.send_multipart([zmq_topics.topic_cam_dec_exp, pickle.dumps([0])])
                
                elif topic == zmq_topics.topic_gui_exposureVal:
                    print('got camera exp. value:', data)
                    camPubSock.send_multipart([zmq_topics.topic_cam_exp_val, pickle.dumps(data)])
                
                elif topic == zmq_topics.topic_gui_update_pids:
                    print('update PIDs... %s'%data['pluginUpdate'] )
                    if data['pluginUpdate'] == 'depth':
                        jsonFileName = "/tmp/tmpDepthConfigPid.json"
                    elif data['pluginUpdate'] == 'yaw' or data['pluginUpdate'] == 'roll' or data['pluginUpdate'] == 'pitch':
                        jsonFileName = "/tmp/tmpAttConfigPid.json"
                    with open(jsonFileName, 'w') as fid:
                        json.dump(data['data'], fid, indent=4)
                    
                
                
                        
                    


        tic=time.time()
        if tic-timer10hz>0:
            timer10hz=tic+1/10.0
            system_state['ts']=tic
            pub_sock.send_multipart([zmq_topics.topic_system_state,pickle.dumps(system_state)]) 
        if tic-thrustersTimerHz > 0:
            thrustersTimerHz=tic+1/thrustersRate
            if not system_state['arm']:
                thruster_cmd=np.zeros(8)
            else:
                for k in thrusters_dict:
                    thruster_cmd += thrusters_dict[k]
            pub_sock.send_multipart([zmq_topics.topic_thrusters_comand,pickle.dumps((tic,list(thruster_cmd)))])
            thruster_cmd = np.zeros(8)
        if tic-timer0_1hz>0:
            timer0_1hz=tic+10
            system_state['diskUsage'] = int(os.popen('df -h / | tail -n 1').readline().strip().split()[-2][:-1])


                #print('botton',ret)

        await asyncio.sleep(0.001)
 
async def main():
    await asyncio.gather(
            recv_and_process(),
            )

if __name__=='__main__':
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())
    #asyncio.run(main())




