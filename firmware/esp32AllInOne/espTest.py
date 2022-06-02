import serial
import time
import struct
import optparse

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

serialMotorsMsgPack = '<BBhhhhhhhh'
serialLedsMsgPack = '<BBh'

try:
    if opts.port == "noDev":
        import sys
        sys.path.append("../../utils")
        import detect_usb
        ser = serial.Serial(detect_usb.devmap['ESC_USB'], 115200)
    else:
        ser = serial.Serial(opts.port, 115200)
    
    msgBuf = None
    
    if opts.motorTest:
        motorsVals = [0]*8
        pwm = int(opts.motorSpeed) - 1500
        motorsVals[int(opts.motorId)-1] = max(-400, min(400, pwm ))
        print(motorsVals)
        msgBuf = struct.pack(serialMotorsMsgPack, 145, opMotors, *motorsVals ) 
        print("perform motor test on motor %d to speed %d"%(int(opts.motorId), int(opts.motorSpeed)))
        
        ser.write(msgBuf)
        ser.flush()
        
        time.sleep(0.5)
        motorsVals = [0]*8
        #motorsVals[int(opts.motorId)-1] = max(-400, min(400, pwm ))
        print(motorsVals)
        msgBuf = struct.pack(serialMotorsMsgPack, 145, opMotors, *motorsVals )
        print("perform motor test on motor %d to speed %d"%(int(opts.motorId), int(opts.motorSpeed)))
        ser.write(msgBuf)
        ser.flush()
        time.sleep(1)
        
        
    
    if opts.ledTest:
        if pwm != 0:
            pwm = min(max(1100, pwm), 1900)
            pwm = int(int(opts.ledPwm)) - 1500
        
            msgBuf = struct.pack(serialLedsMsgPack, 145, opLeds, max(-400, min(400, pwm)) ) 
            print("perform led test, pwm: %d"%(int(opts.ledPwm) ))
            
            ser.write(msgBuf)
            ser.flush()
            time.sleep(1)
        else:
            for pWm in range(1100,1900,50): 
                pWm = int(pWm - 1500)
                msgBuf = struct.pack(serialLedsMsgPack, 145, opLeds, max(-400, min(400, pWm)) ) 
                
                print("perform leds test, pwm: %d"%(int(pWm) ))
                ser.write(msgBuf)
                ser.flush()
                time.sleep(1)
            
    
    if opts.camServo:
        for pwm in range(850,2250,50): #700<->220
            msgBuf = struct.pack(serialLedsMsgPack, 145, opCamServo, pwm ) 
            
            print("perform servo test, pwm: %d"%(int(pwm) ))
            ser.write(msgBuf)
            ser.flush()
            time.sleep(1)
    
    


    if msgBuf is None: # default test
        motorsVals = [0]*8
        for i in range(0,8,2):
            motorsVals[i] = 50
            motorsVals[i+1] = -50
            print(motorsVals)
            msgBuf = struct.pack(serialMotorsMsgPack, 145, opMotors, *motorsVals ) 
            ser.write(msgBuf)
            ser.flush()
            time.sleep(0.2) 
            motorsVals = [0]*8
    
        motorsVals = [0]*8
        print(motorsVals)
        msgBuf = struct.pack(serialMotorsMsgPack, 145, opMotors, *motorsVals )
        ser.write(msgBuf)
        ser.flush()
        time.sleep(0.2) 
except:
    print("test error - turn motors off...")
    motorsVals = [0]*8
    print(motorsVals)
    msgBuf = struct.pack(serialMotorsMsgPack, 145, opMotors, *motorsVals )
    ser.write(msgBuf)
    ser.flush()
    time.sleep(0.2)
