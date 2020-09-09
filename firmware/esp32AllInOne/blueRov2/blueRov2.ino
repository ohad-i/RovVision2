
#include <ESP32_Servo.h>
#include <Wire.h>
#include "MS5837.h"

#include "xtensa/core-macros.h"


#define DSHOT_TIMEOUT_C 20000
#define SERIAL_MSG_START_B 0b10010000

#define DEBUG 1
#define DEBUG_SER_PORT Serial
//#define DMG_MSG
#ifdef DMG_MSG
#define WRITE_DEBUG_MSGLN(msg) { if(DEBUG) DEBUG_SER_PORT.println(msg); }
#define WRITE_DEBUG_MSG(msg) { if(DEBUG) DEBUG_SER_PORT.print(msg); }
#else
#define WRITE_DEBUG_MSGLN(msg) {}
#define WRITE_DEBUG_MSG(msg) { }
#endif

#define MAIN_SER_PORT Serial2


#define OP_MOTORS 0x01
#define OP_LEDS 0x02
#define OP_CAMSERVO 0x03

#define MAX_WAIT_FOR_MSG 30 

Servo motors[8];
Servo leds;
Servo camServo;

MS5837 DepthSensor;

int motorsNum = 8;
static const int motorsPin[] = {12, 14, 27, 26, 25, 33, 32, 4};

static const int ledsPort = 23;
static const int camServoPin = 10;
uint32_t tic = 0;



void delay_ms(uint32_t ms)
{
    vTaskDelay(ms / portTICK_PERIOD_MS);
    uint32_t remainderUS = (ms % portTICK_PERIOD_MS)*1000;
    if(remainderUS) delayMicroseconds(remainderUS);
}

void setup() {
    DEBUG_SER_PORT.begin(115200);
    MAIN_SER_PORT.begin(115200);
    //MAIN_SER_PORT.setTimeout(1);
    
    WRITE_DEBUG_MSGLN("init...");

    Wire.begin();
    
    // Init motors, 1500 pwm -> stop
    for(int i = 0; i<motorsNum; i++)
    {
      WRITE_DEBUG_MSG("init motor - ");
      WRITE_DEBUG_MSGLN(motorsPin[i]);
      motors[i].attach(motorsPin[i], 1100, 1900);
      delay_ms(10);
      motors[i].write(1500);
      delay_ms(100);
    }
    // Init Leds pwm output

    leds.attach(ledsPort, 1100, 1900);
    leds.write(1000);
    delay_ms(100);

    camServo.attach(camServoPin, 750, 2200);
    camServo.write(1500);
    delay_ms(100);
    /*
    for(int k = 800; k<2500; k+=10)
    {
      camServo.write(k);
      delay(1);
      WRITE_DEBUG_MSGLN(k);
      
    }*/

    // Init deapth sensor, I2c (0x76 address)
    while (!DepthSensor.init()) 
    {
    WRITE_DEBUG_MSGLN("Init failed!");
    WRITE_DEBUG_MSGLN("Are SDA/SCL connected correctly?");
    WRITE_DEBUG_MSGLN("Blue Robotics Bar30: White=SDA, Green=SCL");
    WRITE_DEBUG_MSGLN("\n\n\n");
    delay(1000);
    }
    DepthSensor.setModel(MS5837::MS5837_30BA);
    DepthSensor.setFluidDensity(1029); // kg/m^3 (997 for freshwater, 1029 for seawater)
      
    delay_ms(1000);
    WRITE_DEBUG_MSGLN("done init.");    
    tic = millis(); //XTHAL_GET_CCOUNT();
}

int mapFloat(float inVal, float inMin, float inMax, int outMin, int outMax)
{
   int ret = (int)((inVal-inMin)*(outMax-outMin)/(inMax-inMin) + outMin);
   return ret;
}

short readShortFromSerial()
{
  union vals{
    byte b[2];
    short val;
  } ret;
  ret.b[0] = MAIN_SER_PORT.read();
  ret.b[1] = MAIN_SER_PORT.read();
  
  return ret.val;
}

union upMsg{
    byte b[2];
    short value;
  } msg;

union motVals_
{
  byte b[16];
  short vals[8];
} motVals;

void loop() {
  
  DepthSensor.read();
  float depth_m = DepthSensor.depth();
  if( (millis() - tic)/portTICK_PERIOD_MS >= 18)
  {
     msg.value = (short)round(depth_m * 100);
     tic = millis(); //XTHAL_GET_CCOUNT();;
     //WRITE_DEBUG_MSGLN(tic);
     //WRITE_DEBUG_MSG(" ");
     WRITE_DEBUG_MSG(" got depth ");
     WRITE_DEBUG_MSGLN(depth_m);
     MAIN_SER_PORT.write(msg.b, 2);
  }
  
  static char serial_buff[2];
  char opCode = 0 ;
  short focusStep;
  short val;
  int pwm; 

    if((MAIN_SER_PORT.read() & 0b11110000) == SERIAL_MSG_START_B)
    {
      WRITE_DEBUG_MSGLN("got msg");
      
      opCode = MAIN_SER_PORT.read();
      if(opCode == OP_MOTORS)
      {
        WRITE_DEBUG_MSG("got motors cmd - ");
        
        MAIN_SER_PORT.readBytes(motVals.b, 16);
        for(int iMot = 0; iMot < motorsNum; iMot++)
        {
          short val = motVals.vals[iMot];
          int pwm = map(val, -400, 400, 1100, 1900);
          WRITE_DEBUG_MSG(pwm);
          WRITE_DEBUG_MSG(" , ");
          motors[iMot].write(pwm);
        }
        WRITE_DEBUG_MSGLN("-------");
    
      }
      if(opCode == OP_LEDS)
      {
          WRITE_DEBUG_MSG("got leds cmd - ");
          val = readShortFromSerial();
          pwm = map(val, -400, 400, 1100, 1900);
          WRITE_DEBUG_MSGLN(pwm);
          WRITE_DEBUG_MSGLN("-------");
          leds.write(pwm);
      }
      if(opCode == OP_CAMSERVO)
      {
          WRITE_DEBUG_MSG("got cam servo cmd - ");
          focusStep = readShortFromSerial();
          WRITE_DEBUG_MSGLN(focusStep);
          WRITE_DEBUG_MSGLN("-------");
          
          camServo.write(focusStep);
      }
    }

}
