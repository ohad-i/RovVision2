#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Aug 20 13:14:12 2022

@author: ohadi
"""

import json


def reloadPIDs(tmpPIDS):
    with open(tmpPIDS) as fid:
        data = json.load(fid)
    
    pidY = data['config_pid'][0]['yaw_pid']
    pidY['P'] = pidY['P']*pidY['K']
    pidY['I'] = pidY['I']*pidY['K']
    pidY['D'] = pidY['D']*pidY['K']
    
    pidP = data['config_pid'][0]['pitch_pid']
    pidP['P'] = pidP['P']*pidP['K']
    pidP['I'] = pidP['I']*pidP['K']
    pidP['D'] = pidP['D']*pidP['K']

    pidR = data['config_pid'][0]['roll_pid']
    pidR['P'] = pidR['P']*pidR['K']
    pidR['I'] = pidR['I']*pidR['K']
    pidR['D'] = pidR['D']*pidR['K']
    
    pidDep = data['config_pid'][0]['depth_pid']
    pidDep['P'] = pidDep['P']*pidDep['K']
    pidDep['I'] = pidDep['I']*pidDep['K']
    pidDep['D'] = pidDep['D']*pidDep['K']
    
    return pidY, pidP, pidR, pidDep
