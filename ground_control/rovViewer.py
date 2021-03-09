#!/usr/bin/python3
# need fping install - sudo apt install fping
# install ssh support - Exscript @ https://exscript.readthedocs.io/en/latest/install.html
# install matplotlib -  sudo apt-get install python3-matplotlib

from tkinter import *
from PIL import Image, ImageTk
import io
import time
import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import subprocess
#from PIL import ImageGrab
import os

tm = time.gmtime()
filename = "logs/gui_{}_{}_{}__{}_{}_{}.log".format(
    tm.tm_year, tm.tm_mon, tm.tm_mday,
    tm.tm_hour, tm.tm_min, tm.tm_sec)
log_file = open(filename, "a")


def log(data):
    try:
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        log_file.write("{} - {}".format(st, data))
        log_file.write("\n")
        log_file.flush()
        print(data)
    finally:
        pass


# this class helps add callback to text modification
class CustomText(Text):
    def __init__(self, *args, **kwargs):
        """A text widget that report on internal widget commands"""
        Text.__init__(self, *args, **kwargs)

        # create a proxy for the underlying widget
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, command, *args):
        cmd = (self._orig, command) + args
        result = self.tk.call(cmd)

        if command in ("insert", "delete", "replace"):
            self.event_generate("<<TextModified>>")

        return result

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

# this class is the base of our GUI
class rovViewerWindow(Frame):
    def __init__(self, parent=None, **kw):
        super().__init__(**kw)
        self.parent = parent

        # init attributes
        self.init_time = datetime.datetime.utcnow()
        
        
        self.checkDepthHold = IntVar()
        self.checkDepthHold.set(1)
        
        self.checkAttHold = IntVar()
        self.checkAttHold.set(1)
        
        
        self.checkDepthControl = IntVar()
        self.checkDepthControl.set(1)
        self.checkPitchControl = IntVar()
        self.checkPitchControl.set(1)
        self.checkRollControl = IntVar()
        self.checkRollControl.set(1)
        self.checkYawControl = IntVar()
        self.checkYawControl.set(1)
        
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

        # create widgets
        self.make_widgets()
        self.bind_widgets_events()
        self.maximize_with_title()
        self.set_style()
        
        log(' display layer init done ')

        
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

    def create_disabled_label(self, name, display_text, n_col, n_row, width):
        lbl = Label(self.parent, text=display_text, width=width)
        lbl.grid(column=n_col, row=n_row, sticky='e', padx=2, pady=2)
        lbl.configure(background=self.myStyle['bg'], foreground=self.myStyle['disabled_fg'])
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
        for number in range(0, 30):
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

        self.myStyle[first_name] = Label(self.parent, text=display_text1, anchor="w", width=15)
        self.myStyle[second_name] = Label(self.parent, text=display_text2, width=10)
        self.myStyle[third_name] = Label(self.parent, text=display_text3, width=15)
        self.myStyle[fourth_name] = Label(self.parent, text=display_text4, width=15)
        self.myStyle[fifth_name] = Label(self.parent, text=display_text5, width=15)

        self.myStyle[first_name].grid(column=n_col, row=n_row)
        self.myStyle[second_name].grid(column=n_col + 1, row=n_row)
        self.myStyle[third_name].grid(column=n_col + 3, row=n_row)
        self.myStyle[fourth_name].grid(column=n_col + 5, row=n_row)
        self.myStyle[fifth_name].grid(column=15, row=n_row)

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

    def create_single_textbox(self, name, width, height, n_col, n_row, col_span):
        txt = CustomText(self.parent, borderwidth=1, padx=2, pady=2, relief="sunken", width=width, height=height,
                         selectbackground=self.myStyle['select_bg'])
        txt.config(font=self.TextboxFont, undo=True, wrap='word')
        txt.config(state=DISABLED)
        txt.grid(row=n_row, column=n_col, sticky="nsew", padx=2, pady=2, columnspan=col_span)
        txt.insert(END, "")
        self.myStyle[name] = txt

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
        log('ip clicked')
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
        except:
            print('failed to load value')
        
        
    def updatePitch(self, event):
        chars = event.widget.get()
        try:
            val = float(chars.strip())
            print('new pitch is %0.2f'%val)
            desiredPitch = val
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
        except:
            print('failed to load value')
        

    def update_squal(self, event):
        chars = event.widget.get("1.0", "end-1c")
        val = chars.replace('\n', '').strip()
        self.squal_val = val

    def scan_ips(self):
        log('starting IP scan')
        ip_list = [200, 206, 213, 214, 215, 216, 217, 218, 219]

        for ip_item in ip_list:
            ip_add = "192.168.1.{}".format(ip_item)
            command = ['fping', '-c', '1', '-r', '1', '-t', '300ms', '-q', ip_add, ]
            response = subprocess.call(command)
            if response == 0:
                log('scan detected valid ip! {}'.format(ip_add))
                self.myStyle["ip_textbox"].delete('1.0', END)
                self.myStyle['ip_textbox'].insert(END, ip_add)
                return
            log('no response from {}'.format(ip_add))

    def update_ip(self, event):
        chars = event.widget.get("1.0", "end-1c")
        self.hostname = chars.replace('\n', '').strip()
        
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
        submit_btn.grid(row=row, column=col, columnspan=width, rowspan=height, pady=15, padx=7, ipadx=100,
                        sticky="nsew")
        submit_btn.config(background=bg, activebackground=bg)
        self.myStyle['control_bg'] = submit_btn

    def image_clicked(self, event):
        print('aaaa')
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
            log(err)

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
            log(err)

    def update_image(self, img):
        log('update image')
        self.img = Image.open(io.BytesIO(img)) ## jpg stream
        if self.should_rotate_180():
            self.img = ImageTk.PhotoImage(self.img.resize((572, 429), Image.NONE).rotate(180))
        else:
            self.img = ImageTk.PhotoImage(self.img.resize((600, 450), Image.NONE))

        self.myStyle['disp_image'].configure(image=self.img)
        self.myStyle['disp_image'].image = self.img

    def should_rotate_180(self):
        if self.check_inverted_cam.get() == 0:
            return True
        return False

    def send_fa_params(self):
        oper_cmd = '0'
        z_ret = '0'
        of_ret = '0'
        w_ret = '0'

        if self.check_oper_cmd.get() == 0:
            oper_cmd = '1'
        if self.check_z_ret.get() == 0:
            z_ret = '1'
        if self.check_of_ret.get() == 0:
            of_ret = '1'
        if self.check_w_ret.get() == 0:
            w_ret = '1'

        self.logic.send_params(oper=oper_cmd, z_ret=z_ret, of_ret=of_ret, w_ret=w_ret,
                               velocity=self.nominal_velocity_val, timeout=self.timeout_val,
                               squal=self.squal_val, control1=0, height=self.height_val)

    def set_default_image(self):
        path = "Drone.jpg"
        self.img = Image.open(path)
        self.img = ImageTk.PhotoImage(self.img.resize((600, 450), Image.NONE))
        self.myStyle['disp_image'].configure(image=self.img)
        self.myStyle['disp_image'].image = self.img

    def make_image(self, name, col, row, width, height, char_width, char_height):
        path = "rov.jpg"
        self.img = Image.open(path)
        self.img = ImageTk.PhotoImage(self.img.resize((char_width, char_height), Image.NONE))
        lbl = Label(self.parent, image=self.img, width=char_width, height=char_height, borderwidth=2,
                    highlightbackground="white")
        lbl.image = self.img
        lbl.grid(row=row, column=col, columnspan=width, rowspan=height, pady=5, padx=5, sticky="nsew")
        self.myStyle[name] = lbl

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

    def create_soft_button(self, name, display_text, n_col, n_row, callback, sticky="center", width=10):
        button_name = "{}_button".format(name)
        self.myStyle[button_name] = Button(self.parent, text=display_text, command=callback, width=width,
                                        activebackground=self.myStyle['activeSoftButtonBg'])
        if 'center' not in sticky:
            self.myStyle[button_name].grid(column=n_col, row=n_row, sticky=sticky)
        else:
            self.myStyle[button_name].grid(column=n_col, row=n_row)
        self.myStyle[button_name].config(background=self.myStyle['buttonBgSoft'], foreground=self.myStyle['buttonFgSoft'],
                                      font=self.TFont)

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

    def led_moderate(self):
        pass

    def led_high(self):
        pass

    def led_extreme(self):
        pass

    def clear_gui(self):
        self.current_led_display = None
        # todo: nirge
        self.clear_version()
        self.long_ping = 0
        self.short_ping = 0
        self.delay_text = 'NaN'
        self.myStyle["rssi_text"]['text'] = 'n/a'
        self.myStyle['seq_text']['text'] = 'n/a'
        self.myStyle['ffk_text']['text'] = 'n/a'
        self.myStyle['fa_text']['text'] = 'n/a'
        # self.myStyle['arm_text']['text'] = 'n/a'
        self.myStyle['impub_text']['text'] = 'n/a'
        #self.myStyle['light_text']['text'] = 'n/a'
        self.myStyle['battery_text']['text'] = 'n/a'
        self.myStyle['cpu_text']['text'] = 'n/a'
        #self.myStyle['last_cmd_text']['text'] = 'n/a'
        self.myStyle['log_textbox'].config(state=NORMAL)
        self.myStyle["log_textbox"].delete('1.0', END)
        self.myStyle['log_textbox'].config(state=DISABLED)
        self.set_default_image()

        self.logic.clear()

    def led_auto(self):
        pass

    def cmd_disarm(self):
        self.update_button_active_command("disarm__button")
        pass

    def cmd_arm(self):
        self.update_button_active_command("arm__button")
        pass

    def cmd_takeoff(self):
        if self.check_enable_takeoff.get() == 0:
            self.update_button_active_command("takeoff__button")
            log("takeoff issued")
            pass
        else:
            log("takeoff rejected!")
            self.add_log_file('takeoff rejected, check Enable Fly before Takeoff')

    def cmd_hold(self):
        self.update_button_active_command("manual__button")
        

    def cmd_land(self):
        self.update_button_active_command("land__button")
        

    def cmd_autonomous(self):
        self.update_button_active_command("cruise_and_return__button")
        

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


    def make_widgets(self):
        propertyCol = 1
        commandCol = 3
        controlCol = 5
        
        row_index = 0
        self.create_main_col_row_labels()
        row_index += 1
        self.create_label_header(name="header", display_text1="Property", display_text2="Status",
                                 display_text3="Commands", display_text4="Control",
                                 display_text5=" Manual control ", n_col=1,
                                 n_row=row_index)
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
        self.create_text_box(name="rollCmd", label_text="dRoll:", display_text="[deg]", n_col=commandCol, n_row=row_index, textbox_width=5)
        self.myStyle['rollCmd_textbox'].bind("<Key-Return>", self.updateRoll)
        row_index += 1
        self.create_label_pair(name="rtYaw", display_text="Yaw:", n_col=propertyCol, n_row=row_index)
        self.create_text_box(name="yawCmd", label_text="dYaw:", display_text="[deg]", n_col=commandCol, n_row=row_index, textbox_width=5)
        self.myStyle['yawCmd_textbox'].bind("<Key-Return>", self.updateYaw)
        row_index += 1
        self.create_label_pair(name="battery", display_text="BATT:", n_col=propertyCol, n_row=row_index)
        pidRow = row_index + 1
        self.create_checkbox_button("showDepth", "depth control", propertyCol, pidRow, self.checkDepthControl, anchor='w')
        pidRow += 1
        self.create_checkbox_button("showPitch", "pitch control", propertyCol, pidRow, self.checkPitchControl, anchor='w')
        pidRow += 1
        self.create_checkbox_button("showRoll", "roll control", propertyCol, pidRow, self.checkRollControl, anchor='w')
        pidRow += 1
        self.create_checkbox_button("showYaw", "yaw control", propertyCol, pidRow, self.checkYawControl, anchor='w')
        pidRow += 1
        
        self.create_checkbox_button("depthHold", "Depth hold", commandCol, row_index, self.checkDepthHold, anchor='w')
        row_index += 1
        self.create_checkbox_button("attHold", "Attitude hold", commandCol, row_index, self.checkAttHold, anchor='w')
        
        row_index += 2
        self.create_button("getRecords", "Fetch Recs", commandCol, row_index, self.download_dir)
        
        
        #row_index += 5
        #self.create_label_buffer(name="buffer_before_buttons", n_row=row_index, n_col=100)
        #row_index += 1
        row_btn_idx = 2
        self.create_button("runRemote", "run ROV", controlCol, row_btn_idx, self.cmd_arm)
        row_btn_idx += 1
        self.create_button("arm_", "ARM", controlCol, row_btn_idx, self.cmd_arm)
        row_btn_idx += 1
        self.create_button("disarm_", "DISARM", controlCol, row_btn_idx, self.cmd_disarm)
        row_btn_idx += 1        
        self.create_button("ledsUp", "Inc. Lights", controlCol, row_btn_idx, self.send_fa_params)
        row_btn_idx += 1
        self.create_button("ledsDown", "Dec. Lights", controlCol, row_btn_idx, self.get_records)
        row_btn_idx += 1
        self.create_button("focusFar", "Focus far", controlCol, row_btn_idx, self.cmd_takeoff)
        row_btn_idx += 1
        self.create_button("focusNear", "Focus near", controlCol, row_btn_idx, self.cmd_png_map)
        row_btn_idx += 1
        self.create_button("killRemote", "kill ROV", controlCol, row_btn_idx, self.cmd_arm)
        row_btn_idx += 1
        self.create_button("rebootRemote", "reboot ROV", controlCol, row_btn_idx, self.cmd_arm)
        row_btn_idx += 1
        #set video window
        self.make_image(name='disp_image', col=1, row=row_btn_idx, width=10, height=14, char_width=800, char_height=600)

        
        
        control_start_col = 12
        
        self.make_square(col=control_start_col, row=2, width=7, height=5, bg='gray90')
        self.create_control_button("goRight", "❱❱", control_start_col + 5, 5, self.turn_right)
        self.create_control_button("goLeft", "❰❰", control_start_col + 1, 5, self.turn_left)
        self.create_control_button("goForward", "⟰", control_start_col + 3, 3, self.go_forwards)
        self.create_control_button("goBackwords", "⟱", control_start_col + 3, 5, self.go_backwards)
        
        self.create_control_button("yawLeft", "Yaw left➚", control_start_col + 1, 3, self.go_up)
        self.create_control_button("yawRight", "➘ Yaw right", control_start_col + 5, 3, self.go_down)
        
        self.create_control_button("deeper", "Deeper ⟱", control_start_col + 1, 4, self.go_forwards)
        self.create_control_button("shallower", "Shallower ⟰", control_start_col + 5, 4, self.go_backwards)
        

    def add_log_file(self, data):
        self.myStyle['log_textbox'].config(state=NORMAL)
        self.myStyle['log_textbox'].insert(END, data)
        self.myStyle['log_textbox'].insert(END, "\n")
        self.myStyle['log_textbox'].see(END)
        time.sleep(0.1)
        self.myStyle['log_textbox'].config(state=DISABLED)

        if 'rosbag:' in data:
            self.last_rosbag = data

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

    def download_dir(self):
        self.logic.get_log_directories()

    def update_transport(self):
        if self.short_ping < 75:
            if self.long_ping == 0:
                ping_status = '0%'
                color = 'red'
            else:
                color = 'blue'
                ping_status = '{:.0f}% ext'.format(self.long_ping)
        else:
            color = 'green'
            ping_status = '{:.0f}% fast'.format(self.short_ping)

        self.myStyle['transport_text']['text'] = '{}/{}s'.format(ping_status, self.delay_text)
        self.myStyle['transport_text'].config(foreground=color)
        self.delay_text = 'NaN'

        if self.update_ping_window and self.ping_window is not None:
            self.ping_window.update_ping_values(self.short_ping, self.long_ping, self.rssi_str, self.rssi_clar)
        self.short_ping = 0
        self.long_ping = 0
        self.rssi_str = 0
        self.rssi_clar = 0

    def update_long_ping_percentage(self, pings_ok, total_pings):
        try:
            self.long_ping = 100 * pings_ok / total_pings
        except Exception as err:
            log("Exception during ping update: {}".format(err))

    def update_flight_timer(self, data):
        try:
            self.myStyle["flight_time_text"]['text'] = "{:.2f} s".format(data)
        except Exception:
            pass

    def update_rssi(self, sig, qual):
        self.myStyle["rssi_text"]['text'] = "{} ~ {}".format(sig, qual)
        try:
            self.rssi_str = -float(sig)
        except Exception:
            self.rssi_str = 0.0
        try:
            rssi_clr_arr = qual.split('/')
            self.rssi_clar = 100 * float(rssi_clr_arr[0]) / float(rssi_clr_arr[1])
        except Exception:
            self.rssi_clar = 0.0

    def update_delay_time(self, data):
        try:
            self.delay_text = "{:.2f}".format(data)
        except Exception:
            self.delay_text = "NaN"

    def update_short_ping_percentage(self, pings_ok, total_pings):
        try:
            self.short_ping = 100 * pings_ok / total_pings
        except Exception as err:
            log("Exception during ping update: {}".format(err))

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
            log("can't set squal value")
            log(err)
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

    def update_wret_display_status(self, txt):
        try:
            if int(txt) > 0:
                txt = 'T'
            else:
                txt = 'F'
        finally:
            self.myStyle['wreject_d_text']['text'] = txt

    def update_ffk_status(self, txt):
        self.myStyle['ffk_text']['text'] = txt

    def update_last_cmd(self, txt):
        # self.myStyle['last_cmd_text']['text'] = "CMD: {}".format(txt)

        if txt is self.last_cmd_from_cf:
            return
        try:
            switcher = {"Disarm": "disarm__button",
                        "Arm": "arm__button",
                        "Takeoff": "takeoff__button",
                        "Land": "land__button",
                        "ESTOP": None,
                        "CHNG_AUTO": None,
                        "PnG Vis": None,
                        "SET HEIGHT": None,
                        "SET PARAM": None,
                        "RECOVER": None,
                        "FAIL": None,
                        "Hold Pos": "manual__button",
                        "Cruise&Ret": "cruise_and_return__button",
                        "FLY": None,
                        "PnG Map": 'png_map__button',
                        "Phase1 Assist": None
                        }
            if self.last_cmd_from_cf == 'Change Pos':
                bg = 'LightSteelBlue'
                self.myStyle['control_bg'].config(background=bg, activebackground=bg)
            elif switcher[self.last_cmd_from_cf] is not None:
                self.myStyle[switcher[self.last_cmd_from_cf]].config(background=self.myStyle['buttonBg'])
            self.last_cmd_from_cf = txt
            if switcher[self.last_cmd_from_cf] is not None:
                self.myStyle[switcher[self.last_cmd_from_cf]].config(background=self.myStyle['activeDisplayButtonBg'])

        except Exception as err:
            try:
                if txt == "Change Pos":
                    bg = 'pink'
                    self.myStyle['control_bg'].config(background=bg, activebackground=bg)
                else:
                    log("error with button update cmd, updating to {} ".format(txt))
                    log(err)
            except Exception as err2:
                log("error with button update cmd, updating to {} ".format(txt))
                log(err2)
        self.last_cmd_from_cf = txt

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


    def update_seq_num(self, txt, in_messages, out_messages):
        __str = '{} [{}/{}]'.format(txt, in_messages, out_messages)
        self.myStyle['seq_text']['text'] = __str

    def update_fa_status(self, txt):
        self.myStyle['fa_text']['text'] = txt

    def update_arm_status(self, txt):
        # self.myStyle['arm_text']['text'] = txt
        pass

    def update_impub_status(self, txt):
        self.myStyle['impub_text']['text'] = txt
        color = 'black'
        if 'PUBLISHING' in txt:
            color = 'green'
        elif 'FAULTY' in txt:
            color = 'red'

        self.myStyle['impub_text'].config(foreground=color)

    def light_status(self, txt):
        if txt == self.current_led_display:
            return
        self.current_led_display = txt
        # self.myStyle['light_text']['text'] = txt

        switcher = {
            "Off": "front_led_off__button",
            "Low": "front_led_low__button",
            "Medium": "front_led_on__button",
            "High": "front_led_high__button",
            "Extreme": "front_led_extreme__button",
        }

        self.myStyle[switcher['Off']].config(background=self.myStyle['buttonBg'])
        self.myStyle[switcher['Low']].config(background=self.myStyle['buttonBg'])
        self.myStyle[switcher['Medium']].config(background=self.myStyle['buttonBg'])
        self.myStyle[switcher['High']].config(background=self.myStyle['buttonBg'])
        self.myStyle[switcher['Extreme']].config(background=self.myStyle['buttonBg'])

        if txt in switcher:
            val = switcher.get(txt, "Invalid month")
            self.myStyle[val].config(background=self.myStyle['btnHighlight'])

    def battery_status(self, txt):
        self.myStyle['battery_text']['text'] = '{}'.format(txt)

    def cpu_status(self, txt):
        self.myStyle['cpu_text']['text'] = '{}%'.format(txt)

    def looking_state(self, txt):
        self.add_log_file("looking {}".format(txt))

if __name__=='__main__':
    root = Tk()
    #root.grid_columnconfigure(0, weight=1)
    #root.grid_rowconfigure(0, weight=1)
    #root.resizable(True, False)
    guiInstance = rovViewerWindow(root)
    root.bind("<Configure>", guiInstance.resize)
    root.mainloop()
