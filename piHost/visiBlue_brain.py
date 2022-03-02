# from operator import truediv
import time
import datetime
# from turtle import hideturtle
import board
import numpy as np
import json
import paho.mqtt.client as mqtt
import telebot
import os
from adafruit_as726x import AS726x_I2C

###################################
####### Subscription Plan #########
###################################
current_working_directory = os.getcwd()
# Depending on OS type, the / is different in the directory
if os.name == 'posix': 
    slash = '/' 
else: 
    slash = '\\'

# Obtain user info [clientID,subscriptionPlan,teleID,sleepHour,preSleepBuffer,doctorEmail]
# Demo: # 116F - General; 227B - Insomniac; 338J - Sensitive
userDetailsOpen = open(current_working_directory+slash+'userDetails.csv') 
userDetailsRead = userDetailsOpen.read()
userDict = {}
isGeneral = isInsomniacs = isSensitive = False
for i in userDetailsRead.split('\n')[:-1]:
    user = i[:4] 
    info = i[4:].split(',')[1:]
    userDict[user]=info
    if info[0] == '0':
        isGeneral = True # Send dataPackage every 15 minutes
    elif info[0] == '1':
        isInsomniacs = True # send Telebot notification; Turn on glass filter (print line), Request for desired sleeping time 
        insomniac_tele_id = info[1]
        sleepHour = int(info[2]) # 24 hour format
        preSleepBuffer = int(info[3]) # hours
    elif info[0] == '2':
        isSensitive = True # Turn on glass filter (print line)
        doctorEmail = info[4]

###################################
###### Set up telegram bot ########
###################################
# Obtain token for the telebot and the user ID
token_txt = open(os.path.join(current_working_directory,'telebot','token.txt'), 'r')
bot_alert_id = token_txt.read()
token_txt.close()
# Create bot
bot_alert = telebot.TeleBot(token=bot_alert_id)
# Limit frequency of msgs
tele_send_freq = 60 # seconds -> seconds (just for demo)


#########################
###### Set up MQTT ######
#########################
client = mqtt.Client()
client.tls_set(ca_certs="mosquitto.org.crt",certfile="client.crt",keyfile="client.key")
client.connect("test.mosquitto.org",port=8884) # returns 0 if successful
MqttTopic = "IC.embedded/GOEL/sendDict"


#########################
###### Set up I2C #######
#########################
i2c = board.I2C()
sensor = AS726x_I2C(i2c)
sensor.conversion_mode = sensor.MODE_2


#############################
###### Tunable Params #######
#############################
harmfulHEVMask = np.array([1,1,0,0,0,0],dtype=bool) # violet and blue are HEV
# Set threshold values (user/doctor can adjust thresholds)
if isGeneral:
    HEVThresholdValue = 0.4
    LightThresholdValue = 0.6
elif isInsomniacs:
    HEVThresholdValue = 0.25
    LightThresholdValue = 0.3
else:
    LightThresholdValue = 0.3 # or any other value prescribed by the doctor
# Attempt to distinguish real vs artificial light
normalizedStdDevThresholdValue = 0.2 # param to decide natural or screen light -> should be low
maxSensorReading = 16000 # maximum value for sensor reading
# Sensor reading frequency; Mqtt publishing frequency
sensorReadFrequency = 5 # seconds
piPublishFrequency = 10 # times
piCounter = 0
teleBlueList = [False,1000]
teleLightList = [False,1000]
dataPackageDict = {}
actuationTimeOut = 30 # seconds (just for demo)


##############################
###### Helper Functions ######
##############################
time_pointer=datetime.datetime.now()-datetime.timedelta(seconds=tele_send_freq)
def send_tele_message(tele_user_id, message):
    global time_pointer
    if datetime.datetime.now() >= time_pointer:
        bot_alert.send_message(tele_user_id, message)
        time_pointer=datetime.datetime.now()+datetime.timedelta(seconds=tele_send_freq)
        print('Tele Alert Sent')

# screen vs natural light
def identifyArtificialLight(lightValues):
    '''Takes in array of 6 frequencies from sensor; Outputs whether light is natural or artifical.'''
    # might want to consider using ML instead
    normalizedStdDev = np.std(lightValues)/np.mean(lightValues)
    # print('normalizedStdDev',normalizedStdDev)
    return [int(normalizedStdDev > normalizedStdDevThresholdValue),normalizedStdDev] # 1 if Artificial light

def nearingSleep():
    # assume user sleeps before/at sleepHour
    hourNow = datetime.datetime.now().hour
    addOn=0
    if sleepHour<hourNow:
        addOn=24
    if sleepHour+addOn-hourNow < preSleepBuffer:
        return True
    return False

# obtain HEV Level and Intensity Levels, and send Alerts if required
def checkHEVLevel(lightValues):
    harmfulHEVIntensity = sum(lightValues[harmfulHEVMask])/sum(lightValues)
    # print(harmfulHEVIntensity)
    # this only involves insomniacs and sensitives
    if (nearingSleep() and isInsomniacs) or isSensitive:
        # bad light
        if harmfulHEVIntensity > HEVThresholdValue:
            print('[debug] HEV alert')
            if isInsomniacs: 
                # add to tele msg alert
                teleBlueList[0] = True
                teleBlueList[1] = harmfulHEVIntensity
            # turn on filter if not already on for both subscribers
            blueLightActuation.activateActuationAndSetEndTime() 
        else: 
            blueLightActuation.deactivateActuation()
    # keep filter off for insomniac subscribers if not yet sleeptime 
    if not nearingSleep() and isInsomniacs:
        blueLightActuation.deactivateActuation()
    return harmfulHEVIntensity


def checkIntensityLevel(lightValues):
    overallLightIntensity = min(sum(lightValues)/(5*maxSensorReading),1)
    # print(overallLightIntensity)
    # this only involves insomniacs and sensitives
    if (nearingSleep() and isInsomniacs) or isSensitive:
        # bad light
        if overallLightIntensity > LightThresholdValue:
            print('[debug] Bright alert')
            if isInsomniacs:
                # add to msg alert
                teleLightList[0] = True
                teleLightList[1] = overallLightIntensity
            # turn on filter if not already on for both subscribers
            brightLightActuation.activateActuationAndSetEndTime()
        else:
            brightLightActuation.deactivateActuation()
    # keep filter off for insomniac subscribers if not yet sleeptime
    if not nearingSleep() and isInsomniacs:
        brightLightActuation.deactivateActuation()
    return overallLightIntensity


def craftAndSendTeleMsg(teleBlueList,teleLightList):
    teleHeaderStr = 'visiBLUE alert notification: \n'
    if teleBlueList[0] or teleLightList[0]:
        if teleBlueList[0]:
            teleBlueStr = f'Blue Intensity Exceeded: {round(teleBlueList[1],2)}. \n '
            teleHeaderStr = teleHeaderStr + teleBlueStr
        if teleLightList[0]:
            teleLightStr = f'Light Intensity Exceeded: {round(teleLightList[1],2)} \n '
            teleHeaderStr = teleHeaderStr + teleLightStr
        send_tele_message(insomniac_tele_id,teleHeaderStr)
        # reset tele msg
        teleBlueList[0] = False
        teleBlueList[1] = 1000
        teleLightList[0] = False
        teleLightList[1] = 1000

class actuationOnOff:
    def __init__(self,actuatorType,thresholdValue):
        self.actuationOn = False # Actuation is off
        self.actuatorType = actuatorType
        self.actuationEndTime = datetime.datetime.now()
        self.thresholdValue = thresholdValue
    def activateActuationAndSetEndTime(self):
        self.actuationEndTime = datetime.datetime.now()+datetime.timedelta(seconds=actuationTimeOut)
        if not self.actuationOn:
            print(f'[ACTUATION] Activating visiBLUE {self.actuatorType} Filter')
            self.actuationOn = True
    def deactivateActuation(self):
        if self.actuationOn:
            if datetime.datetime.now()>self.actuationEndTime:
                print(f'[ACTUATION] Deactivating visiBLUE {self.actuatorType} Filter')
                self.actuationOn = False
    def killSwitch(self):
        self.actuationOn = False
        self.actuationEndTime = datetime.datetime.now()

blueLightActuation = actuationOnOff('Blue Light',HEVThresholdValue)
brightLightActuation = actuationOnOff('Bright Light',LightThresholdValue)


######################
###### visiBLUE ######
######################
while True:
    # Wait for data to be ready
    while not sensor.data_ready:
        time.sleep(0.1)
    timeNow = datetime.datetime.now().strftime("%d-%b-%y %H:%M:%S")
    piCounter += 1
    print(f"Packet {piCounter}/{piPublishFrequency}.")

    lightValues = np.array([sensor.violet, sensor.blue, sensor.green, sensor.yellow, sensor.orange, sensor.red])
    # print(lightValues)

    # Check levels; send immediate alerts for insomniacs; adjust visiBLUE filter levels for insomniacs and sensitive
    harmfulHEVIntensity=checkHEVLevel(lightValues)
    overallLightIntensity=checkIntensityLevel(lightValues)
    artificialLightBool=identifyArtificialLight(lightValues)[0]

    craftAndSendTeleMsg(teleBlueList,teleLightList)

    normalizedStdDev=identifyArtificialLight(lightValues)[1]
    #print(f'Light Intensity: {overallLightIntensity}; HEV Intensity: {harmfulHEVIntensity}.\n')

    # prepare and send dataPackage for general and sensitive subscribers
    if isGeneral or isSensitive:
        dataPackageDict[piCounter]=[timeNow,harmfulHEVIntensity,overallLightIntensity,artificialLightBool,normalizedStdDev]
        dataPackageDict[piCounter].extend(lightValues)
        # print(len(dataPackageDict))
        if piCounter == piPublishFrequency:
            print(dataPackageDict)
            # publish data
            dataPackageJson = json.dumps(dataPackageDict)
            MSG_INFO = client.publish(MqttTopic,dataPackageJson)
            print('Published to laptop client')

            piCounter = 0
            dataPackageDict={}
    time.sleep(sensorReadFrequency)

