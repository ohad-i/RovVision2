#include <ESP32_Servo.h>
#include <Wire.h>
#include "MS5837.h"

#include <esp_task_wdt.h>

#define SERIAL_MSG_START_B 0x91 
// 0x91 -> 0b10010001 -> 145

#define DEBUG_SER_PORT Serial

//#define DBG_MSG
#ifdef DBG_MSG
#define WRITE_DEBUG_MSGLN(msg) { DEBUG_SER_PORT.println(msg); }
#define WRITE_DEBUG_MSG(msg) { DEBUG_SER_PORT.print(msg); }
#else
#define WRITE_DEBUG_MSGLN(msg) {}
#define WRITE_DEBUG_MSG(msg) { }
#endif

#define WRITE_CRITICAL_MSG(msg) { DEBUG_SER_PORT.print(msg); }
#define WRITE_CRITICAL_MSGLN(msg) { DEBUG_SER_PORT.println(msg); }

#define MAIN_SER_PORT Serial2


#define OP_MOTORS 0x01

#define OP_LEDS 0x02
#define OP_CAMSERVO 0x03

#define OP_GENERAL_CMD 0x04

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

void delay_ms(uint32_t ms)
{
    vTaskDelay(ms / portTICK_PERIOD_MS);
    uint32_t remainderUS = (ms % portTICK_PERIOD_MS)*1000;
    if(remainderUS) {
      delayMicroseconds(remainderUS);
    }
}

union syncMsg{
    byte b[2];
    short sync;
  } synMsg;


union upMsgOld{
    byte b[2];
    uint16_t value;    
  } msgOld;

union upMsg_{
    byte b[8];
    uint16_t value[4];    
  } upmsg;


union motVals_
{
  byte b[16];
  short vals[8];
} motVals;


union generalMsg_
{
  byte b[20];
  short vals[10]; // morors 0...7, focus, leds 
} generalMsg;
int focusIdx = 8;
int ledsIdx = 9;

float motFPS = 0.0;
float sensFPS = 0.0;
int motCnt = 0;


bool deepSensInit = false;


TaskHandle_t Task1;
TaskHandle_t Task2;

void motorsFailSafe(){

    WRITE_CRITICAL_MSGLN("failsafe motors - ");
    for(int i = 0; i<motorsNum; i++)
    {
      WRITE_CRITICAL_MSG("motor - ");
      WRITE_CRITICAL_MSGLN(motorsPin[i]);
      motors[i].write(1500);
      delay_ms(10);
    }

}


void sensorsHandler_LRT( void * parameter) {

  //esp_task_wdt_init(30, false); //disable esp HW watchdog
  
  WRITE_CRITICAL_MSGLN("starting lrt thread...");
  
  synMsg.b[0] = 0xac;
  synMsg.b[1] = 0xad;

  float voltage = 0.0;
  uint16_t voltage_u16 = 0;
  float depth_m = 99;
  float temp_c = 99;
  uint16_t tempC_u16 = 99;
  uint16_t depth_u16 = 99;
  uint16_t motorFPS_u16 = 99;

  float loopFPS = 0;
  int sensCnt = 0;
  int loopCnt = 0;
  uint32_t sensFpsTic = millis();

  esp_task_wdt_init(30, false); //disable esp HW watchdog
  
  for(;;) 
  {
    loopCnt++;
    if( (millis() - tic) >= 195)
    {
      tic = millis();
      sensCnt++; 
      
      voltage = analogRead(voltagePin)*0.01063; //0.010604;
      voltage_u16 = (uint16_t)min(max(round(voltage*200), (float)0.0), (float)65536.0);
      

      if (deepSensInit )
      {
        DepthSensor.read();
        depth_m = DepthSensor.depth();
        temp_c = DepthSensor.temperature();

        WRITE_DEBUG_MSG("cuurent depth: ");     
        WRITE_DEBUG_MSGLN(depth_m);
        
        depth_u16 = (uint16_t)min(max(round(depth_m*200), (float)0.0), (float)65536.0);
        tempC_u16 = (uint16_t)min(max(round(temp_c*200), (float)0.0), (float)65536.0);
      }
      else
      {
        depth_u16 = (uint16_t)min(max(round(depth_m*200), (float)0.0), (float)65536.0);
        tempC_u16 = (uint16_t)min(max(round(temp_c*200), (float)0.0), (float)65536.0);
        //WRITE_CRITICAL_MSG(millis() );
        //WRITE_CRITICAL_MSGLN(" no deepth sensor...");
      }
      
      motorFPS_u16 = (uint16_t)min(max(round(motFPS*200), (float)0.0), (float)65536.0);
      if(depth_m <= 0)
      {
            depth_u16 = (uint16_t)(0.01*200);
      }
      upmsg.value[0] = depth_u16;     
      upmsg.value[1] = tempC_u16;
      upmsg.value[2] = voltage_u16;
      upmsg.value[3] = motorFPS_u16;
      
      MAIN_SER_PORT.write(synMsg.b, 2);
      MAIN_SER_PORT.write(upmsg.b, 8);
      
     }

      if ( (millis() - sensFpsTic) >= 8000)
      {
        sensFPS = sensCnt/((millis() - sensFpsTic)/1000);
        loopFPS = loopCnt/((millis() - sensFpsTic)/1000);
        WRITE_CRITICAL_MSG(" sensors fps: ");
        WRITE_CRITICAL_MSGLN(sensFPS);
        
        WRITE_CRITICAL_MSG( millis() );
        WRITE_CRITICAL_MSG(" ");
        WRITE_CRITICAL_MSG(loopFPS);
        WRITE_CRITICAL_MSGLN(" - sensoers lps");
        
        sensCnt = 0;
        sensFpsTic = millis(); 
        loopCnt = 0;  
      }
    
    }
    //optional...
    //vTaskDelete(Task1);
    

}

void commandHandler_RT( void * parameter) {
  char opCode = 0x00;
  float loopFPS;
  int pwm;
  short val;
  short ii = 0;

  int loopCnt = 0;
  uint32_t motFpsTic = millis();
  uint32_t lastMsgTic = millis();

  //esp_task_wdt_init(30, false); //disable esp HW watchdog

  WRITE_CRITICAL_MSGLN("starting rt thread...");
  bool sentFailSafe = false;

  esp_task_wdt_init(30, false); //disable esp HW watchdog

  for(;;) {
    loopCnt++;

    if( (millis()-lastMsgTic) > 1000 )
    {
      if(!sentFailSafe)
      {
        motorsFailSafe();
        sentFailSafe = true;
      }

    }
    if(MAIN_SER_PORT.available()>1)
    {
      char bla = MAIN_SER_PORT.read();
      
      if( (bla) == SERIAL_MSG_START_B)
      {
        opCode = MAIN_SER_PORT.read();
        if(opCode == OP_GENERAL_CMD)
        {
          lastMsgTic = millis();
          sentFailSafe = false;
          //WRITE_DEBUG_MSG("got motors cmd - ");
          while(!(MAIN_SER_PORT.available() >= 20))
          {
            
          }
          MAIN_SER_PORT.readBytes(generalMsg.b, 20);
          for(int iMot = 0; iMot < motorsNum; iMot++)
          {
            short val = generalMsg.vals[iMot];
            int pwm = map(val, -400, 400, 1100, 1900);
            WRITE_DEBUG_MSG(pwm);
            WRITE_DEBUG_MSG(" , ");
            motors[iMot].write(pwm);
          }
          WRITE_DEBUG_MSGLN(" --- ");
          motCnt += 1;
          if(generalMsg.vals[focusIdx] > 0)
          {
            pwm = map(generalMsg.vals[focusIdx]-700, -700, 700, 800, 2200);
            WRITE_DEBUG_MSG("recieved focus PWM -> ")
            WRITE_DEBUG_MSGLN(pwm);
            WRITE_DEBUG_MSGLN("-------");
            camServo.write(pwm);
          }
          if(generalMsg.vals[ledsIdx] > 0)
          {
            pwm = map(generalMsg.vals[ledsIdx]-400, -400, 400, 1100, 1900);
            WRITE_DEBUG_MSG("recieved led PWM -> ")
            WRITE_DEBUG_MSGLN(pwm);
            WRITE_DEBUG_MSGLN("-------");
            leds.write(pwm);
          }
        }
        else // old configuration where each device had an opcode of its own
        { 
          if(opCode == OP_MOTORS)
          {
            lastMsgTic = millis();
            sentFailSafe = false;
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
              short focusStep = readShortFromSerial();
              //WRITE_DEBUG_MSGLN(focusStep);
              //WRITE_DEBUG_MSGLN("-------");
              
              camServo.write(focusStep);
          }
        }
      }
    }
    
    if ( (millis() - motFpsTic) >= 5000)
    {
      motFPS = motCnt/((millis() - motFpsTic)/1000);
      loopFPS = loopCnt/((millis() - motFpsTic)/1000);
      WRITE_CRITICAL_MSG(" motor fps: ");
      WRITE_CRITICAL_MSGLN(motFPS);
      
      WRITE_CRITICAL_MSG( millis() );
      WRITE_CRITICAL_MSG(" ");
      WRITE_CRITICAL_MSG(loopFPS);
      WRITE_CRITICAL_MSGLN(" - motors lps");
      
      motCnt = 0;
      motFpsTic = millis(); 
      loopCnt = 0;  
    }
    
    //optional...
    //vTaskDelete(Task1);
  }
}

void setup() {
    
    //delay_ms(1500);
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
      delay_ms(10);
    }
    // Init Leds pwm output
    leds.attach(ledsPort, 1100, 1900);
    leds.write(1100);
    delay_ms(10);


    camServo.attach(camServoPin, 750, 2200);
    camServo.write(1500);
    delay_ms(10);

    /*
    for(int k = 800; k<2500; k+=10)
    {
      camServo.write(k);
      delay(1);
      WRITE_DEBUG_MSGLN(k);
      
    }*/
    
    
    // Init deapth sensor, I2c (0x76 address)
    if(!DepthSensor.init())
    {

      for(int j = 0; j< 10; j++)  
      {
        WRITE_CRITICAL_MSGLN("Init failed!");
        WRITE_CRITICAL_MSGLN("Are SDA/SCL connected correctly?");
        WRITE_CRITICAL_MSGLN("Blue Robotics Bar30: White=SDA, Green=SCL");
        WRITE_CRITICAL_MSGLN(j);
        WRITE_CRITICAL_MSGLN("");
        delay(300);
        if(DepthSensor.init() )
        {
          break;
        }
      }
    }

    if( DepthSensor.init() )
    {
      DepthSensor.setModel(MS5837::MS5837_30BA);
      DepthSensor.setFluidDensity(1029); // kg/m^3 (997 for freshwater, 1029 for seawater)
      deepSensInit = true;
    }
    WRITE_CRITICAL_MSGLN("222");
    
    WRITE_DEBUG_MSGLN("done init.");    
    tic = millis(); //XTHAL_GET_CCOUNT();
    
    // RT -> high real time operations: motors commans
    xTaskCreatePinnedToCore(
      commandHandler_RT, /* Function to implement the task */
      "commandHandler",   /* Name of the task */
      10000,     /* Stack size in words */
      NULL,      /* Task input parameter */
      1,         /* Priority of the task 0(lowes),1,2 (highest) */
      &Task1,    /* Task handle. */
      1);        /* Core where the task should run */
    
    //LRT-> low realtime operations: focus servo, leds
    xTaskCreatePinnedToCore(
      sensorsHandler_LRT, /* Function to implement the task */
      "sensorsHandler",   /* Name of the task */
      10000,     /* Stack size in words */
      NULL,      /* Task input parameter */
      1,         /* Priority of the task 0(lowes),1,2 (highest)*/
      &Task2,    /* Task handle. */
      0);        /* Core where the task should run */ 

    esp_task_wdt_init(30, false); //disable esp HW watchdog
    WRITE_CRITICAL_MSGLN("done init, no debug info...");

}

void loop() {
  
}
