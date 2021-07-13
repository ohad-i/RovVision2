#torun 
# conda activate 3.6 
#from vnpy import *
print('done import')
import time,sys
import os,zmq
sys.path.append('..')
sys.path.append('../utils')
import zmq_wrapper as utils
print('done import 2')
import zmq_topics
import asyncio,pickle
import serial

from select import select

pub_imu = utils.publisher(zmq_topics.topic_imu_port)
##### vnav commands (setup)
#doc in https://www.vectornav.com/docs/default-source/documentation/vn-100-documentation/vn-100-user-manual-(um001).pdf?sfvrsn=b49fe6b9_32
vn_pause = b'$VNASY,0*XX'
vn_resume = b'$VNASY,1*XX'
vn_setoutput_quaternion =b'$VNWRG,06,2*XX'

vn_mag_disturbance_1 = b'$VNKMD,1,1*XX'
vn_mag_disturbance_0 = b'$VNKMD,0,0*XX'
vn_acc_disturbance_1 = b'$VNKAD,1,1*XX'
vn_acc_disturbance_0 = b'$VNKAD,0,0*XX'

#Yaw, Pitch, Roll, Magnetic, Acceleration, and Angular Rate Measurements
#header VNYMR
vn_setoutput=b'$VNWRG,06,14*XX' 
##### 
## set vnav frequency
## optional values: 1,2,4,5,10,20,25,40,50,100,200(Hz)
vn_setfreq20hz=b'$VNWRG,07,20*XX'
vn_setfreq100hz=b'$VNWRG,07,100*XX'


####
## to set permanent baudrate
## manually set commnads using the following:
## after set new baud rate...
## open screen /dev/ttyUSB0 newBaudRate
## you will see data running, do the folowing, no feedback...
## on screen copy-paste the command:
## $VNCMD*XX  "enter"
## type: system save "enter"
####


### clibration
vn_heading_mode=b'$VNWRG,35, 1, 0, 1, 1*XX'

vn_reset_hsi=b'$VNWRG,44,2,3,5*XX'
vn_hsi_on=b'$VNWRG,44,1,3,5*XX'
vn_hsi_off=b'$VNWRG,44,0,3,5*XX'
vn_read_hsi=b'$VNRRG,47*XX'
vn_read_saved_mag=b'$VNRRG,23*XX'
vn_clear_mag=b'$VNWRG,23,1,0,0,0,1,0,0,0,1,0,0,0*76'
vni_reset_unit=b'$VNRST*4D'


def save_reg23_to_disk(ser):
    print('saving reg 23 to disk')
    regline=write(ser,vn_read_saved_mag)
    open('mag_calib.txt','wb').write(regline)

def load_reg23_from_file(ser):
    print('reading reg 23 from file')
    line=open('mag_calib.txt','rb').read()
    part = b'$VNWRG,23,'+line.strip().split(b',',2)[2].split(b'*')[0]+b'*XX'
    write(ser,part)

def write(ser,cmd, timeout=0.5):

    ret = select([],[ser],[], timeout)
    if len(ret[1]) > 0:
        ser.write(cmd+b'\n')
        ser.flush()
    
    ret = select([ser],[],[], timeout)
    ln = 'None'
    if len(ret[0]) > 0:
        #while ser.inWaiting():
        #    ln=ser.readline()
        ln=ser.readline()
        print('>',ln)
    return ln


def calibrate_mag(ser):
    print('start mag calibration')
    write(ser,vn_pause)
    write(ser,vn_hsi_off)
    write(ser,vn_reset_hsi)
    input('hit enter to start calibration')
    write(ser,vn_hsi_on)
    input('rotate rov and hit enter when done')
    write(ser,vn_hsi_off)
    print('read hsi:')
    line=write(ser,vn_read_hsi)
    #save result to register 23
    part = b'$VNWRG,23,'+line.strip().split(b',',2)[2].split(b'*')[0]+b'*XX'
    print('writing',part)
    write(ser,part)
    save_reg23_to_disk(ser)
    input('hit enter to resume output')
    write(ser,vn_resume)

    

def init_serial(dev=None):
    if dev is None:
        #import detect_usb
        dev="/dev/ttyUSB0" #detect_usb.devmap['VNAV_USB']

    #ser = serial.Serial(dev,115200)
    #write(ser,vn_set_baud, 1)
    #return None
    
    ser = serial.Serial(dev, 921600)
    
    if False:#os.path.isfile('mag_calib.txt'):
        load_reg23_from_file(ser)
    #set freq and output

    write(ser,vn_pause)
    write(ser,vn_setoutput)
    print('---')
    #write(ser,vn_setfreq20hz)
    write(ser,vn_setfreq100hz)
    print('---')
    write(ser,vn_hsi_off)
    write(ser, vn_heading_mode)
    write(ser,vn_acc_disturbance_0)
    write(ser,vn_mag_disturbance_0)
    #set frequency
    
    write(ser,vn_resume, 4)
    return ser

def parse_line(line):
    if line.startswith(b'$'):
        parts=line.strip().split(b'*')[0].split(b',')
        if parts[0]==b'$VNYMR':
            y,p,r,mx,my,mz,ax,ay,az,gx,gy,gz = map(float,parts[1:])
        ret={}
        #ret['ypr'] = (y,p,r)
        ret['yaw'],ret['pitch'],ret['roll']=y,p,r
        ret['rates'] = (gx,gy,gz)
        ret['mag'] = (mx,my,mz)
        ret['acc'] = (ax,ay,az)
        return ret


def recv_and_process2(ser):
    cnt=0
    fpsCnt = 0.0
    fpsTic = time.time()
    
    while 1:
        ret = select([ser],[],[], 0.005)
        if len(ret[0]) > 0:
            l=ser.readline()
            try:
                imu=parse_line(l)
                tic=time.time()
                imu['ts']=tic
            except:
                print('fail to parse line')
                imu=None
            if imu is not None:
                fpsCnt += 1
                if time.time()-fpsTic > 3:
                    fps = fpsCnt/(time.time()-fpsTic)
                    print('---> imu rate: %.2fHz'%fps)
                    fpsCnt = 0.0
                    fpsTic = time.time()
                if cnt%200==0:
                    print('dsim Y{:4.2f} P{:4.2f} R{:4.2f}'.format(imu['yaw'],imu['pitch'],imu['roll'])
                                +' X{:4.2f} Y{:4.2f} Z{:4.2f}'.format(*imu['rates']))
                pub_imu.send_multipart([zmq_topics.topic_imu,pickle.dumps(imu)])
                cnt+=1


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--calib_mag", help="run mag calibration", action='store_true')
    parser.add_argument("--reset", help="run reset", action='store_true')
    parser.add_argument("--read_reg23", help="read reg 23mag calibration", action='store_true')
    parser.add_argument("--dev", help="device", default=None)
    parser.add_argument("--setBaud", help="New vector nav setup, set baud from 115200 to 926100", action='store_true', default=None)
   

    args = parser.parse_args()
    
    if args.setBaud:
        print('changing baud from 115 to 926... may stuck, ctrl+c after a while and do permanently register flush procedure...')
        
        vn_set_baud = b'$VNWRG,05,921600*XX' 
        ser = serial.Serial(dev, 115200)
        write(ser, vn_set_baud, 1)

    ser = init_serial(args.dev)
    if args.calib_mag:
        calibrate_mag(ser)
    elif args.reset:
        write(ser,vn_reset_unit)
    elif args.read_reg23:
        print('reg 23 mag calibration is:')
        write(ser,vn_pause)
        write(ser,vn_read_saved_mag)
        write(ser,vn_resume)
    else:
        recv_and_process2(ser)
    #testline=b'$VNRRG,27,+006.380,+000.023,-001.953,+1.0640,-0.2531,+3.0614,+00.005,+00.344,-09.758,-0.001222,-0.000450,-0.001218*4F'
    #print(parse_line(testline))
