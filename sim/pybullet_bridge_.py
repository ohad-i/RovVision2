#!/usr/bin/env python
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import sys,os,time
import pybullet as pb
import pybullet_data
sys.path.append('..')
sys.path.append('../utils')
sys.path.append('unreal_proxy')
import zmq
import struct
import cv2,os
import numpy as np
import pickle
import zmq_wrapper as utils
import ue4_zmq_topics
import zmq_topics
import config
import dill
from numpy import sin,cos

zmq_sub=utils.subscribe([zmq_topics.topic_thrusters_comand],zmq_topics.topic_thrusters_comand_port)
zmq_pub=utils.publisher(zmq_topics.topic_camera_port)
pub_imu = utils.publisher(zmq_topics.topic_imu_port)
pub_depth = utils.publisher(zmq_topics.topic_depth_port)

pub_sonar = utils.publisher(zmq_topics.topic_sonar_port)
pub_motors = utils.publisher(zmq_topics.topic_motors_output_port)

#cvshow=True
cvshow=False
test=1

dill.settings['recurse'] = True
lamb=dill.load(open('lambda.pkl','rb'))
current_command=[0 for _ in range(8)] # 8 thrusters
dt=1/60.0
#pybullet init
#render = pb.GUI #pb.DIRECT
render = pb.DIRECT
#physicsClient = pb.connect(pb.GUI)#or p.DIRECT for non-graphical version
physicsClient = pb.connect(render, options='--background_color_blue=1.0')#or p.DIRECT for non-graphical version
pb.setAdditionalSearchPath(pybullet_data.getDataPath()) #optionally
pb.setGravity(0,0,-0)
print('start...')
planeId = pb.loadURDF("plane.urdf")
pb.resetBasePositionAndOrientation(planeId,(0,0,-20),pb.getQuaternionFromEuler((0,0,0,)))
import random
robj=[]
def set_random_objects():
    random.seed(0)
    for _ in range(400):
        urdf = "random_urdfs/{0:03d}/{0:03d}.urdf".format(random.randint(1,1000)) 
        x = (random.random()-0.5)*5
        y = (random.random()-0.5)*5
        z = (random.random())*-10
        obj = pb.loadURDF(urdf,basePosition=[x,y,z],globalScaling=3,baseOrientation=[random.random() for _ in range(4)])
        robj.append(obj)
        print('---loading--',urdf,x,y)
        #pb.resetBasePositionAndOrientation(obj,(x,y,z),pb.getQuaternionFromEuler((0,0,0,)))

set_random_objects()
keep_running = True

def getrov():

    shift = [0, -0.0, 0]
    meshScale = np.array([0.01, 0.01, 0.01])*0.3
    vfo=pb.getQuaternionFromEuler(np.deg2rad([90, 0, 0]))
    visualShapeId = pb.createVisualShape(shapeType=pb.GEOM_MESH,
                                        fileName="br1.obj",
                                        rgbaColor=[1, 0, 0, 1],
                                        specularColor=[0.4, .4, 0],
                                        visualFramePosition=[0,0,0],
                                        visualFrameOrientation=vfo,
                                        meshScale=meshScale)#set the center of mass frame (loadURDF sets base link frame) startPos/Ornp.resetBasePositionAndOrientation(boxId, startPos, startOrientation)
    boxId=pb.createMultiBody(baseMass=1,
                          baseInertialFramePosition=[0, 0, 0],
                          baseCollisionShapeIndex=1,
                          baseVisualShapeIndex=visualShapeId,
                          basePosition=[0,0,0],
                          useMaximalCoordinates=True)
    return boxId

def get_next_state(curr_q,curr_u,control,dt,lamb):
    forces=control
    #print('forces = ',forces)
    u_dot_f=lamb(curr_q,curr_u,*forces).flatten()
    next_q=curr_q+curr_u*dt
    next_u=curr_u+u_dot_f*dt
    return next_q,next_u

def translateM(M,dx,dy,dz):
    T = np.zeros((4,4),dtype=float)
    T[np.diag_indices(4)]=1.0
    T[0,3]=dx
    T[1,3]=dy
    T[2,3]=dz
    #T[3,0]=dx
    #T[3,1]=dy
    #T[3,2]=dz
    VM = T.T @ np.array(M).reshape((4,4))
    #VM =  np.array(M).reshape((4,4)) @ T.T
    VM = VM.flatten().tolist()
    return VM

def resize(img,factor):
    h,w = img.shape[:2]
    return cv2.resize(img,(int(w*factor),int(h*factor)))

def main():
    cnt=0
    frame_cnt=0
    frame_ratio=3 # for 6 sim cycles 1 video frame
    resize_fact=0.5
    mono=True
    imgl = None
    curr_q = np.zeros(6)
    curr_u = np.zeros(6)
    current_command = np.zeros(8)

    if render==pb.GUI:
        boxId = getrov()
    
    simCamState = {'expVal':-1, 'aGain':False, 'aExp':False}
    
    fpsCnt = 0
    fpsTic = time.time()
    

    while keep_running:
        tic_cycle = time.time()
        while len(zmq.select([zmq_sub],[],[],0.001)[0])>0:
            data = zmq_sub.recv_multipart()
            topic=data[0]
            if topic==zmq_topics.topic_thrusters_comand:
                _,current_command=pickle.loads(data[1])
                current_command=[i*1.3 for i in current_command]
                
                motorsPwm = [e * 400 for e in current_command]

                pub_motors.send_multipart( [zmq_topics.topic_motors_output, pickle.dumps( {'ts':time.time(), 'motors':motorsPwm} )])
        next_q,next_u=get_next_state(curr_q,curr_u,current_command,dt,lamb)
        next_q,next_u=next_q.flatten(),next_u.flatten()
        curr_q,curr_u=next_q,next_u

        ps={}
        #print('dsim {:4.2f} {:4.2f} {:4.2f} {:3.1f} {:3.1f} {:3.1f}'.format(*curr_q),current_command)
        ps['posx'],ps['posy'],ps['posz']=curr_q[:3]
        yaw,roll,pitch = curr_q[3:]
        ps['yaw'],ps['roll'],ps['pitch']=np.rad2deg(curr_q[3:])
        #ps['yaw']=-ps['yaw']
        #ps['posy']=-ps['posy']
    #ps['pitch']=-ps['pitch'] 
        #ps['roll']=-ps['roll']
        #pub_pos_sim.send_multipart([xzmq_topics.topic_sitl_position_report,pickle.dumps((time.time(),curr_q))])
        zmq_pub.send_multipart([ue4_zmq_topics.topic_sitl_position_report,pickle.dumps(ps)])
        px,py,pz=ps['posx'],ps['posy'],ps['posz']

        if cnt%frame_ratio==0:
            #print('====',yaw,pitch,roll)
            #first camera
            yawd,pitchd,rolld=ps['yaw'],ps['roll'],ps['pitch']
            VM = pb.computeViewMatrixFromYawPitchRoll((py,px,-pz),1.0,-yawd+00,pitchd,rolld,2)
            #VM=translateM(VM,0.4,-0.1,0) 
            if not mono:
                VM=translateM(VM,0.2,-1.1,0.0)#left camera 0.2 for left 
            
            PM = pb.computeProjectionMatrixFOV(fov=60.0,aspect=1.0,nearVal=0.1,farVal=1000)
            w = int(config.cam_res_rgbx*resize_fact)
            h = int(config.cam_res_rgby*resize_fact)
            width, height, rgbImg, depthImg, segImg = pb.getCameraImage(
                width=w, 
                height=h,
                viewMatrix=VM,
                projectionMatrix=PM,renderer = pb.ER_BULLET_HARDWARE_OPENGL)
                    #get images from py bullet
            imgl=resize(rgbImg[:,:,:3],1/resize_fact)#inly interested in rgb
            #print('===',imgl.shape)

            #second camera
            if not mono:
                VM = pb.computeViewMatrixFromYawPitchRoll((px,py,-pz),1.0,-yawd,pitchd,rolld,2)
                VM=translateM(VM,-0.2,-1.1,0.0)#left camera 0.2 for left 
                PM = pb.computeProjectionMatrixFOV(fov=60.0,aspect=1.0,nearVal=0.1,farVal=1000)
                width, height, rgbImg, depthImg, segImg = pb.getCameraImage(
                    width=w, 
                    height=h,
                    viewMatrix=VM,
                    projectionMatrix=PM,renderer = pb.ER_BULLET_HARDWARE_OPENGL)
                imgr=resize(rgbImg[:,:,:3],1/resize_fact) #todo...
                
            fpsCnt += 1
            if time.time() - fpsTic >= 3:
                simFps = fpsCnt/(time.time() - fpsTic)
                print('simFPS: %0.2f'%simFps)
                fpsTic = time.time()
                fpsCnt = 0

            if cvshow:
                #if 'depth' in topic:
                #    cv2.imshow(topic,img)
                #else:
                #cv2.imshow(topic,cv2.resize(cv2.resize(img,(1920/2,1080/2)),(512,512)))
                imgls = imgl[::2,::2]
                #imgrs = imgr[::2,::2]
                cv2.imshow('l',imgls)
                #cv2.imshow('r',imgrs)
                cv2.waitKey(1)
            
            if mono:
                zmq_pub.send_multipart([zmq_topics.topic_stereo_camera,pickle.dumps([ frame_cnt, (imgl.shape[0]*2,imgl.shape[1]*2, 3 ), time.time(), simCamState, False]),imgl.tobytes(), b''])
            else:
                zmq_pub.send_multipart([zmq_topics.topic_stereo_camera,pickle.dumps([frame_cnt,(imgl.shape[0]*2,imgl.shape[1]*2, 3 ), time.time(), simCamState , False]),imgl.tobytes(), b'' , imgr.tobytes(), b'' ] )
            
            time.sleep(0.001) 
            zmq_pub.send_multipart([zmq_topics.topic_stereo_camera_ts,pickle.dumps((frame_cnt,time.time()))]) #for sync
                
            #get depth image
            if 0:
                depthImg=depthImg[::4,::4]
                min_range=depthImg.min() 
                #import pdb;pdb.set_trace()
    
                img_show=(depthImg/10.0).clip(0,255).astype('uint8')
                depthImg[depthImg>5000]=np.nan
                max_range=np.nanmax(depthImg)
                #print('sonar::',min_range,max_range)
                pub_sonar.send_multipart([zmq_topics.topic_sonar,pickle.dumps([min_range,max_range])])
    
                if cvshow:
                    cv2.imshow('depth',img_show)
                    cv2.waitKey(1)
            frame_cnt+=1

            #print('====',px,py,pz,roll,pitch,yaw)
            #pb.resetBasePositionAndOrientation(boxId,(px,py,pz),pb.getQuaternionFromEuler((roll,pitch,yaw)))
            if render==pb.GUI:
                print('ttt', time.time())
                pb.resetBasePositionAndOrientation(boxId,(py,px,-pz),pb.getQuaternionFromEuler((roll,-pitch,-yaw+np.radians(0))))
            ### test
            tic=time.time()
            imu={'ts':tic}
            imu['yaw'],imu['pitch'],imu['roll']=np.rad2deg(curr_q[3:])
            #rates from dsym notebook
            #R.ang_vel_in(R).express(R).to_matrix(R)
            #good video in https://www.youtube.com/watch?v=WZEFoWP0Tzs
            q3,q4,q5=curr_q[3:]
            u3,u4,u5=curr_u[3:]
            imu['rates']=(
                    -u3*sin(q4) + u5,
                    u3*sin(q5)*cos(q4) + u4*cos(q5),
                    u3*cos(q4)*cos(q5) - u4*sin(q5))
            pub_imu.send_multipart([zmq_topics.topic_imu,pickle.dumps(imu)])
            pub_depth.send_multipart([zmq_topics.topic_depth,pickle.dumps({'ts':tic,'depth':curr_q[2]})])


        time.sleep(0.010)
        if 0: #cnt%20==0 and imgl is not None:
            print('send...',cnt, imgl.shape)
        cnt+=1


       
if __name__ == '__main__':
    main()
