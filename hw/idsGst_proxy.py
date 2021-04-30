#!/usr/bin/env python

import sys
import time
import numpy as np
import traceback
from ipdb import set_trace as st
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

sys.path.append('../')
sys.path.append('../utils')

import zmq_topics
import zmq_wrapper as utils
import pickle 

socket_pub = utils.publisher(zmq_topics.topic_camera_port)


def get_dims(pipeline,name='dec'):
    pad = pipeline.get_by_name(name).pads[0]
    caps=pad.get_current_caps()
    struct=caps.get_structure(0)
    h=struct.get_int('height')[1]
    w=struct.get_int('width')[1]
    if h==0:
        print('Error: dim h is 0')
        return None
    return (h,w,3)

def get_image_from_sink(sink,dims):
    sample=sink.emit('pull-sample') 
    buf=sample.get_buffer()
    mem=buf.get_all_memory()
    ret,mi=mem.map(Gst.MapFlags.READ)
    #t = (self.pipeline.clock.get_time()-self.pipeline.base_time)/1e9
    t = (sink.clock.get_time()-sink.base_time)/1e9
    image=(t,np.frombuffer(mi.data,'uint8').reshape(dims))
    mi.memory.unmap(mi)
    return image
     


class Reader:   
    def on_new_buffer(self,sink):
        if self.dims is None:
           self.dims=get_dims(self.pipeline)
        self.image=get_image_from_sink(sink,self.dims)
        return Gst.FlowReturn.OK

    def __init__(self,fname):
        Gst.init(None)
        #pipe = 'filesrc location=out.mkv ! matroskademux ! avdec_h265 ! videoconvert ! video/x-raw,format=RGB ! appsink name=sink'
        pipe = 'filesrc location={} ! matroskademux ! decodebin name=dec ! videoconvert ! video/x-raw,format=RGB ! appsink name=sink'.format(fname)
        pipeline = Gst.parse_launch(pipe)

        sink=pipeline.get_by_name('sink')
        sink.set_property("max-buffers",2)
        sink.set_property("emit-signals", True)
        sink.connect("new-sample", self.on_new_buffer) 
        pipeline.set_state(Gst.State.READY)
        self.pipeline=pipeline
        self.image=None
        self.pipeline.set_state(Gst.State.PLAYING)
        self.dims=None

    def get_next(self):
        bus = self.pipeline.get_bus()
        while self.image is None:
            message = bus.timed_pop_filtered(3*Gst.MSECOND,Gst.MessageType.ANY)
            if message:
                t = message.type
                if t == Gst.MessageType.EOS:
                    sys.stdout.write("End-of-stream\n")
                    break
                elif t == Gst.MessageType.ERROR:
                    err, debug = message.parse_error()
                    sys.stderr.write("Error: %s: %s\n" % (err, debug))
                    break
        # self.pipeline.set_state(Gst.State.PAUSED)
        ret=self.image
        self.image=None
        return ret
    def pause(self):
        self.pipeline.set_state(Gst.State.PAUSED) 
    def play(self):
        self.pipeline.set_state(Gst.State.PLAYING)

    def __del__(self):    # cleanup
        self.pipeline.set_state(Gst.State.NULL)


class Writer:
    def __init__(self, fname=None,ip='127.0.0.1',port=6666):
        Gst.init(None)
        # pipe = 'videotestsrc is-live=true horizontal-speed=5 name=src ! x265enc bitrate=500 ! h265parse ! matroskamux ! filesink location=out.mkv'
        # pipe = 'videotestsrc is-live=true horizontal-speed=5 name=src '
        #pipe = 'v4l2src device=/dev/video2 name=src ! video/x-raw,format=YUY2,width=640,height=480 ' 
        enc = '264' 
        bitrate = 10*1024*1024  # 1500 #bytes
        mkvBitrate = 5*1024*1024  # 1500 #bytes
        nvidia = True

        saveMKV = False
        if fname is not None:
            saveMKV = True 
        sendUdp = False
        if nvidia:
            encline1='! omxh{0}enc control-rate=2 bitrate={1} ! video/x-h{0}, stream-format=(string)avc '.format(enc,mkvBitrate)
            encline2='! omxh{0}enc control-rate=2 bitrate={1} ! video/x-h{0}, stream-format=(string)byte-stream '.format(enc,bitrate)
            #pipe = 'v4l2src device=/dev/video2 name=src ! video/x-raw,format=YUY2,width=640,height=480 '
            pipe = 'idsueyesrc config-file="./ids.ini" name=src '
            pipe += '! tee name=t ! queue ! '
            pipe += 'videoconvert ! video/x-raw,format=RGB ! appsink name=sink '
            
            if saveMKV:
                print('save mkv')
                pipe += 't. ! queue ! '

                pipe += 'videoconvert ! video/x-raw,format=I420 '
                pipe += encline1
                pipe += '! h{0}parse ! matroskamux name=dec ! filesink location={1} sync=false '.format(enc, fname)
            #pipe += '! fakesink sync=false '.format(enc)
            #pipe += '! filesink location=out.h{} '.format(enc)
            #pipe += '! filesink location=out.h{} '.format(enc)
            if sendUdp:
                print('send udp')
                pipe += 't. ! queue ! '
                pipe += 'videoconvert ! video/x-raw,format=I420 '
                pipe += encline2
                pipe += '! rtph{}pay ! udpsink port={} host={} sync=false'.format(enc,port,ip)
        
        else:
            encline='! x{}enc tune=zerolatency  bitrate={} '.format(enc,bitrate)
            pipe = 'v4l2src device=/dev/video2 name=src ! video/x-raw,format=YUY2,width=640,height=480 '
            pipe += '! tee name=tt ! queue ! '
            pipe += 'videoconvert ! video/x-raw,format=RGB ! appsink name=sink '
            pipe += 'tt. ! queue ! '

            pipe += 'videoconvert ! video/x-raw,format=I420 '
            pipe += encline
            pipe += '! tee name=t ! queue ! '
            pipe += 'h{}parse ! matroskamux name=dec ! filesink location={} sync=false '.format(enc,fname)
            pipe += 't. ! queue ! '
            pipe += 'rtph{}pay ! udpsink port={} host={} sync=false'.format(enc,port,ip)

        self.pipeline = Gst.parse_launch(pipe)
       

        sink=self.pipeline.get_by_name('sink')
        sink.set_property("max-buffers",2)
        sink.set_property("emit-signals", True)
        sink.connect("new-sample", self.on_new_buffer) 
        self.source = self.pipeline.get_by_name('src')
        
        self.pipeline.set_state(Gst.State.READY)
        self.pipeline.set_state(Gst.State.PLAYING)
        
        self.dims=None
        self.image=None
    
    def on_new_buffer(self,sink):
        try:
            if self.dims is None:
                self.dims=get_dims(self.pipeline, 'src')
            self.image=get_image_from_sink(sink,self.dims)
        except Exception as e:
            print('ERROR',traceback.format_exc())
        return Gst.FlowReturn.OK

     
    def get_next(self):
        pipeline=self.pipeline
        bus = pipeline.get_bus()
        message = bus.timed_pop_filtered(5*Gst.MSECOND,Gst.MessageType.ANY)
         
        stream_time=(self.source.clock.get_internal_time()-self.source.base_time)/1e9
        if message:
            t = message.type
            if t == Gst.MessageType.EOS:
                sys.stdout.write("End-of-stream\n")
            elif t == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                sys.stderr.write("Error: %s: %s\n" % (err, debug))
        ret={'ts':stream_time}
        if self.image is not None:
            ret['image']=self.image
            self.image=None
        return ret 
    
    def __del__(self):    # cleanup
        self.pipeline.set_state(Gst.State.NULL)
 

if __name__ == '__main__':
    import argparse
    import cv2
    parser = argparse.ArgumentParser()
    parser.add_argument("--reader", help="is reader",default=False,action='store_true')
    parser.add_argument("--ip", help="destenation ip",default='127.0.0.1')
    parser.add_argument("--port", help="destenation ip",default=6666,type=int)
    args = parser.parse_args()
    if args.reader:
        rd = Reader('out.mkv')
        cnt=0
        while 1:
            t,img = rd.get_next()
            print('t=',t)
            if img is None:
                break
            cv2.imshow('img',img)
            if cnt==10:
                rd.pause()
                time.sleep(5)
                rd.play()
            k=cv2.waitKey(1)
            if k%256==ord('q'):
                break
            cnt+=1
    else:
        wt = Writer(None, ip=args.ip,port=args.port)
        tic=time.time()
        dflag=True
        cnt = 0.0
        ticf = time.time()
        
        doShow = False
        winName = 'input'
           
        frameCnt = 0
        while True:
            #time.sleep(0.0001)
            '''
            if dflag and time.time()-tic>15:
                print('write dot file if GST_DEBUG_DUMP_DOT_DIR env exist')
                #run with GST_DEBUG_DUMP_DOT_DIR=dumppath
                Gst.debug_bin_to_dot_file(wt.pipeline,Gst.DebugGraphDetails.ALL,'out')
                dflag=False
            
            '''
            ret = wt.get_next()
            if 'image' in ret:
                cnt += 1
                frameCnt += 1
                if time.time() - ticf >= 3:
                    fps = cnt / (time.time() - ticf)
                    print('fps: %0.2f, imshape: [%d,%d]'%(fps,ret['image'][1].shape[1], ret['image'][1].shape[0] ))
                    ticf = time.time()
                    cnt = 0.0
                if doShow:
                    cv2.namedWindow(winName, 0)
                    cv2.imshow(winName, ret['image'][1])
                    key = cv2.waitKey(1)
                    if key&0xff == 27:
                        break
                
                imShape = ret['image'][1].shape
                imRaw = np.frombuffer(ret['image'][1], dtype='uint8').reshape(imShape)
                
                QRes = cv2.resize(imRaw, (imShape[1]//2, imShape[0]//2))
                
                socket_pub.send_multipart([zmq_topics.topic_stereo_camera,
                                        pickle.dumps((frameCnt, ret['image'][1].shape, ret['ts'])), QRes.tobytes(),
                                            ret['image'][1].tobytes()])
                socket_pub.send_multipart( [zmq_topics.topic_stereo_camera_ts, 
                                            pickle.dumps( (frameCnt, ret['ts']) )] )
                #print('got image',ret['image'][0],ret['image'][1].shape,time.time()-tic)
                
