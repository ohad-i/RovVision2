import numpy as np
import serial
import zmq
import sys
import asyncio
import time
import pickle
import struct
import os

sys.path.append('..')
sys.path.append('../utils')
import zmq_wrapper as utils
import zmq_topics
import detect_usb
import config

from select import select

import argparse

parser = argparse.ArgumentParser(description='UDP gate: zmq pub-sub to/from UDP', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-e', '--emulator', action='store_true', help='run without the real HW, currntly - connect any ttyUSB to computer')
args = parser.parse_args()


current_command=[0 for _ in range(8)] # 8 thrusters
keep_running=True

subs_socks=[]
subs_socks.append(utils.subscribe([zmq_topics.topic_thrusters_comand],zmq_topics.topic_thrusters_comand_port))
subs_socks.append(utils.subscribe([zmq_topics.topic_check_thrusters_comand],zmq_topics.topic_check_thrusters_comand_port))

if not args.emulator:
    ser = serial.Serial(detect_usb.devmap['ESC_USB'], 115200)
else:
    ser = serial.Serial('/dev/ttyUSB0', 115200)

rov_type = int(os.environ.get('ROV_TYPE','1'))
if rov_type == 4:
    pub_depth = utils.publisher(zmq_topics.topic_depth_port)
    pub_volt = utils.publisher(zmq_topics.topic_volt_port)
    pub_motors = utils.publisher(zmq_topics.topic_motors_output_port)
    
    subs_socks.append(
                utils.subscribe([zmq_topics.topic_lights],
                         zmq_topics.topic_controller_port))

    subs_socks.append(
                utils.subscribe([zmq_topics.topic_focus],
                         zmq_topics.topic_controller_port))
             
    OP_MOTORS = 0x01
    OP_LEDS = 0x02
    OP_CAMSERVO = 0x03

    serialMotorsMsgPack = '<BBhhhhhhhh'
    serialLedsMsgPack = '<BBh'
    serialCamServoMsgPack = '<BBh'

    ## 0-3 -> lower thrusters 4-7 -> upper thrusters                             
    motorDirConf = [1, 1, 1, 1, -1, -1, 1, 1]
    maxPWM = 400 # 400

    marker = 145

def setCmdToPWM(curCmd):
    # rov_type -> 4
    retVals = np.int16(np.array(curCmd)*maxPWM*np.array(motorDirConf))
    #print(retVals)
    return retVals




def motor_cmnd_to_DShot(cmnds):
    dshot_msgs = [0]*len(cmnds)
    for idx, cmd in enumerate(cmnds):
        zero_val = 48
        if np.sign(cmd) >= 0.001:
            zero_val = 1048
        cmd_dshot = int(zero_val + min(max(round(abs(cmd)*999), 0), 999)) << 1
        csum = (cmd_dshot ^ (cmd_dshot >> 4) ^ (cmd_dshot >> 8)) & 0xf
        dshot_msgs[idx] = cmd_dshot << 4 | csum

    return dshot_msgs


def dshotmsg_to_serialbuffer(dshot_msg_l):
    serial_buff = [0]*17
    serial_buff[0] = 145    #start and code nibbles
    binary_message_list = [[0]*16 for i in range(len(dshot_msg_l))]
    for msg_indx, msg in enumerate(dshot_msg_l):
        for bit_indx, bit in enumerate(bin(msg)[2:][::-1]):
            binary_message_list[msg_indx][15 - bit_indx] = int(bit)
    frame_list = list(np.array(binary_message_list).transpose())
    for buff_indx in range(16):
        frame_byte = 0
        for bit in frame_list[buff_indx]:
            frame_byte = (frame_byte << 1) | bit
        serial_buff[buff_indx + 1] = frame_byte

    return serial_buff


async def send_serial_command_50hz():
    while keep_running:
        await asyncio.sleep(1/50.0)

        rov_type = int(os.environ.get('ROV_TYPE','1'))
        # Need to convert comands to list of -1 -> 1?
        m = [0]*8
        c=current_command
        if rov_type == 1:
            m[0]=c[5]
            m[1]=c[4]
            m[2]=-c[6]
            m[3]=-c[7]
            m[4]=-c[1]
            m[5]=-c[0]
            m[6]=-c[2]
            m[7]=-c[3]
        elif rov_type == 2:
            m[0]=c[6]
            m[1]=c[7]
            m[2]=-c[5]
            m[3]=-c[4]
            m[4]=c[2]
            m[5]=-c[3]
            m[6]=c[1]
            m[7]=-c[0]

        m=np.clip(m,-config.thruster_limit,config.thruster_limit)
        dshot_frames = motor_cmnd_to_DShot(m)
        s_buff_64 = dshotmsg_to_serialbuffer(dshot_frames)
        ser.write(s_buff_64)
        #serial.write([struct.pack('>B', byte) for byte in s_buff_64])


### todo: add process to publish vector nav data???


async def recv_and_process():
    global current_command
    while keep_running:
        socks=zmq.select(subs_socks,[],[],0.000)[0]
        for sock in socks:
            ret=sock.recv_multipart()
            if ret[0]==zmq_topics.topic_thrusters_comand:
                _,current_command=pickle.loads(ret[1])
        await asyncio.sleep(0.001)
        #print('-1-',time.time())

async def main():
    await asyncio.gather(
            recv_and_process(),
            send_serial_command_50hz(),
            )



def mainHwGate():
    prevDepths=[]
    filterLen = 100

    espDataTic = time.time()
    espMsgCnt = 0.0

    if os.path.exists('./focusState.bin'):
         with open('./focusState.bin', 'r') as fid:
             pwm = int(fid.read(4))

             print('reset focus to:', pwm)
             msgBuf = struct.pack(serialCamServoMsgPack, marker, OP_CAMSERVO, pwm )
             ser.write(msgBuf)
             ser.flush() 
    
    minMotFps = 999999
    maxMotFps = -1
    
    ignoreController = False
    
    while True:
        time.sleep(0.0001)
        socks = zmq.select(subs_socks, [], [], 0.001)[0]
        for sock in socks:
            ret=sock.recv_multipart()
            topic,data=ret[0],pickle.loads(ret[1])
            if topic == zmq_topics.topic_lights:
                pwm = int((data) - 2)*200
                print('got lights command',data, pwm)
                msgBuf = struct.pack(serialLedsMsgPack, marker, OP_LEDS, max(-400, min(400, pwm)) )
                ser.write(msgBuf)
                ser.flush()
            if topic == zmq_topics.topic_focus:
                pwm = int(data)
                print('got focus command', pwm)
                msgBuf = struct.pack(serialCamServoMsgPack, marker, OP_CAMSERVO, pwm )
                with open('./focusState.bin', 'w') as fid:
                    fid.write(str(pwm))
                ser.write(msgBuf)
                ser.flush()
     
    
            if topic == zmq_topics.topic_thrusters_comand and not ignoreController:
                _, current_command = pickle.loads(ret[1])
                c = current_command
                if rov_type == 4:
                    m = [0]*8
    
                    m[0]=c[5] # c[6]
                    m[1]=c[4] #c[7]
                    m[2]=c[6] #-c[5]
                    m[3]=c[7] #!!!c[5]!!!#-c[4]
                    m[4]=c[1]  #c[2]
                    m[5]=-c[0] #-c[3]
                    m[6]=-c[3]  #c[1]
                    m[7]=c[2] #-c[0]
                    '''
                    m[6]=c[2]  #c[1]
                    m[7]=-c[3] #-c[0]
                    '''
                    '''
                    m[0]=c[5]
                    m[1]=c[4]
                    m[2]=-c[6]
                    m[3]=-c[7]
                    m[4]=-c[1]
                    m[5]=-c[0]
                    m[6]=-c[2]
                    m[7]=-c[3]
                    '''
                motorsPwm = setCmdToPWM(m)
                #print('---from controller.py--->',current_command)
                #print('---to esp32 --->',motorsPwm)
                
                pub_motors.send_multipart( [zmq_topics.topic_motors_output, pickle.dumps( {'ts':time.time(), 'motors':motorsPwm} )])
                
                msgBuf = struct.pack(serialMotorsMsgPack, marker, OP_MOTORS, *motorsPwm)
                ser.write(msgBuf)
                ser.flush()
                #print(time.time(), '---motors regular cmd to esp32 --->',motorsPwm)
                
            if topic == zmq_topics.topic_check_thrusters_comand:
                _, current_command = pickle.loads(ret[1])
                m = current_command
                tmp = m[6]
                m[6] = m[7]
                m[7] = tmp
                
                motorsPwm = setCmdToPWM(m)

                if any(motorsPwm): 
                    ignoreController = True
                else:
                    ignoreController = False

                print('---motors check cmd to esp32 --->',motorsPwm)
                
                msgBuf = struct.pack(serialMotorsMsgPack, marker, OP_MOTORS, *motorsPwm)
                ser.write(msgBuf)
                ser.flush()
                
                pub_motors.send_multipart( [zmq_topics.topic_motors_output, pickle.dumps( {'ts':time.time(), 'motors':motorsPwm} )])
                
                
    
        ret = select([ser],[],[],0.001)[0]
        if len(ret) > 0:
            chck = ser.read(1)
            if ord(chck) == 0xac:
               chck = ser.read(1)
               if ord(chck) == 0xad:
                   espData = ser.read(8)
                   baro_m = espData[:2] #ser.read(2)
                   temp_c = espData[2:4] #eser.read(2)
                   voltage = espData[4:6] #ser.read(2)
                   motorFps = espData[6:] #ser.read(2)
                   #print('--1->', baro_m)
                   #print('--2->', temp_c)

                   tic = time.time()
                   bar_D = struct.unpack('h',baro_m)[0]/200
                   temp_D = struct.unpack('h',temp_c)[0]/200
                   volt_D = struct.unpack('h',voltage)[0]/200
                   motFps = struct.unpack('h',motorFps)[0]/200
                   if motFps > maxMotFps:
                       maxMotFps = motFps
                   elif motFps < minMotFps:
                       minMotFps = motFps
                         
                   #current_D = struct.unpack('h',current)[0]/200
                   #print('baro --3->', bar_D)
                   #print('temp --4->', temp_D)
                   
                   pub_depth.send_multipart( [zmq_topics.topic_depth,pickle.dumps( {'ts':tic, 'depth':bar_D} )])
                   
                   pub_volt.send_multipart(  [zmq_topics.topic_volt, pickle.dumps( ( {'ts':tic, 'V':volt_D, 'I':-1.0}) )] )
                   espMsgCnt += 1
                   if time.time() - espDataTic >= 5:
                       espFps = espMsgCnt/(time.time() - espDataTic)
                       print('%d esp data mps: %0.2f'%(espDataTic, espFps))
                       print('baro --3->', bar_D)
                       print('temp --4->', temp_D)
                       print('voltage --5->', volt_D)
                       print('motor fps --6-> min %0.2f max %0.2f '%(minMotFps, maxMotFps) )
                       minMotFps = 9999999
                       maxMotFps = -1
                       #print('current --6->', current_D)
                       espMsgCnt = 0.0
                       espDataTic = time.time()

    
    

if __name__=='__main__':
    if rov_type != 4:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(main())
        #asyncio.run(main())
    elif rov_type == 4:
        mainHwGate()
