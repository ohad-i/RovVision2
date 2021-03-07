### PIDS
ds=0.45
'''
ds=0.1
'P':2.5*ds,
'I':0.001*ds,
'D':5*ds,
'''
depth_pid={
        'P':2.5*ds,
        'I':0.01*ds,
        'D':1.5*ds,
        'limit':0.3,
        'step_limit':0.05,
        'i_limit':0.01,
        'FF':0,
        'angle_deg_type':False,
        'initial_i':0,
        'func_in_err':None}

ys=0.03
#ys=0.00
yaw_pid={
        'P':0.3*ys,
        'I':0.0001*ys,
        'D':0.15*ys,
        'limit':0.5,
        'step_limit':0.05,
        'i_limit':0.1,
        'FF':0,
        'angle_deg_type':True,
        'initial_i':0,
        'func_in_err':None}

#rs=0.03
##rs=0.001
rs=0.5
roll_pid={
        'P':0.006*rs,
        'I':0.0005*rs,
        'D':0.002*rs,
        'limit':0.3,
        'step_limit':0.5,
        'i_limit':0.4,
        'FF':0,
        'angle_deg_type':True,
        'initial_i':0,
        'func_in_err':None}

ps=0.25
#ps=0.000
pitch_pid={
        'P':0.05*ps,
        'I':0.001*ps,
        'D':0.01*ps,
        'limit':0.5,
        'step_limit':0.5,
        'i_limit':0.4,
        'FF':0,
        'angle_deg_type':True,
        'initial_i':0,
        'func_in_err':None}

#if set to true always try to mantain 0 roll
roll_target_0 = True

sc=0.00
pos_pid_x={
        'P':2.5 * sc ,
        'I':0.001 * sc ,
        'D':5 * sc ,
        'limit':0.6,
        'step_limit':0.05,
        'i_limit':0.01,
        'FF':0,
        'angle_deg_type':True,
        'initial_i':0,
        'func_in_err':None}
sc=0.0
pos_pid_y={
        'P':2.5 * sc ,
        'I':0.001 * sc ,
        'D':5 * sc ,
        'limit':0.6,
        'step_limit':0.05,
        'i_limit':0.01,
        'FF':0,
        'angle_deg_type':True,
        'initial_i':0,
        'func_in_err':None}

sc=0.00
pos_pid_z={
        'P':2.5 * sc ,
        'I':0.001 * sc ,
        'D':5 * sc ,
        'limit':0.6,
        'step_limit':0.05,
        'i_limit':0.01,
        'FF':0,
        'angle_deg_type':True,
        'initial_i':0,
        'func_in_err':None}





pos_pids=[pos_pid_x, pos_pid_y, pos_pid_z]
