import os
import pickle

if __name__=='__main__':
    dmap = {}

    rov_type = int(os.environ.get('ROV_TYPE','1'))
    for dev in ['/dev/ttyUSB%d'%i for i in [0,1,2,3]]:
        cmd = 'udevadm info '+dev
        lines=os.popen(cmd).readlines()
        line=os.popen(cmd).read()
        #import ipdb; ipdb.set_trace()

        if rov_type==1:
            if '1-7' in line:
                dmap['SONAR_USB']=dev
            if '1-5' in line:
                dmap['ESC_USB']=dev
            if '1-3' in line:
                dmap['VNAV_USB']=dev
            if '1-1' in line:
                dmap['PERI_USB']=dev
        
        if rov_type==2:
            if '1-5.4' in line:
                dmap['SONAR_USB']=dev
            if '1-5.1' in line:
                dmap['PERI_USB']=dev
            if '1-5.2' in line:
                dmap['VNAV_USB']=dev
            if '1-5.3' in line:
                dmap['ESC_USB']=dev

        if rov_type==3:
            if '1-5.4' in line:
                dmap['SONAR_USB']=dev
            if '1-5.1' in line:
                dmap['PERI_USB']=dev
            if '1-5.2' in line:
                dmap['VNAV_USB']=dev
            if '1-5.3' in line:
                dmap['ESC_USB']=dev

        if rov_type==4:
            if 'FTDI_TTL232R_FTA1YCS4' in line:
                dmap['SONAR_USB']=dev
            if 'FTDI_USB-RS232_Cable_FTWV7X4Y' in line:
                dmap['VNAV_USB']=dev
            if 'FTDI_FT232R_USB_UART_AI0484HC' in line:
                dmap['ESC_USB']=dev #esp32
            


    with open('/tmp/devusbmap.pkl','wb') as fp:
        #print(dmap)
        pickle.dump(dmap,fp)
        print('device map = ',dmap)

else:
    if not os.path.isfile('/tmp/devusbmap.pkl'):
        print('Error cannot find /tmp/devusbmap.pkl please run detect_usb.py')
        devmap = None
    else:
        devmap = pickle.load(open('/tmp/devusbmap.pkl','rb'))

