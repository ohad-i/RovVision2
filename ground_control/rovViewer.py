#!/usr/bin/python3
# need fping install - sudo apt install fping
# install ssh support - Exscript @ https://exscript.readthedocs.io/en/latest/install.html
# install matplotlib -  sudo apt-get install python3-matplotlib

from tkinter import *
from PIL import Image, ImageTk
import io
import time
import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

#from PIL import ImageGrab
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


## matplotlib functions
##CPingWindow
class pidGraph(Frame):
    def __init__(self, parent=None, **kw):
        super().__init__(**kw)
        self.max_list_size = 100
        self.list_size = 3
        self.x_values = range(self.list_size)
        self.long_ping = [0] * self.list_size
        self.short_ping = [0] * self.list_size
        self.rssi_str = [0] * self.list_size
        self.rssi_clar = [0] * self.list_size

        self.parent = parent
        self.window = Tk()
        self.window.title("Crazy-Flie connection analysis")
        # w, h = self.window.winfo_screenwidth(), self.window.winfo_screenheight()
        self.window.geometry("%dx%d+0+0" % (420, 240))
        self.window.protocol("WM_DELETE_WINDOW", self.parent.handle_ping_window_quit)  # register kill command
        # self.canvas = Canvas(master=self.window, width=400, height=200)
        # self.canvas.grid(row=1, column=0)

        # the figure that will contain the plot
        self.fig = Figure(figsize=(5, 5), dpi=100)

        # adding the subplot
        self.plot1 = self.fig.add_subplot(111)

        # creating the Tkinter canvas
        # containing the Matplotlib figure
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)

        # self.plotline1 = self.plot1.plot(self.x_values, self.short_ping)
        # self.plotline2 = self.plot1.plot(self.x_values, self.long_ping)
        # self.plotline3 = self.plot1.plot(self.x_values, self.rssi_str)
        self.plotline3 = self.plot1.plot(self.x_values, self.rssi_clar)

        ax = self.canvas.figure.axes[0]
        ax.set_xlim(0, self.list_size - 1)
        ax.set_ylim(-0.5, 101)

        self.canvas.draw()
        # placing the canvas on the Tkinter window
        self.canvas.get_tk_widget().pack()
        self.window.after(500, self.refresh_figure)

    def quit(self):
        self.window.destroy()

    def maximize(self):
        self.window.geometry("%dx%d+0+0" % (420, 220))
        self.window.lift()

    def update_ping_values(self, short_val, long_val, rssi_str, rssi_clar):
        if self.list_size >= self.max_list_size:
            self.long_ping.pop(0)
            self.short_ping.pop(0)
            self.rssi_str.pop(0)
            self.rssi_clar.pop(0)
        else:
            self.list_size += 1
        self.long_ping.append(long_val)
        self.short_ping.append(short_val)
        self.rssi_str.append(rssi_str)
        self.rssi_clar.append(rssi_clar)

        # callback is hooked every 500 ms
        # self.window.after(100, self.refreshFigure)

    def refresh_figure(self):
        self.plot1.clear()
        self.x_values = range(self.list_size)

        # self.plotline1 = self.plot1.plot(self.x_values, self.short_ping)
        # self.plotline2 = self.plot1.plot(self.x_values, self.long_ping)
        # self.plotline3 = self.plot1.plot(self.x_values, self.rssi_str)
        self.plotline3 = self.plot1.plot(self.x_values, self.rssi_clar)

        ax = self.canvas.figure.axes[0]
        ax.set_xlim(0, self.list_size)
        ax.set_ylim(-0.1, 101)
        self.canvas.draw()
        self.window.after(500, self.refresh_figure)
        
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
        self.last_cmd_from_cf = 'disarmed'
        self.last_pressed_button = 'disarm'
        
        self.TFont = ("Courier", 14)
        self.TextboxFont = ("Courier", 12)
        self.HeaderFont = ("Courier", 16, "underline")
        
        
        self.ROVHandler = rovDataHandler(self)
        self.ROVHandler.start()

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
        self.myStyle[second_name] = Label(self.parent, text="n/a", width=18)
        self.myStyle[first_name].grid(column=n_col, row=n_row)
        self.myStyle[second_name].grid(column=n_col + 1, row=n_row)
        self.myStyle[first_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])
        self.myStyle[second_name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])

        self.myStyle[first_name].config(font=self.TFont)
        self.myStyle[second_name].config(font=self.TFont)

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
        #self.parent.protocol("WM_DELETE_WINDOW", self.client_exit)  # register kill command

        
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

    def ip_clicked_func(self, event):
        print('ip clicked')
        if self.ping_window is not None:
            self.ping_window.maximize()
            return
        self.ping_window = CPingWindow(self)
        self.update_ping_window = True

    def update_height(self, event):
        chars = event.widget.get("1.0", "end-1c")
        val = chars.replace('\n', '').strip()
        self.height_val = val

    def update_nominal(self, event):
        chars = event.widget.get("1.0", "end-1c")
        val = chars.replace('\n', '').strip()
        self.nominal_velocity_val = val

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
        
    def updateRoll(self, event):
        chars = event.widget.get()
        try:
            val = float(chars.strip())
            print('new roll is %0.2f'%val)
            desiredRoll = val
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
        

    
        
    def create_label_buffer(self, name, n_col, n_row):
        self.myStyle[name] = Label(master=self.parent, text='    ')
        self.myStyle[name].grid(column=n_col, row=n_row)
        self.myStyle[name].configure(background=self.myStyle['bg'], foreground=self.myStyle['fg'])

    def create_button(self, name, display_text, n_col, n_row, callback):
        button_name = "{}_button".format(name)
        _btn = Button(self.parent, text=display_text, command=callback, width=13,
                      activebackground=self.myStyle['activeButtonBg'])
        _btn.grid(column=n_col+1, row=n_row)
        _btn.config(background=self.myStyle['buttonBg'], foreground=self.myStyle['buttonFg'], font=self.TFont)
        self.myStyle[button_name] = _btn

    def make_square(self, col, row, width, height, bg):
        submit_btn = Button(self.parent, text='            ', borderwidth=1)
        submit_btn.grid(row=row, column=col, columnspan=width, rowspan=height, pady=15, padx=7, sticky="nwse")
        submit_btn.config(background=bg, activebackground=bg)
        self.myStyle['control_bg'] = submit_btn

    def image_clicked(self, event):
        if self.img is None:
            return
        try:
            tm_img = time.gmtime()
            img_file = "logs/img_{}_{}_{}__{}_{}_{}.jpg".format(tm_img.tm_year, tm_img.tm_mon, tm_img.tm_mday,
                                                                tm_img.tm_hour, tm_img.tm_min, tm_img.tm_sec)

            obj = self.myStyle['disp_image']

            x = obj.winfo_rootx()
            y = obj.winfo_rooty()
            height = obj.winfo_height() + y
            width = obj.winfo_width() + x
            # ImageGrab.grab().crop((x, y, width, height)).save(img_file)
        except Exception as err:
            print(err)

    def image_right_clicked(self, event):
        if self.img is None:
            return
        try:
            tm_img = time.gmtime()
            img_file = "logs/screenshot_{}_{}_{}__{}_{}_{}.jpg".format(tm_img.tm_year, tm_img.tm_mon, tm_img.tm_mday,
                                                                tm_img.tm_hour, tm_img.tm_min, tm_img.tm_sec)

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
        self.parent.after(50, self.update_image)

    def should_rotate_180(self):
        if self.check_inverted_cam.get() == 0:
            return True
        return False

    
    def make_image(self, name, col, row, width, height, char_width, char_height):
        path = "rov.jpg"
        self.img = Image.open(path)
        self.img = ImageTk.PhotoImage(self.img.resize((char_width, char_height), Image.NONE))
        lbl = Label(self.parent, image=self.img, width=char_width, height=char_height, borderwidth=2,
                    highlightbackground="white")
        lbl.image = self.img
        lbl.grid(row=row, column=col, columnspan=width, rowspan=height, pady=5, padx=5, sticky="nw") #, sticky="nsew")
        self.myStyle[name] = lbl
        self.update_image()

    def create_control_button(self, name, display_text, n_col, n_row, callback):
        button_name = "{}_button".format(name)
        btn = Button(self.parent, text=display_text, command=callback, width=10,
                     activebackground=self.myStyle['activeControlButtonBg'])
        btn.grid(column=n_col, row=n_row)
        btn.config(background=self.myStyle['buttonBgControl'], foreground=self.myStyle['buttonFgControl'],
                   font=self.TFont)
        self.myStyle[button_name] = btn

    def create_checkbox_button(self, name, display_text, n_col, n_row, var, anchor):
        checkbox = Checkbutton(self.parent, variable=var, onvalue=0, offvalue=1, text=display_text)
        checkbox.grid(column=n_col, row=n_row) #, sticky=anchor)
        checkbox.config(background=self.myStyle['bg'], foreground=self.myStyle['fg'], font=self.TFont)
        self.myStyle[name] = checkbox

    def send_command(self, opcode, x, y, z):
        pass

    def move(self, x, y, z, psi):
        pass

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

    def get_vers(self):
        self.clear_version()

    def get_records(self):
        pass

    def get_last_record(self):
        pass

    def cmd_manual(self):
        self.update_button_active_command("manual__button")
        pass

    def cmd_cruise_and_return(self):
        self.update_button_active_command("cruise_and_return__button")
        pass

    def cmd_png_viz(self):
        pass

    def cmd_png_map(self):
        pass


    def setStringValue(self, labelKey, val):
        self.myStyle[labelKey+'text']['text'] = str(val)
        
    
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
        
        ###############################
                
        self.figure1 = plt.Figure(figsize=(7,5), dpi=100)
        self.ax1 = self.figure1.add_subplot(211)
        self.ax2 = self.figure1.add_subplot(212)
        bar1 = FigureCanvasTkAgg(self.figure1, self.parent)
        
        self.canvas = FigureCanvasTkAgg(self.figure1, master=self.parent)
        #canvas.get_tk_widget().grid(column=7, row=1, rowspan=1, columnspan=4)
        # here: plot suff to your fig
        
        frame = Frame(self.parent)
        frame.grid(row=0, column=7)
        toobar = NavigationToolbar2Tk(self.canvas, frame)
        self.canvas.get_tk_widget().grid(column=7, row=1, rowspan=1, columnspan=8)
        self.initPlots()
        self.canvas.draw()
        ###############################
        
        
        row_index += 1
        initRow = 6 #15
        #set video window
        self.make_image(name='disp_image', col=1, row=row_index, width=10, height=12, char_width=800, char_height=600)
        row_index += initRow#15
        '''
        self.create_label_header(name="header", display_text1="Property", display_text2="Status",
                                 display_text3="Commands", display_text4="Control",
                                 display_text5=" Manual control ", n_col=1,
                                 n_row=row_index)
        '''
        row_index += 1
        # creates ststic text with text
        self.create_text_box(name="ROV_Data", label_text="ROV ip:", display_text="192.168.3.10", n_col=propertyCol, n_row=row_index,
                             textbox_width=15)
        
        row_index += 1
        self.create_label_pair(name="rtDepth", display_text="Depth:", n_col=propertyCol, n_row=row_index)
        self.create_text_box(name="depthCmd", label_text="dDepth:", display_text="[m]", n_col=commandCol, n_row=row_index, textbox_width=1)
        self.myStyle['depthCmd_textbox'].bind("<Key-Return>", self.updateDepth)
        row_index += 1
        self.create_label_pair(name="rtPitch", display_text="Pitch:", n_col=propertyCol, n_row=row_index)
        self.create_text_box(name="pitchCmd", label_text="dPitch:", display_text="[deg]", n_col=commandCol, n_row=row_index, textbox_width=5)
        self.myStyle['pitchCmd_textbox'].bind("<Key-Return>", self.updatePitch)
        row_index += 1
        self.create_label_pair(name="rtRoll", display_text="Roll:", n_col=propertyCol, n_row=row_index)
        self.create_text_box(name="rollCmd", label_text="dRoll:", display_text="0.0°", n_col=commandCol, n_row=row_index, textbox_width=5)
        self.myStyle['rollCmd_textbox'].bind("<Key-Return>", self.updateRoll)
        self.myStyle['rollCmd_textbox'].configure(state=DISABLED)
        row_index += 1
        self.create_label_pair(name="rtYaw", display_text="Yaw:", n_col=propertyCol, n_row=row_index)
        self.create_text_box(name="yawCmd", label_text="dYaw:", display_text="[deg]", n_col=commandCol, n_row=row_index, textbox_width=5)
        self.myStyle['yawCmd_textbox'].bind("<Key-Return>", self.updateYaw)
        row_index += 1
        self.create_label_pair(name="rtBattery", display_text="BATT:", n_col=propertyCol, n_row=row_index)
        pidRow = row_index + 1
        
        self.create_checkbox_button("showDepth", "depth control", propertyCol, pidRow, self.checkDepthControl, anchor='w')
        pidRow += 1
        self.create_checkbox_button("showPitch", "pitch control", propertyCol, pidRow, self.checkPitchControl, anchor='w')
        pidRow += 1
        self.create_checkbox_button("showRoll", "roll control", propertyCol, pidRow, self.checkRollControl, anchor='w')
        pidRow += 1
        self.create_checkbox_button("showYaw", "yaw control", propertyCol, pidRow, self.checkYawControl, anchor='w')
        pidRow += 1
        
        #self.create_checkbox_button("depthHold", "Depth hold", commandCol, row_index, self.checkDepthHold, anchor='w')
        #self.myStyle["depthHold"].configure(command=self.cmdDepthHold)
        self.create_button("depthHold", "Depth hold", commandCol, row_index, self.cmdDepthHold)
        row_index += 1
        #self.create_checkbox_button("attHold", "Attitude hold", commandCol, row_index, self.checkAttHold, anchor='w')
        #self.myStyle["attHold"].configure(command=self.dummy)
        self.create_button("attHold", "attitude hold", commandCol, row_index, self.cmdAttHold)
        row_index += 1
        self.create_button("getRecords", "Fetch Recs", commandCol, row_index, self.fetchRecords)
      
        
        row_btn_idx = initRow+2
        self.create_button("runRemote", "run ROV", controlCol, row_btn_idx, self.runRemote)
        row_btn_idx += 1
        self.create_button("arm", "ARM/DISARM", controlCol, row_btn_idx, self.cmdArm)
        row_btn_idx += 1
        self.create_button("record", "Record", controlCol, row_btn_idx, self.cmdRecord)
        row_btn_idx += 1        
        self.create_button("ledsUp", "Inc. Lights", controlCol, row_btn_idx, self.cmdIncLights)
        row_btn_idx += 1
        self.create_button("ledsDown", "Dec. Lights", controlCol, row_btn_idx, self.cmdDecLights)
        row_btn_idx += 1
        self.create_button("focusFar", "Focus far", controlCol, row_btn_idx, self.focusFar)
        row_btn_idx += 1
        self.create_button("focusNear", "Focus near", controlCol, row_btn_idx, self.focusNear)
        row_btn_idx += 1
        self.create_button("killRemote", "kill ROV", controlCol, row_btn_idx, self.killRemote)
        row_btn_idx += 1
        self.create_button("rebootRemote", "reboot ROV", controlCol, row_btn_idx, self.rebootRemote)
        row_btn_idx += 1
        

        
        
        if 0:
            ### show manual controls
            control_start_col = 7 #12
            manualControlOffsetRow = 16
            #self.make_square(col=control_start_col, row=manualControlOffsetRow+2, width=10, height=5, bg='gray90')
            self.create_control_button("goRight", "❱❱", control_start_col + 2, manualControlOffsetRow+4, self.turn_right)
            self.create_control_button("goLeft", "❰❰", control_start_col , manualControlOffsetRow+4, self.turn_left)
            self.create_control_button("goForward", "⟰", control_start_col + 1, manualControlOffsetRow+3, self.go_forwards)
            self.create_control_button("goForward", "▄ ", control_start_col + 1, manualControlOffsetRow+4, self.go_forwards)
            self.create_control_button("goBackwords", "⟱", control_start_col + 1, manualControlOffsetRow+5, self.go_backwards)
            
            self.create_checkbox_button("inertial", "inertial movment", control_start_col + 1, manualControlOffsetRow+1, self.checkInertial, anchor='w')
            
            self.create_control_button("yawLeft", "↙ Yaw left", control_start_col, manualControlOffsetRow+3, self.go_up)
            self.create_control_button("yawRight", "Yaw right ↘", control_start_col + 2, manualControlOffsetRow+3, self.go_down)
            
            self.create_control_button("deeper", "Deeper ⟱", control_start_col , manualControlOffsetRow+5, self.go_forwards)
            self.create_control_button("shallower", "Shallower ⟰", control_start_col + 2, manualControlOffsetRow+5, self.go_backwards)
    
        
        
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

    def clear_version(self):
        self.myStyle['vers_textbox'].config(state=NORMAL)
        self.myStyle["vers_textbox"].delete('1.0', END)
        time.sleep(0.1)
        self.myStyle['vers_textbox'].config(state=DISABLED)

    def add_version(self, data):
        data = " {}".format(data)
        self.myStyle['vers_textbox'].config(state=NORMAL)
        self.myStyle['vers_textbox'].insert(END, data)
        self.myStyle['vers_textbox'].see(END)
        self.myStyle['vers_textbox'].insert(END, "\n")
        time.sleep(0.01)
        self.myStyle['vers_textbox'].config(state=DISABLED)

    def client_exit(self):
        
        log_file.close()
        if self.ping_window is not None:
            self.ping_window.quit()
        exit()

    def update_explore_display_status(self, txt):
        try:
            val = int(float(txt) / 1000)
            txt = "{}".format(val)
        finally:
            self.myStyle['explore_d_text']['text'] = txt

    def update_motor_status(self, txt):
        color = 'black'
        try:
            val = int(txt)
            m1 = val % 2
            val = int(val/2)
            m2 = val % 2
            val = int(val / 2)
            m3 = val % 2
            val = int(val / 2)
            m4 = val % 2

            txt = "{}.{}.{}.{}".format(m1, m2, m3, m4)
            if m1 and m2 and m3 and m4:
                color = 'green'
            else:
                color = 'red'
        finally:
            self.myStyle['prop_test_text']['text'] = txt
            self.myStyle['prop_test_text'].config(foreground=color)

    def update_height_display_status(self, txt):
        try:
            val = float(txt)
            txt = "{:.2f}".format(val)
        finally:
            self.myStyle['height_d_text']['text'] = txt

    def update_vnom_display_status(self, txt):
        try:
            val = float(txt)
            txt = "{:.1f}".format(val)
        finally:
            self.myStyle['nominal_d_text']['text'] = txt

    def update_squal_display_status(self, txt):
        try:
            val = int(txt)
            txt = "{}".format(val)
        except Exception as err:
            print("can't set squal value")
            print(err)
        finally:
            self.myStyle['squall_d_text']['text'] = txt

    def update_control_display_status(self, txt):
        pass

    def update_oper_display_status(self, txt):
        try:
            if int(txt) > 0:
                txt = 'T'
            else:
                txt = 'F'
        finally:
            self.myStyle['oper_d_text']['text'] = txt

    def update_zret_display_status(self, txt):
        try:
            if int(txt) > 0:
                txt = 'T'
            else:
                txt = 'F'
        finally:
            self.myStyle['zreject_d_text']['text'] = txt

    def update_ofret_display_status(self, txt):
        try:
            if int(txt) > 0:
                txt = 'T'
            else:
                txt = 'F'
        finally:
            self.myStyle['ofreject_d_text']['text'] = txt

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
        
        root.protocol("WM_DELETE_WINDOW", guiInstance.quit)
        root.mainloop()
    except:
        import traceback
        traceback.print_exc()
    finally:
        guiInstance.quit()
        
