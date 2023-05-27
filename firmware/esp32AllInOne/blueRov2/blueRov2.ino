#include <ESP32_Servo.h>
#include <Wire.h>
#include "MS5837.h"

//#include "xtensa/core-macros.h"


//#define DSHOT_TIMEOUT_C 20000
#define SERIAL_MSG_START_B 0b10010001

#define DEBUG_SER_PORT Serial

//#define DBG_MSG
#ifdef DBG_MSG
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
static const int motorsPin[] = {12, 14, 27, 26, 25, 33, 32, 15};

static const int ledsPort = 23;
static const int camServoPin = 10;
static const int voltagePin = 36;
static const int currentPin = 39;


uint32_t tic = 0;



void delay_ms(uint32_t ms)
{
    vTaskDelay(ms / portTICK_PERIOD_MS);
    uint32_t remainderUS = (ms % portTICK_PERIOD_MS)*1000;
    if(remainderUS) delayMicroseconds(remainderUS);
}

void setup() {
    delay_ms(1500);
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
    leds.write(1100);
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

union syncMsg{
    byte b[2];
    short sync;
  } synMsg;


union upMsgOld{
    byte b[2];
    uint16_t value;    
  } msgOld;

union upMsg{
    byte b[8];
    uint16_t value[4];    
  } msg;


union motVals_
{
  byte b[16];
  short vals[8];
} motVals;

float voltage = 0.0;
uint16_t voltage_u16 = 0;

float motFPS = 0.0;
int motCnt = 0;
uint32_t motFpsTic = millis();

void loop() {
  

  if( (millis() - tic) >= 195)
  {
     tic = millis(); //XTHAL_GET_CCOUNT();;

     voltage = analogRead(voltagePin)*0.01063; //0.010604;
     voltage_u16 = (uint16_t)min(max(round(voltage*200), (float)0.0), (float)65536.0);

     DepthSensor.read();
     float depth_m = DepthSensor.depth();
     WRITE_DEBUG_MSG("cuurent depth: ");     
     WRITE_DEBUG_MSGLN(depth_m);
     float temp_c = DepthSensor.temperature();
     
     uint16_t depth_u16 = (uint16_t)min(max(round(depth_m*200), (float)0.0), (float)65536.0);
     uint16_t tempC_u16 = (uint16_t)min(max(round(temp_c*200), (float)0.0), (float)65536.0);
     uint16_t motorFPS_u16 = (uint16_t)min(max(round(motFPS*200), (float)0.0), (float)65536.0);
     if(depth_m <= 0)
     {
          depth_u16 = (uint16_t)(0.01*200);
     }
     msg.value[0] = depth_u16;     
     msg.value[1] = tempC_u16;
     msg.value[2] = voltage_u16;
     msg.value[3] = motorFPS_u16;
     
     //WRITE_DEBUG_MSGLN(tic);
     //WRITE_DEBUG_MSG(" ");
     /*
     WRITE_DEBUG_MSG("voltage: ");
     WRITE_DEBUG_MSGLN(voltage);
     
     WRITE_DEBUG_MSG("current: ");
     WRITE_DEBUG_MSGLN(current);
     */
     /*
     WRITE_DEBUG_MSG(" got depth ");
     WRITE_DEBUG_MSG(depth_m);
     WRITE_DEBUG_MSGLN(" ");

     WRITE_DEBUG_MSG(" got depth raw:");
     WRITE_DEBUG_MSG(depth_u16 );
     WRITE_DEBUG_MSGLN(" ");
     */

     
     synMsg.b[0] = 0xac;
     synMsg.b[1] = 0xad;
     MAIN_SER_PORT.write(synMsg.b, 2);
     MAIN_SER_PORT.write(msg.b, 8);
     
     /*
     WRITE_DEBUG_MSG(temp_c);
     WRITE_DEBUG_MSG(" ");
     
     
     WRITE_DEBUG_MSG(voltage);
     WRITE_DEBUG_MSG(" ");
     
     msg.value[3] = current_u16;
     WRITE_DEBUG_MSG(current);
     WRITE_DEBUG_MSG(" ");
     
     WRITE_DEBUG_MSGLN(tic);
     */
   }
  
  static char serial_buff[2];
  char opCode = 0 ;
  short focusStep;
  short val;
  int pwm;

  if(MAIN_SER_PORT.available()>1)
  {
    char bla = MAIN_SER_PORT.read();
    //Serial.println(bla,HEX);
  
    if((bla ) == SERIAL_MSG_START_B)
    {
      //WRITE_DEBUG_MSGLN("got msg");

      opCode = MAIN_SER_PORT.read();
      if(opCode == OP_MOTORS)
      {
        //WRITE_DEBUG_MSG("got motors cmd - ");
        while(!(MAIN_SER_PORT.available() >= 16))
        {
          
        }
        MAIN_SER_PORT.readBytes(motVals.b, 16);
        for(int iMot = 0; iMot < motorsNum; iMot++)
        {
          short val = motVals.vals[iMot];
          int pwm = map(val, -400, 400, 1100, 1900);
          //WRITE_DEBUG_MSG(pwm);
          //WRITE_DEBUG_MSG(" , ");
          motors[iMot].write(pwm);
        }
        //WRITE_DEBUG_MSGLN("-------");
        motCnt += 1;
        
      }
      if(opCode == OP_LEDS)
      {
          while(!(MAIN_SER_PORT.available() > 1))
          {
            
          }
          WRITE_DEBUG_MSG("got leds cmd - ");
          val = readShortFromSerial();
          pwm = map(val, -400, 400, 1100, 1900);
          WRITE_DEBUG_MSGLN(val);
          WRITE_DEBUG_MSGLN("-------");
          leds.write(pwm);
      }
      if(opCode == OP_CAMSERVO)
      {
          while(!(MAIN_SER_PORT.available() > 1))
            {
              
            }
          //WRITE_DEBUG_MSG("got cam servo cmd - ");
          focusStep = readShortFromSerial();
          //WRITE_DEBUG_MSGLN(focusStep);
          //WRITE_DEBUG_MSGLN("-------");
          
          camServo.write(focusStep);
      }
    }
  }
  
  if ( (millis() - motFpsTic) >= 5000)
  {
    motFPS = motCnt/((millis() - motFpsTic)/1000);
    motCnt = 0;
    motFpsTic = millis(); 
    WRITE_DEBUG_MSG(" motor fps: ");
    WRITE_DEBUG_MSGLN(motFPS);
  }
}
