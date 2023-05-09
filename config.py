#cameras info
import os
rov_type = int(os.environ.get('ROV_TYPE',1))
camera_setup='stereo' #'mono'

if rov_type==1:
    cam_resx,cam_resy=1920,1200
    reverse_camera_order=True
if rov_type==2:
    cam_resx,cam_resy=1280,1024
    reverse_camera_order=False
if rov_type==3:
    cam_resx,cam_resy=1920,1200#1080 todo change to 1080 for bluerobotics cameras
    camera_setup='mono' #'mono'
if rov_type==4:
    cam_resx,cam_resy=1936,1216#1080 todo change to 1080 for bluerobotics cameras
    camera_setup='mono' #'mono'


cam_res_rgbx, cam_res_rgby = cam_resx//2, cam_resy//2
fps=10

groundIp = "192.168.3.11"
udpPort = 33221

toROVudpPort   = fromGroundUdpPort = 55661
fromROVudpPort = toGroundUdpPort   = 55662


#gstreamer
gst_ports=[6760,6761]
gst_bitrate=1024*3
#gst_bitrate=256
gst_speed_preset=1

#tracker type
#tracker = 'local'
tracker = 'rope'

joy_deadband=0.05

thruster_limit=0.5

viewer_blacks=(50,100)

initPitch = 0 #deg

if __name__=='__main__':
    #for bash scripts to get state
    import sys
    print(globals()[sys.argv[1]],end='')
