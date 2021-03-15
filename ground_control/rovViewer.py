#!/usr/bin/python3
# need fping install - sudo apt install fping
# install ssh support - Exscript @ https://exscript.readthedocs.io/en/latest/install.html
# install matplotlib -  sudo apt-get install python3-matplotlib
# install tix - sudo apt-get install tix-dev


from tkinter import *
#from tkinter.tix import *
from PIL import Image, ImageTk
import io
import time
import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import os
import sys
import socket
import pickle

sys.path.append('../onboard')
sys.path.append('../utils')
sys.path.append('..')

import config
import zmq_topics
import zmq_wrapper as utils
from annotations import draw_mono
import numpy as np
import cv2
from select import select
import zmq
import image_enc_dec


#### matplotlib add
import matplotlib.pyplot as plt
####

'''
tm = time.gmtime()
filename = "logs/gui_{}_{}_{}__{}_{}_{}.log".format(
    tm.tm_year, tm.tm_mon, tm.tm_mday,
    tm.tm_hour, tm.tm_min, tm.tm_sec)
log_file = open(filename, "a")
'''
class CycArr():
    def __init__(self,size=20000):
        self.buf=[]
        self.size=size

    def add(self,arr):
        self.buf.append(arr)
        if len(self.buf)>self.size:
            self.buf.pop(0)

    def get_data(self,labels):
        data = np.zeros((len(self.buf),len(labels)))
        for i,d in enumerate(self.buf):
            for j,l in enumerate(labels):
                if l in d:
                    data[i][j]=d[l]
                else:
                    data[i][j]=0
        return data

    def get_vec(self):
        return np.array([d for _,d in self.buf])

    def __len__(self):
        return len(self.buf)

    def reset(self):
        self.buf=[]


from threading import Thread
class rovDataHandler(Thread):
    def __init__(self, rovViewer):
        super().__init__()
        self.subs_socks=[]
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_thrusters_comand,zmq_topics.topic_system_state],zmq_topics.topic_controller_port))
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_button, zmq_topics.topic_hat], zmq_topics.topic_joy_port))
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_imu], zmq_topics.topic_imu_port))
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_depth], zmq_topics.topic_depth_port))
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_depth_hold_pid], zmq_topics.topic_depth_hold_port))
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_sonar], zmq_topics.topic_sonar_port))
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_stereo_camera_ts], zmq_topics.topic_camera_port)) #for sync perposes
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_tracker], zmq_topics.topic_tracker_port))
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_volt], zmq_topics.topic_volt_port))
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_hw_stats], zmq_topics.topic_hw_stats_port))
        
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_pos_hold_pid_fmt%i for i in range(3)], zmq_topics.topic_pos_hold_port))
        self.subs_socks.append(utils.subscribe([zmq_topics.topic_att_hold_yaw_pid,
                                           zmq_topics.topic_att_hold_pitch_pid,
                                           zmq_topics.topic_att_hold_roll_pid], zmq_topics.topic_att_hold_port))
        
        
        self.imgSock =  socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
        self.imgSock.bind(('', config.udpPort))
        
        self.image = None 
        
        self.pubData = True
        self.socket_pub = None
        if self.pubData:
            self.socket_pub = utils.publisher(zmq_topics.topic_local_route_port,'0.0.0.0')
        self.rovViewer = rovViewer
        self.keepRunning = True
        self.telemtry = {}
        
        
    def getNewImage(self):
        ret = None
        if self.image is not None:
            ret = np.copy(self.image)
            self.image = None
        return ret
    
    def getTelemtry(self):
        return self.telemtry.copy()
    
    def run(self):
        self.main()

    def kill(self):
        self.keepRunning = False
        time.sleep(0.1)
    
    
    def main(self):
        
        sx,sy=config.cam_res_rgbx,config.cam_res_rgby
        
        #main_camera_fd=None
        message_dict={}
        rcv_cnt=0
        images = [None, None]
        bmargx,bmargy=config.viewer_blacks
        print('rovDataHandler running...')
        while self.keepRunning:
            if len(select([self.imgSock],[],[],0.003)[0]) > 0:
                data, addr = self.imgSock.recvfrom(1024*64)
                img = cv2.imdecode(pickle.loads(data), 1)
                images = [img]
                rcv_cnt+=1
            #if all(images):
            while True:

                socks = zmq.select(self.subs_socks,[],[],0.005)[0]
                if len(socks)==0: #flush msg buffer
                    break
                for sock in socks:
                    ret = sock.recv_multipart()
                    topic, data = ret
                    data = pickle.loads(ret[1])
                    message_dict[topic]=data
                    
                    self.telemtry = message_dict.copy()                    
                    if self.pubData:
                        self.socket_pub.send_multipart([ret[0],ret[1]])
    
            showIm = None
            if images[0] is not None:
                images[0] = cv2.cvtColor(images[0], cv2.COLOR_BGR2RGB)
                fmt_cnt_l=image_enc_dec.decode(images[0])
                draw_mono(images[0],message_dict,fmt_cnt_l)
                
                showIm = images[0]
            
            if showIm is not None:
                #self.rovViewer.update_image(showIm)
                self.image = showIm
                if 0:
                    cv2.imshow('3dviewer', showIm)
                    cv2.waitKey(10)
                
        print('bye bye!')


### message mapping from joystick to gui
armDisarmMsg = [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]

recordMsg = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]
attHoldMsg = [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0] 
depthHoldMsg = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]

lightDownMsg = [0, 0, 0, 0, 0, 0, 0.0, 1.0]
lightUpMsg = [0, 0, 0, 0, 0, 0, 0.0, -1.0]
neutralHatMsg = [0, 0, 0, 0, 0, 0, 0.0, 0]
focusNearMsg = [0, 0, 0, 0, 0, 0, -1, 0]
focusFarMsg = [0, 0, 0, 0, 0, 0, 1, 0]

attHoldMsg   = [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
depthHoldMsg = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]

# this class is the base of our GUI
class rovViewerWindow(Frame):
    def __init__(self, parent=None, **kw):
        super().__init__(**kw)
        self.parent = parent

        # init attributes
        
        self.checkInertial = IntVar()
        self.checkInertial.set(1)
        
        self.checkDepthControl = IntVar()
        self.checkDepthControl.set(1)
        self.checkPitchControl = IntVar()
        self.checkPitchControl.set(1)
        self.checkRollControl = IntVar()
        self.checkRollControl.set(1)
        self.checkYawControl = IntVar()
        self.checkYawControl.set(1)
        self.checkRecorder = IntVar()
        self.checkRecorder.set(1)
        
        self.ping_window = None
        self.update_ping_window = False
        self.resize_called = True
        
        self.myStyle = {'fg': 'black', 'bg': 'LightSteelBlue', 'buttonBg': 'gray90', 'buttonFg': 'black',
                     'activeDisplayButtonFg': 'gray40', 'activeDisplayButtonBg': 'pink',
                     'buttonBgSoft': 'slategrey', 'buttonFgSoft': 'white', 'activeSoftButtonBg': 'gray50',
                     'buttonBgControl': 'green', 'buttonFgControl': 'ghostwhite', 'btnHighlight': 'pink',
                     'disabled_fg': 'gray26', 'select_bg': 'pink', 'activeButtonBg': 'gray70',
                     'activeControlButtonBg': 'gray50'}

        self.img = None
        self.last_pressed_button = 'disarm'
        
        self.TFont = ("Courier", 14)
        self.TextboxFont = ("Courier", 12)
        self.HeaderFont = ("Courier", 16, "underline")
        
        
        self.ROVHandler = rovDataHandler(self)
        self.ROVHandler.start()

        self.initX = 15
        self.initY = 660
        self.colWidth = 100
        self.colButtonWidth = 120
        self.rowHeight = 30
 
        # create widgets
        self.make_widgets()
        self.bind_widgets_events()
        self.maximize_with_title()
        self.set_style()
        
        self.updateGuiData()
        self.rovGuiCommandPublisher = utils.publisher(zmq_topics.topic_gui_port)
        self.armClicked = False
        self.recClicked = False
        self.attMessage = {'dDepth':0.0, 'dPitch': 0.0, 'dYaw':0.0}
        
        self.pidMsgs = {}
        self.updatePids()
        
        print(' display layer init done ')
        
    
    def quit(self):
        self.ROVHandler.kill()
        self.parent.quit()
    
        
    def maximize_with_title(self):
        self.parent.title("ROV viewer")
        w, h = self.parent.winfo_screenwidth(), self.parent.winfo_screenheight()
        self.parent.geometry("%dx%d+0+0" % (w - 20, h - 20))

    def set_style(self):
        #self.parent.geometry('1600x900+0+0')
        self.parent.configure(background=self.myStyle['bg'])

    def resize(self, event):
        self.resize_called = True

    def create_label(self, name, display_text, n_col, n_row, width, centered):
        if centered:
            lbl = Label(self.parent, text=display_text, width=width)
        else:
            lbl = Label(self.parent, text=display_text, anchor="w", width=width)
        lbl.grid(column=n_col, row=n_row)
        lbl.configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
        lbl.config(font=self.TFont)
        self.myStyle[name] = lbl

    def create_label_pair(self, name, display_text, n_col, n_row):
        first_name = "{}label".format(name)
        second_name = "{}text".format(name)
        self.myStyle[first_name] = Label(self.parent, text=display_text, anchor="w", width=15)
        self.myStyle[second_name] = Label(self.parent, text="n/a", width=18, anchor="w")
        self.myStyle[first_name].grid(column=n_col, row=n_row)
        self.myStyle[second_name].grid(column=n_col + 1, row=n_row)
        self.myStyle[first_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
        self.myStyle[second_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])

        self.myStyle[first_name].config(font=self.TFont)
        self.myStyle[second_name].config(font=self.TFont)

        #print('-->', display_text, n_col, n_row)
        self.myStyle[first_name].place(x=self.initX+(n_col-1)*self.colWidth, y=self.initY+(n_row-1)*self.rowHeight)
        self.myStyle[second_name].place(x=self.initX+(n_col)*self.colWidth, y=self.initY+(n_row-1)*self.rowHeight)


    def create_main_col_row_labels(self):
        for number in range(0, 10):
            lbl = Label(self.parent, text=" ", anchor="e", width=1)
            lbl.grid(column=number, row=0)
            lbl.configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
            lbl = Label(self.parent, text=" ", anchor="e", width=1)
            lbl.grid(column=0, row=number)
            lbl.configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])

    def create_single_label_header(self, name, display_text, n_col, n_row):
        first_name = "{}label1".format(name)
        self.myStyle[first_name] = Label(self.parent, text=display_text, anchor="w", width=1 + len(display_text))
        self.myStyle[first_name].grid(column=n_col, row=n_row, padx=5, pady=2)
        self.myStyle[first_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
        self.myStyle[first_name].config(font=self.HeaderFont)

    def create_label_header(self, name, display_text1, display_text2, display_text3, display_text4, display_text5,
                            n_col, n_row):
        first_name = "{}label1".format(name)
        second_name = "{}label2".format(name)
        third_name = "{}label3".format(name)
        fourth_name = "{}label4".format(name)
        fifth_name = "{}label5".format(name)

        self.myStyle[first_name] = Label(self.parent, text=display_text1, width=15) #, anchor="w")
        self.myStyle[second_name] = Label(self.parent, text=display_text2, width=10)
        self.myStyle[third_name] = Label(self.parent, text=display_text3, width=15)
        self.myStyle[fourth_name] = Label(self.parent, text=display_text4, width=15)
        self.myStyle[fifth_name] = Label(self.parent, text=display_text5, width=15)

        self.myStyle[first_name].grid(column=n_col, row=n_row)
        self.myStyle[second_name].grid(column=n_col + 1, row=n_row)
        self.myStyle[third_name].grid(column=n_col + 3, row=n_row)
        self.myStyle[fourth_name].grid(column=n_col + 5, row=n_row)
        self.myStyle[fifth_name].grid(column=n_col + 7, row=n_row)

        self.myStyle[first_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
        self.myStyle[second_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
        self.myStyle[third_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
        self.myStyle[fourth_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
        self.myStyle[fifth_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])

        self.myStyle[first_name].config(font=self.HeaderFont)
        self.myStyle[second_name].config(font=self.HeaderFont)
        self.myStyle[third_name].config(font=self.HeaderFont)
        self.myStyle[fourth_name].config(font=self.HeaderFont)
        self.myStyle[fifth_name].config(font=self.HeaderFont)
   
    
    def create_text_box(self, name, label_text, display_text, n_col, n_row, textbox_width, stickyness='NESW'):
        first_name = "{}_label".format(name)
        second_name = "{}_textbox".format(name)
        self.myStyle[first_name] = Label(self.parent, text=label_text, anchor="w") #, width=15)
        self.myStyle[first_name].grid(column=n_col, row=n_row)
        self.myStyle[first_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
        self.myStyle[first_name].config(font=self.TFont)

        self.myStyle[second_name] = Entry(self.parent, borderwidth=1, relief="sunken", width=textbox_width, selectbackground=self.myStyle['select_bg'])
        self.myStyle[second_name].config(font=self.TextboxFont)
        self.myStyle[second_name].grid(row=n_row, column=n_col + 1, padx=2, pady=2, sticky=stickyness)

        self.myStyle[second_name].insert(END, display_text)
        #print('-->', label_text, n_col, n_row)
        self.myStyle[first_name].place(x=self.initX+(n_col-1)*self.colWidth, y=self.initY+(n_row-1)*self.rowHeight)
        self.myStyle[second_name].place(x=self.initX+(n_col)*self.colWidth, y=self.initY+(n_row-1)*self.rowHeight)

    def bind_widgets_events(self):
        
        self.myStyle['disp_image'].bind("<Button-1>", self.image_clicked)
        self.myStyle['disp_image'].bind("<Button-2>", self.image_right_clicked)
        self.myStyle['disp_image'].bind("<Button-3>", self.image_right_clicked)
        
        self.parent.bind("<Left>", self.left_click_func)
        self.parent.bind("<Right>", self.right_click_func)
        self.parent.bind("<Up>", self.up_click_func)
        self.parent.bind("<Down>", self.down_click_func)
        self.parent.bind("<Prior>", self.page_up_click_func)
        self.parent.bind("<Next>", self.page_down_click_func)
        self.parent.bind("<Key-7>", self.turn_left_click_func)
        self.parent.bind("<Key-9>", self.turn_right_click_func)

        self.parent.bind("<Key-a>", self.left_click_func)
        self.parent.bind("<Key-d>", self.right_click_func)
        self.parent.bind("<Key-w>", self.up_click_func)
        self.parent.bind("<Key-s>", self.down_click_func)
        self.parent.bind("<Key-r>", self.page_up_click_func)
        self.parent.bind("<Key-f>", self.page_down_click_func)
        self.parent.bind("<Key-q>", self.turn_left_click_func)
        self.parent.bind("<Key-e>", self.turn_right_click_func)

        
    def page_up_click_func(self, event):
        self.go_up()

    def page_down_click_func(self, event):
        self.go_down()

    def turn_left_click_func(self, event):
        self.turn_left()

    def turn_right_click_func(self, event):
        self.turn_right()

    def left_click_func(self, event):
        print('left')

    def right_click_func(self, event):
        self.go_right()

    def up_click_func(self, event):
        self.go_forwards()

    def down_click_func(self, event):
        self.go_backwards()

    def handle_ping_window_quit(self):
        pass

    def updateDepth(self, event):
        chars = event.widget.get()
        try:
            val = float(chars.strip())
            print('new depth is %0.2f'%val)
            desiredDepth = val
            
            self.attMessage['dDepth'] = desiredDepth
            data = pickle.dumps(self.attMessage, protocol=3)
            self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_depthAtt, data])
        except:
            print('failed to load value')
        
        
    def updatePitch(self, event):
        chars = event.widget.get()
        try:
            val = float(chars.strip())
            print('new pitch is %0.2f'%val)
            desiredPitch = val
            self.attMessage['dPitch'] = desiredPitch
            data = pickle.dumps(self.attMessage, protocol=3)
            self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_depthAtt, data])
        except:
            print('failed to load value')
        
    def updateFocus(self, event):
        chars = event.widget.get()
        try:
            val = min(max(int(chars.strip()),850),2250)
            self.myStyle['focusCmd_textbox'].delete(0, END)
            self.myStyle['focusCmd_textbox'].insert(0,str(val))
            print('new focus PWM %d'%val)
            ## send focus command
        except:
            print('failed to load value')

    def updateYaw(self, event):
        chars = event.widget.get()
        try:
            val = float(chars.strip())
            print('new yaw is %0.2f'%val)
            desiredYaw = val
            self.attMessage['dYaw'] = desiredYaw
            data = pickle.dumps(self.attMessage, protocol=3)
            self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_depthAtt, data])
        except:
            print('failed to load value')
        

    def create_button(self, name, display_text, n_col, n_row, callback):
        button_name = "{}_button".format(name)
        _btn = Button(self.parent, text=display_text, command=callback, width=13,
                      activebackground=self.myStyle['activeButtonBg'])
        _btn.grid(column=n_col+1, row=n_row)
        _btn.config(background=self.myStyle['buttonBg'], foreground=self.myStyle['buttonFg'], font=self.TFont)
        self.myStyle[button_name] = _btn

        #print('-->', name, n_col, n_row)
        self.myStyle[button_name].place(x=self.initX+(n_col-1)*self.colWidth, y=self.initY+(n_row-1)*self.rowHeight)




    def image_clicked(self, event):
        if self.img is None:
            return
        try:
            tm_img = time.gmtime()

            obj = self.myStyle['disp_image']

            x = event.x
            y = event.y

            print('clicked x=%d, y=%d'%(x,y))
            # ImageGrab.grab().crop((x, y, width, height)).save(img_file)
        except Exception as err:
            print(err)

    def image_right_clicked(self, event):
        if self.img is None:
            return
        try:
            tm_img = time.gmtime()

            x = self.parent.winfo_rootx()
            y = self.parent.winfo_rooty()
            height = self.parent.winfo_height() + y
            width = self.parent.winfo_width() + x
            # ImageGrab.grab().crop((x, y, width, height)).save(img_file)
            # os.system("xdg-open {}".format(img_file))
        except Exception as err:
            print(err)

    def update_image(self):
        
        img = self.ROVHandler.getNewImage()
        if img is not None:
            #self.img = Image.open(io.BytesIO(img)) ## jpg stream
            img = Image.fromarray(img)
            self.img = ImageTk.PhotoImage(img)
            
            self.myStyle['disp_image'].configure(image=self.img)
            self.myStyle['disp_image'].image = self.img
        self.parent.after(10, self.update_image)

    
    def make_image(self, name, col, row, width, height, char_width, char_height):
        path = "rov.jpg"
        self.img = Image.open(path)
        self.img = ImageTk.PhotoImage(self.img.resize((char_width, char_height), Image.NONE))
        lbl = Label(self.parent, image=self.img, width=char_width, height=char_height, borderwidth=2,
                    highlightbackground="white")
        lbl.image = self.img
        lbl.grid(row=row, column=col, columnspan=width, rowspan=height, pady=5, padx=5, sticky="nw") #, sticky="nsew")
        self.myStyle[name] = lbl
        self.myStyle[name].place(x=15,y=35)

        self.update_image()


    def create_control_button(self, name, display_text, n_col, n_row, callback, toolTip = ""):
        button_name = "{}_button".format(name)
        btn = Button(self.parent, text=display_text, command=callback, width=9,
                     activebackground=self.myStyle['activeControlButtonBg'])
        #btn.grid(column=n_col, row=n_row)
        btn.config(background=self.myStyle['buttonBgControl'], foreground=self.myStyle['buttonFgControl'],
                   font=self.TFont)
        self.myStyle[button_name] = btn

        if len(toolTip) > 0:
            pass 
            #balloon = Balloon(self.parent, bg="white", title="Help")
            #balloon.bind_widget(self.myStyle[button_name], balloonmsg= toolTip)
        
        self.myStyle[button_name].place(x=self.initX+(n_col-1)*self.colButtonWidth, y=self.initY+(n_row-1)*self.rowHeight)


    def create_checkbox_button(self, name, display_text, n_col, n_row, var, anchor):
        checkbox = Checkbutton(self.parent, variable=var, onvalue=0, offvalue=1, text=display_text)
        checkbox.grid(column=n_col, row=n_row) #, sticky=anchor)
        checkbox.config(background=self.myStyle['bg'], foreground=self.myStyle['fg'], font=self.TFont)
        self.myStyle[name] = checkbox

        self.myStyle[name].place(x=self.initX+(n_col-1)*self.colWidth, y=self.initY+(n_row-1)*self.rowHeight)




    def turn_right(self):
        pass

    def turn_left(self):
        pass

    def go_up(self):
        pass

    def go_down(self):
        pass

    def go_left(self):
        pass

    def go_right(self):
        pass

    def go_forwards(self):
        pass

    def go_backwards(self):
        pass

    def led_off(self):
        pass

    def led_low(self):
        pass

    def led_high(self):
        pass

    def updateGuiData(self):
        try:
            telemtry = self.ROVHandler.getTelemtry()
            #print(telemtry.keys())
            if zmq_topics.topic_imu in telemtry.keys():
                data = telemtry[zmq_topics.topic_imu]
                self.myStyle['rtPitchtext'].config(text='%.2f°'%data['pitch'])
                self.myStyle['rtRolltext'].config(text='%.2f°'%data['roll'])
                self.myStyle['rtYawtext'].config(text='%.2f°'%data['yaw'])
            if zmq_topics.topic_depth in telemtry.keys():
                data = telemtry[zmq_topics.topic_depth]
                self.myStyle['rtDepthtext'].config(text='%.2f[m]'%data['depth'])
            if zmq_topics.topic_volt in telemtry.keys():
                data = telemtry[zmq_topics.topic_volt]
                self.myStyle['rtBatterytext'].config(text='%.2f[v]'%data['V'])
                
        except:
            import traceback
            traceback.print_exc()
            print('update gui data err')
            
        self.parent.after(25, self.updateGuiData)
    
    def cmdRecord(self):
        data = pickle.dumps(recordMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_diveModes, data])
        data = pickle.dumps(neutralHatMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_diveModes, data])
        self.update_button_active_command("record_button")
        
        if self.recClicked:
            self.myStyle["record_button"].config(foreground=self.myStyle['buttonFg'])
            self.myStyle["record_button"].config(activebackground=self.myStyle['activeButtonBg'])
        
        else:
            self.myStyle["record_button"].config(foreground=self.myStyle['activeDisplayButtonFg'])
            self.myStyle["record_button"].config(activebackground=self.myStyle['activeDisplayButtonBg'])
        self.recClicked = not self.recClicked
        
    
    
    def cmdArm(self):
        data = pickle.dumps(armDisarmMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_diveModes, data])
        data = pickle.dumps(neutralHatMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_diveModes, data])
        
        if self.armClicked:
            self.myStyle["arm_button"].config(foreground=self.myStyle['buttonFg'])
            self.myStyle["arm_button"].config(activebackground=self.myStyle['activeButtonBg'])
        
        else:
            self.myStyle["arm_button"].config(foreground=self.myStyle['activeDisplayButtonFg'])
            self.myStyle["arm_button"].config(activebackground=self.myStyle['activeDisplayButtonBg'])
        self.armClicked = not self.armClicked
    
    def cmdDepthHold(self):
        data = pickle.dumps(depthHoldMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_diveModes, data])
        data = pickle.dumps(neutralHatMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_diveModes, data])

    def cmdAttHold(self):
        data = pickle.dumps(attHoldMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_diveModes, data])
        data = pickle.dumps(neutralHatMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_diveModes, data])
        
    def cmdIncLights(self):
        data = pickle.dumps(lightUpMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_controller, data])
        data = pickle.dumps(neutralHatMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_controller, data])
        
    def cmdDecLights(self):
        data = pickle.dumps(lightDownMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_controller, data])
        data = pickle.dumps(neutralHatMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_controller, data])
        
    def focusFar(self):
        data = pickle.dumps(focusFarMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_controller, data])
        
    def focusNear(self):
        data = pickle.dumps(focusNearMsg, protocol=3)
        self.rovGuiCommandPublisher.send_multipart( [zmq_topics.topic_gui_controller, data])
    
    def updatePids(self):
        telemtry = self.ROVHandler.getTelemtry()
        rollData = None
        pitchData = None
        yawData = None
        depthData = None
        if zmq_topics.topic_att_hold_roll_pid in telemtry.keys():
            rollData = telemtry[zmq_topics.topic_att_hold_roll_pid]
            topic = zmq_topics.topic_att_hold_roll_pid
            if topic not in self.pidMsgs:
                    self.pidMsgs[topic] = CycArr(500)
            self.pidMsgs[topic].add(rollData)
            
        if zmq_topics.topic_att_hold_pitch_pid in telemtry.keys():
            pitchData = telemtry[zmq_topics.topic_att_hold_pitch_pid]
            
            topic = zmq_topics.topic_att_hold_pitch_pid
            if topic not in self.pidMsgs:
                    self.pidMsgs[topic] = CycArr(500)
            self.pidMsgs[topic].add(pitchData)
            
        if zmq_topics.topic_att_hold_yaw_pid in telemtry.keys():
            yawData = telemtry[zmq_topics.topic_att_hold_yaw_pid]
            
            topic = zmq_topics.topic_att_hold_yaw_pid
            if topic not in self.pidMsgs:
                    self.pidMsgs[topic] = CycArr(500)
            self.pidMsgs[topic].add(yawData)
                
        if zmq_topics.topic_depth_hold_pid in telemtry.keys():
            depthData = telemtry[zmq_topics.topic_depth_hold_pid]
            
            topic = zmq_topics.topic_depth_hold_pid
            if topic not in self.pidMsgs:
                    self.pidMsgs[topic] = CycArr(500)
            self.pidMsgs[topic].add(depthData)
        
        
        
        if (self.checkDepthControl.get() == 0) and (depthData is not None):
            self.plotData(zmq_topics.topic_depth_hold_pid, 'Depth control')
            
        if (self.checkPitchControl.get() == 0) and (pitchData is not None):
            self.plotData(zmq_topics.topic_att_hold_pitch_pid, 'Pitch control')
            
        if (self.checkRollControl.get() == 0) and (rollData is not None):
            self.plotData(zmq_topics.topic_att_hold_roll_pid, 'Roll control')
            
        if (self.checkYawControl.get() == 0) and (yawData is not None):
            self.plotData(zmq_topics.topic_att_hold_yaw_pid, 'Yaw control')
        
            
        self.parent.after(20, self.updatePids)
        
        
    
    def initPlots(self):

        self.hdls=[self.ax1.plot([1],'-b'), self.ax1.plot([1],'-g'), self.ax1.plot([1],'-r'), self.ax1.plot([1],'-k')]
        self.ax1.grid('on')
        
        self.hdls2=[self.ax2.plot([1],'-b'), self.ax2.plot([1],'-g'), self.ax2.plot([1],'-r')]
        self.ax2.grid('on')
        
        self.canvas.draw()
    
    def plotData(self, topic, title):
        msgs = self.pidMsgs[topic]
        data = msgs.get_data(['TS','P','I','D','C'])
        
        self.ax1.set_title(title+ ' pid')
        xs = np.arange(data.shape[0])
        
        for i in [0,1,2,3]:
            self.hdls[i][0].set_ydata(data[:,i+1]) #skip timestemp
            self.hdls[i][0].set_xdata(xs)
        self.ax1.set_xlim(data.shape[0]-400,data.shape[0])
        self.ax1.set_ylim(-1,1)
        self.ax1.legend(list('pidc'),loc='upper left')
        
        
        self.ax2.set_title(title)
        data = msgs.get_data(['T','N','R'])
        #cmd_data=gdata.md_hist.get_data(label+'_cmd')
        for i in [0,1,2]:
            self.hdls2[i][0].set_ydata(data[:,i])
            self.hdls2[i][0].set_xdata(xs)
        self.ax2.set_xlim(data.shape[0]-400,data.shape[0])
        min_y = data.min()
        max_y = data.max()
        self.ax2.set_ylim(min_y,max_y)
        self.ax2.legend(list('TNR'),loc='upper left')
        
        self.canvas.draw()


    def make_widgets(self):
        propertyCol = 1
        commandCol = 3
        controlCol = 5
        
        row_index = 0
        self.create_main_col_row_labels()
       
        row_index += 1
        initRow = 6 #15
        #set video window
        col1X = 15
        row1Y = 660

        self.make_image(name='disp_image', col=1, row=row_index, width=10, height=7, char_width=968, char_height=608)
        row_index += initRow#15
        '''
        self.create_label_header(name="header", display_text1="Property", display_text2="Status",
                                 display_text3="Commands", display_text4="Control",
                                 display_text5=" Manual control ", n_col=1,
                                 n_row=row_index)
        '''
        rtDataRow = 1
        rtDataCol = 1
        cmd1Col = 3
        # creates ststic text with text
        self.create_text_box(name="ROV_Data", label_text="ROV ip:", display_text="192.168.3.10", n_col=rtDataCol,  n_row=rtDataRow, textbox_width=15)
        self.myStyle["ROV_Data_label"].place(x=col1X, y=row1Y)
        rtDataRow += 1
        self.create_label_pair(name="rtDepth", display_text="Depth:", n_col=rtDataCol, n_row=rtDataRow)
        self.create_text_box(name="depthCmd", label_text="dDepth:", display_text="[m]", n_col=cmd1Col , n_row=rtDataRow, textbox_width=9)
        self.myStyle['depthCmd_textbox'].bind("<Key-Return>", self.updateDepth)
        rtDataRow += 1
        self.create_label_pair(name="rtPitch", display_text="Pitch:", n_col=rtDataCol, n_row=rtDataRow)
        self.create_text_box(name="pitchCmd", label_text="dPitch:", display_text="[deg]", n_col=cmd1Col, n_row=rtDataRow, textbox_width=9)
        self.myStyle['pitchCmd_textbox'].bind("<Key-Return>", self.updatePitch)
        rtDataRow += 1
        self.create_label_pair(name="rtYaw", display_text="Yaw:", n_col=rtDataCol, n_row=rtDataRow)
        self.create_text_box(name="yawCmd", label_text="dYaw:", display_text="[deg]", n_col=cmd1Col, n_row=rtDataRow, textbox_width=9)
        self.myStyle['yawCmd_textbox'].bind("<Key-Return>", self.updateYaw)
        rtDataRow += 1
        self.create_label_pair(name="rtRoll", display_text="Roll:", n_col=rtDataCol, n_row=rtDataRow)
        self.create_text_box(name="focusCmd", label_text="focusPWM:", display_text="0", n_col=cmd1Col, n_row=rtDataRow, textbox_width=9)
        self.myStyle['focusCmd_textbox'].bind("<Return>", self.updateFocus)
        #self.myStyle['focusCmd_textbox'].configure(state=DISABLED)
        rtDataRow += 1
        self.create_label_pair(name="rtBattery", display_text="BATT:", n_col=rtDataCol, n_row=rtDataRow)
        

        pidRow = 7
        pidCol = 1
        self.create_checkbox_button("showDepth", "depth control", pidCol, pidRow, self.checkDepthControl, anchor='w')
        pidRow += 1
        self.create_checkbox_button("showPitch", "pitch control", pidCol, pidRow, self.checkPitchControl, anchor='w')
        pidRow += 1
        self.create_checkbox_button("showRoll", "roll control", pidCol, pidRow, self.checkRollControl, anchor='w')
        pidRow += 1
        self.create_checkbox_button("showYaw", "yaw control", pidCol, pidRow, self.checkYawControl, anchor='w')
        pidRow += 1

        modesRow = 6
        modesCol =3
        #self.create_checkbox_button("depthHold", "Depth hold", commandCol, row_index, self.checkDepthHold, anchor='w')
        #self.myStyle["depthHold"].configure(command=self.cmdDepthHold)
        self.create_button("depthHold", "Depth hold", modesCol, modesRow, self.cmdDepthHold)
        modesRow += 1
        #self.create_checkbox_button("attHold", "Attitude hold", commandCol, row_index, self.checkAttHold, anchor='w')
        #self.myStyle["attHold"].configure(command=self.dummy)
        self.create_button("attHold", "attitude hold", modesCol, modesRow, self.cmdAttHold)
        modesRow += 1
        self.create_button("getRecords", "Fetch Recs", modesCol, modesRow, self.fetchRecords)
      
        
        row_btn_idx = 2
        btnCol = 5
        self.create_button("runRemote", "run ROV", btnCol, row_btn_idx, self.runRemote)
        row_btn_idx += 1
        self.create_button("arm", "ARM/DISARM", btnCol, row_btn_idx, self.cmdArm)
        row_btn_idx += 1
        self.create_button("record", "Record", btnCol, row_btn_idx, self.cmdRecord)
        row_btn_idx += 1        
        self.create_button("ledsUp", "Inc. Lights", btnCol, row_btn_idx, self.cmdIncLights)
        row_btn_idx += 1
        self.create_button("ledsDown", "Dec. Lights", btnCol, row_btn_idx, self.cmdDecLights)
        row_btn_idx += 1
        self.create_button("focusFar", "Focus far", btnCol, row_btn_idx, self.focusFar)
        row_btn_idx += 1
        self.create_button("focusNear", "Focus near", btnCol, row_btn_idx, self.focusNear)
        row_btn_idx += 1
        self.create_button("killRemote", "kill ROV", btnCol, row_btn_idx, self.killRemote)
        row_btn_idx += 1
        self.create_button("rebootRemote", "reboot ROV", btnCol, row_btn_idx, self.rebootRemote)
        
        

        
        
        if 1:
            ### show manual controls
            control_start_col = 6#12
            manualControlOffsetRow = 3
            xMiddleButton = 1007
            buttonWidth = 143
            
            self.create_control_button("yawLeft", "↙ Yaw left", control_start_col, manualControlOffsetRow, self.go_up, toolTip="yawing ROV left 5deg.")
            self.create_control_button("goLeft", "❰❰", control_start_col , manualControlOffsetRow+1, self.turn_left)
            self.create_control_button("deeper", "Deeper ⟱", control_start_col , manualControlOffsetRow+2, self.go_forwards)
            control_start_col += 1
            self.create_control_button("goForward", "⟰", control_start_col, manualControlOffsetRow, self.go_forwards)
            #self.myStyle["goForward_button"].place(x=xMiddleButton, y=732)
            self.create_control_button("stopMotion", "▄ ", control_start_col, manualControlOffsetRow+1, self.go_forwards)
            #self.myStyle["stopMotion_button"].place(x=xMiddleButton, y=767)
            self.create_control_button("goBackwords", "⟱", control_start_col, manualControlOffsetRow+2, self.go_backwards)
            #self.myStyle["goBackwords_button"].place(x=xMiddleButton, y=802)
            control_start_col += 1
            self.create_control_button("yawRight", "Yaw right ↘", control_start_col, manualControlOffsetRow, self.go_down)
            #self.myStyle["yawRight_button"].place(x=xMiddleButton+buttonWidth, y=732)
            self.create_control_button("goRight", "❱❱", control_start_col, manualControlOffsetRow+1, self.turn_right)
            #self.myStyle["goRight_button"].place(x=xMiddleButton+buttonWidth, y=767)
            self.create_control_button("shallower", "Shallower ⟰", control_start_col, manualControlOffsetRow+2, self.go_backwards)
            #self.myStyle["shallower_button"].place(x=xMiddleButton+buttonWidth, y=802)
            
            self.create_checkbox_button("inertial", "inertial movment", 8, 2, self.checkInertial, anchor='w')
            #self.myStyle["inertial"].place(x=965, y=680)
        ###############################

        self.figure1 = plt.Figure(figsize=(7,5), dpi=100)
        self.ax1 = self.figure1.add_subplot(211)
        self.ax2 = self.figure1.add_subplot(212)
        bar1 = FigureCanvasTkAgg(self.figure1, self.parent)

        self.canvas = FigureCanvasTkAgg(self.figure1, master=self.parent)
        # here: plot suff to your fig

        frame = Frame(self.parent)
        #frame.grid(row=0, column=9)
        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        frame.place(x=1000,y=1)
        #self.canvas.get_tk_widget().grid(column=9, row=1, rowspan=1, columnspan=8)
        self.canvas.get_tk_widget().grid(rowspan=1, columnspan=8)
        self.canvas.get_tk_widget().place(x=1000,y=45)
        self.initPlots()
        self.canvas.draw()
        ###############################
 
        
        
    def fetchRecords(self):
        os.system('cd ../scripts && ./recSync.sh')
        
    def runRemote(self):
        os.system('cd ../scripts && ./run_remote.sh')
    
    def rebootRemote(self):
        os.system('cd ../scripts && ./reboot_remote.sh')
        
    def killRemote(self):
        os.system('cd ../scripts && ./kill_remote.sh')
    
    def dummy(self):
        pass


    def update_button_active_command(self, button_name):
        if button_name is self.last_pressed_button:
            return
        if self.last_pressed_button in self.myStyle:
            self.myStyle[self.last_pressed_button].config(foreground=self.myStyle['buttonFg'])
            self.myStyle[self.last_pressed_button].config(activebackground=self.myStyle['activeButtonBg'])
        self.last_pressed_button = button_name
        if self.last_pressed_button in self.myStyle:
            self.myStyle[self.last_pressed_button].config(foreground=self.myStyle['activeDisplayButtonFg'])
            self.myStyle[self.last_pressed_button].config(activebackground=self.myStyle['activeDisplayButtonBg'])


if __name__=='__main__':
    try:
        root = Tk()
        #root.grid_columnconfigure(0, weight=1)
        #root.grid_rowconfigure(0, weight=1)
        #root.resizable(True, False)
        guiInstance = rovViewerWindow(root)
        root.bind("<Configure>", guiInstance.resize)

        ### placing debug - show mouse motion over GUI
        #def motion(event):
        #    x, y = event.x, event.y
        #    print('{}, {}'.format(x, y))
        #root.bind('<Motion>', motion)
        
        root.protocol("WM_DELETE_WINDOW", guiInstance.quit)
        root.mainloop()
    except:
        import traceback
        traceback.print_exc()
    finally:
        guiInstance.quit()
        
