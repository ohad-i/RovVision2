import serial
import time
import struct
import optparse
from select import select
import sys

import asyncio


'''
#example: python espMTtest.py --port=/dev/ttyUSB1 --motorTest --motorId=1 --motorSpeed=1400 --ledTest --camServo
'''

parser = optparse.OptionParser("esp32Test")
parser.add_option("--port", default='/dev/ttyUSB1', help='tty port (if noDev -> use auto detect port), default: /dev/ttyUSB1')
parser.add_option("--motorTest", default=False, action='store_true', help='test motors')
parser.add_option("--motorId", default="1", help='motor to run 1-8')
parser.add_option("--motorSpeed", default="0", help='1100 to 1900')
parser.add_option("--ledTest", default=False, action='store_true',  help='commit led Test')
parser.add_option("--ledPwm", default="0", help='1100 to 1900')
parser.add_option("--camServo", default=False, action='store_true', help='do focus servo test')

opts, args = parser.parse_args()

opMotors = 0x01
opLeds = 0x02
opCamServo = 0x03
opGeneral = 0x04

syncWord = 0x91


serialMotorsMsgPack = '<BBhhhhhhhh'
serialGenMsgPack = '<BBhhhhhhhhhh'
serialLedsMsgPack = '<BBh'

generalMsg = [0]*10
ledIdx = 9
focusIdx = 8

if opts.port == "noDev":
    import sys
    sys.path.append("../../utils")
    import detect_usb
    ser = serial.Serial(detect_usb.devmap['ESC_USB'], 115200)
else:
    ser = serial.Serial(opts.port, 115200)

async def send_serial_command_50hz():
    global generalMsg
    genSent = 0
    sentTic = time.time()

    generalMsg[ledIdx] = -1 # 0->800 
    generalMsg[focusIdx] = -1 # 0->800
    
    hz = 100.0 
    waitVal = 1/hz
    while True:
        await asyncio.sleep(waitVal)
        wTic = time.time()
        #print('--->', generalMsg) 
        msgBuf = struct.pack(serialGenMsgPack, syncWord, opGeneral, *generalMsg )

        ser.write(msgBuf)
        ser.flush()

        generalMsg[ledIdx] = -1 # 0->800 
        generalMsg[focusIdx] = -1 # 0->800


        if time.time() - sentTic >= 3:
           mps = genSent/(time.time() - sentTic)
           print('general command sent MSP: %0.2f, waitVal: %0.5f'%(mps, waitVal) )
           genSent = 0.0
           sentTic = time.time()
        

        # op-time compensation 
        dt = time.time() - wTic
        waitVal = (1/hz)-1.2*(dt)
        genSent += 1


async def readSerialData():
    
    espDataTic = time.time()
    espMsgCnt = 0
    minMotFps = 9999999
    maxMotFps = -1
    
    bar_D = -1
    volt_D= -1
    temp_D = -1
    while True:
        ret = select([ser],[],[],0.001)[0]
        if len(ret) > 0:
            chck = ser.read(1)
            if ord(chck) == 0xac:
               chck = ser.read(1)
               if ord(chck) == 0xad:
                   espMsgCnt += 1
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
        await asyncio.sleep(0.001)
        if time.time() - espDataTic >= 10:

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

async def testProc():
    global generalMsg
    while True:
        if opts.motorTest:
            motorsVals = [0]*8
            pwm = int(opts.motorSpeed) - 1500
            motorsVals[int(opts.motorId)-1] = max(-400, min(400, pwm ))
            print('--->', motorsVals)
            generalMsg[int(opts.motorId)-1] = motorsVals[int(opts.motorId)-1]
            
            print("perform motor test on motor %d to speed %d"%(int(opts.motorId), int(opts.motorSpeed)))
            await asyncio.sleep(1)
            generalMsg[int(opts.motorId)-1] = max(-400, min(400, 0 ))
            
            print("end motor test on motor %d to speed %d"%(int(opts.motorId), int(opts.motorSpeed)))
            await asyncio.sleep(0.5)
        if opts.ledTest:
            pwm = int(opts.ledPwm)
            if pwm != 0:
                pwm = min(max(1100, pwm), 1900)
                pwm = int(int(pwm)) - 1100

                generalMsg[ledIdx] = pwm # 0->800 
                print("perform led test, pwm: %d"%(int(opts.ledPwm) ))
                await asyncio.sleep(1)

            else:
                for pWm in range(1100,1950,50):
                    print("perform led test, pwm: %d"%(pWm) )
                    pWm = int(int(pWm)) - 1100
                    generalMsg[ledIdx] = pWm # 0->800 
                    await asyncio.sleep(1)
            generalMsg[ledIdx] = 0 # 0->800 
            print("end led test." )
        if opts.camServo:
            for pwm in range(800,2250,50): #700<->220
                generalMsg[focusIdx] = pwm-800 # 0->800 
                print("perform servo test, pwm: %d"%(pwm) )
                await asyncio.sleep(0.3)
            generalMsg[focusIdx] = 0 # 0->800 
            print("end servo test." )
       

        print("esp test ened... waiting for 1 min. check messages rates...")
        await asyncio.sleep(60)
    sys.exit(0)
        


async def main():
    await asyncio.gather(readSerialData(),
                         send_serial_command_50hz(),
                         testProc() )





if __name__=="__main__":

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())

    
 
