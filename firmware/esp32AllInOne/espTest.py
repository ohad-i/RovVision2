import numpy as np
import time
import struct
import serial


def setSerialMessage(dshot_msg_l):
    serial_buff = [0]*17
    serial_buff[0] = 145    #start and code nibbles
    
    return serial_buff

#ser = serial.Serial('/dev/ttyUSB0', 115200)
ser = serial.Serial('COM11', 115200)

current_command = [0, 0, 0, 0, 0, 0, 0, 0]
s_buff_64 = setSerialMessage(dshot_frames)
ser.write(s_buff_64)
time.sleep(5)

