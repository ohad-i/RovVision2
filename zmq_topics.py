topic2portDict = {}

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
topic_sitl_position_report=b'position_rep'
topic_sitl_position_report_port=7755

topic2portDict[topic_sitl_position_report] = topic_sitl_position_report_port


topic_controller_port = topic_thrusters_comand_port=7788
topic_thrusters_comand=b'thruster_cmd'
topic_system_state=b'system_state'
topic_lights=b'topic_lights'
topic_focus=b'topic_set_focus_state'
topic_tracker_cmd=b'topic_tracker_start_stop_cmd'

topic2portDict[topic_thrusters_comand]  = topic_controller_port
topic2portDict[topic_system_state]      = topic_controller_port
topic2portDict[topic_lights]            = topic_controller_port
topic2portDict[topic_focus]             = topic_controller_port
topic2portDict[topic_tracker_cmd]       = topic_controller_port


thrusters_sink_port = 7787

topic_check_thrusters_comand=b'thruster_check_cmd'
topic_check_thrusters_comand_port=9005
topic2portDict[topic_check_thrusters_comand] = topic_check_thrusters_comand_port

topic_autoFocus_port = 7790
topic_autoFocus = b'autoFocus'
topic2portDict[topic_autoFocus] = topic_autoFocus_port

#cameta control topics
topic_cam_toggle_auto_exp  = b'auto_exposureCam'
topic_cam_toggle_auto_gain = b'auto_gainCam'
topic_cam_inc_exp          = b'inc_exposureCam'
topic_cam_dec_exp          = b'dec_exposureCam'
topic_cam_exp_val          = b'exp_value'
topic_cam_ctrl_port = 7791
topic2portDict[topic_cam_toggle_auto_exp]   = topic_cam_ctrl_port
topic2portDict[topic_cam_toggle_auto_gain]  = topic_cam_ctrl_port
topic2portDict[topic_cam_inc_exp]           = topic_cam_ctrl_port
topic2portDict[topic_cam_dec_exp]           = topic_cam_ctrl_port
topic2portDict[topic_cam_exp_val]           = topic_cam_ctrl_port


#topic_camera_left=b'topic_camera_left'
#topic_camera_right=b'topic_camera_right'
topic_stereo_camera    = b'topic_stereo_camera'
topic_stereo_camera_ts = b'topic_stereo_camera_ts'
topic_camera_port=7789
topic2portDict[topic_stereo_camera]     = topic_camera_port
topic2portDict[topic_stereo_camera_ts]  = topic_camera_port


topic_button = b'joy_button'
topic_axes   = b'joy_axes'
topic_hat    = b'joy_hat'
topic_joy_port=8899
topic2portDict[topic_button]    = topic_joy_port
topic2portDict[topic_axes]      = topic_joy_port
topic2portDict[topic_hat]       = topic_joy_port




topic_gui_controller       = b'gui_controller'
topic_gui_diveModes        = b'gui_diveModes'
topic_gui_focus_controller = b'manual_focus'
topic_gui_depthAtt         = b'att_depth'
topic_gui_autoFocus        = b'auto_focus'
topic_gui_start_stop_track = b'tracker_cmd'
topic_gui_toggle_auto_exp  = b'auto_exposureCmd'
topic_gui_inc_exp          = b'inc_exposureCmd'
topic_gui_dec_exp          = b'dec_exposureCmd'
topic_gui_exposureVal      = b'exposureValue'
topic_gui_toggle_auto_gain = b'auto_gainCmd'
topic_gui_update_pids      = b'updatePIDS'

topic_gui_port = 8900

topic2portDict[topic_gui_controller]       = topic_gui_port
topic2portDict[topic_gui_diveModes]        = topic_gui_port
topic2portDict[topic_gui_focus_controller] = topic_gui_port
topic2portDict[topic_gui_depthAtt]         = topic_gui_port
topic2portDict[topic_gui_autoFocus]        = topic_gui_port
topic2portDict[topic_gui_start_stop_track] = topic_gui_port
topic2portDict[topic_gui_toggle_auto_exp]  = topic_gui_port
topic2portDict[topic_gui_inc_exp]          = topic_gui_port
topic2portDict[topic_gui_dec_exp]          = topic_gui_port
topic2portDict[topic_gui_exposureVal]      = topic_gui_port
topic2portDict[topic_gui_toggle_auto_gain] = topic_gui_port
topic2portDict[topic_gui_update_pids]      = topic_gui_port



topic_motors_output = b'motors_output'
topic_motors_output_port = 8898

topic2portDict[topic_motors_output] = topic_motors_output_port

#diffrent topics due to difrent freq devices
topic_imu = b'topic_imu'
topic_imu_port = 8897
topic2portDict[topic_imu] = topic_imu_port

topic_sonar = b'topic_sonar'
topic_sonar_port = 9301
topic2portDict[topic_sonar] = topic_sonar_port

topic_depth = b'topic_depth'
topic_depth_port = 9302
topic2portDict[topic_depth] = topic_depth_port


topic_of_data = b'ofData'
topic_of_minimal_data = b'ofMinimalData'
topic_of_port = 9304
topic2portDict[topic_of_data] = topic_of_port

topic_mission_status = b'mssion_status'
topic_mission_cmd    = b'mission_cmd'
topic_mission_port   = 9306

#messages:
#stop/start recording

topic_record_state=b'record_state'
topic_record_state_port=9303
topic2portDict[topic_record_state] = topic_record_state_port

topic_local_route_port=9995

topic_depth_hold_pid=b'topic_depth_control'
topic_depth_hold_port=9996
topic2portDict[topic_depth_hold_pid] = topic_depth_hold_port

topic_att_hold_yaw_pid=b'topic_att_yaw_control'
topic_att_hold_pitch_pid=b'topic_att_pitch_control'
topic_att_hold_roll_pid=b'topic_att_roll_control'
topic_att_hold_port=10052

topic2portDict[topic_att_hold_pitch_pid]    = topic_att_hold_port
topic2portDict[topic_att_hold_roll_pid]     = topic_att_hold_port
topic2portDict[topic_att_hold_yaw_pid]      = topic_att_hold_port


topic_imHoldPos_yaw_pid     =b'topic_imHoldPos_yaw_ontrol'
topic_imHoldPos_pitch_pid   =b'topic_imHoldPos_pitch_control'
topic_imHoldPos_roll_pid    =b'topic_imHoldPos_roll_control'
topic_imHoldPos_port=10054
topic2portDict[topic_imHoldPos_yaw_pid] = topic_imHoldPos_port
topic2portDict[topic_imHoldPos_pitch_pid] = topic_imHoldPos_port
topic2portDict[topic_imHoldPos_roll_pid] = topic_imHoldPos_port

topic_pos_hold_pid_fmt=b'topic_pos_hold_pid_%d'
topic_pos_hold_port=10053
for i in range(3):
    topic2portDict[topic_pos_hold_pid_fmt%i] = topic_pos_hold_port


topic_tracker        = b'topic_tracker'
topic_tracker_result = b'topic_simple_tracker_result'
topic_tracker_port   = 10101
topic2portDict[topic_tracker] = topic_tracker_port
topic2portDict[topic_tracker_result] = topic_tracker_port

topic_volt=b'topic_volt'
topic_volt_port=10102
topic2portDict[topic_volt] = topic_volt_port

topic_hw_stats=b'topic_hw_stats'
topic_hw_stats_port=10103
topic2portDict[topic_hw_stats] = topic_hw_stats_port
