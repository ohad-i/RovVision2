#!/usr/bin/env python3

# switch gpio 38 (gpio 77) high to enable sonar

import RPi.GPIO as GPIO
import sys
if len(sys.argv) < 2:
    print("Don't know wath to do... exit")
    sys.exit(0)

if sys.argv[1] == "on":
    # GPIO.cleanup()
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(38, GPIO.OUT)
    GPIO.output(38, GPIO.HIGH)
    print('Sonar is on')
elif sys.argv[1] == "off":
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(38, GPIO.OUT)
    GPIO.output(38, GPIO.LOW)
    print('Sonar is off')

