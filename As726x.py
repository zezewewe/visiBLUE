
# SPDX-FileCopyrightText: 2020 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import datetime
import board
import numpy as np
import json
import paho.mqtt.client as mqtt
import telebot
import os

# ====== Set up telegram bot ======

# Depending on OS type, the / is different in the directory
if os.name == 'posix':
    slash = '/telebot/' 
else:
    slash = '\\'

# Getting the currently working directory
current_working_directory = os.getcwd()

# Open the files for token and User ID
token_file = open(current_working_directory + slash + 'token.txt', 'r')
patientUser_file = open(current_working_directory + slash + 'patient_userID.txt', 'r')
normUser_file = open(current_working_directory + slash + 'norm_userID.txt', 'r')

# Obtain the token for the telebot and the user ID, then close the files
pat_bot_ID = token_file.read()
norm_user_IDs = normUser_file.read().split(',')
pat_user_IDs = patientUser_file.read().split(',')
token_file.close()
normUser_file.close()
patientUser_file.close()

# Create bot
pat_bot = telebot.TeleBot(token=pat_bot_ID)

# Last sent message
lastsent_time = datetime.datetime.now()

# Limit frequency of messages
seconds_from_last_msg = 10

# ====== End Set up telegram bot ======

# set up MQTT 
client = mqtt.Client()
client.tls_set(ca_certs="mosquitto.org.crt",certfile="client.crt",keyfile="client.key")
client.connect("test.mosquitto.org",port=8884) # returns 0 if successful

MqttTopic = "IC.embedded/GOEL/sendDict"

# set up I2C:
from adafruit_as726x import AS726x_I2C
i2c = board.I2C()
sensor = AS726x_I2C(i2c)
sensor.conversion_mode = sensor.MODE_2


# Tuneable parameters
user = 'general' #'specialized'
userDict = {'specialized': 0, 'general': 1}

HEVThresholdList = [0.25, 0.4] # HEV = High Energy Visible Light; 0: low, 1: high
LightThresholdList = [0.3,0.6]
HEVThresholdValue = HEVThresholdList[userDict[user]] 
LightThresholdValue = LightThresholdList[userDict[user]]

normalizedStdDevThresholdValue = 0.2 # param to decide natural or screen light -> should be low
maxSensorReading = 16000 # maximum value for sensor reading

sensorReadFrequency = 5 # seconds
piPublishFrequency = 10 # times
piCounter = 0

# HEVTmpVar = 0
# IntensityTmpVar = 0

harmfulHEVMask = np.array([1,1,0,0,0,0],dtype=np.bool) # violet and blue are HEV

dataPackageDict={}

def message_limiter(sendrequest_time, lastsent_time):
    time_diff = sendrequest_time - lastsent_time
    if time_diff.total_seconds() > seconds_from_last_msg:
        return 1
    else:
        return 0

def send_tele_message(userID_list, message):
    #global lastsent_time
    messagesend_time = datetime.datetime.now()
    if message_limiter(messagesend_time, lastsent_time):
        #lastsent_time = messagesend_time
        for userID in userID_list:
            pat_bot.send_message(userID, message)

# screen vs natural light
def identifyArtificialLight(lightValues):
    '''Takes in array of 6 frequencies from sensor; Outputs whether light is natural or artifical.'''
    normalizedStdDev = np.std(lightValues)/np.mean(lightValues)
    print(normalizedStdDev)
    return int(normalizedStdDev > normalizedStdDevThresholdValue) # 1 if Artificial light

# obtain HEV Level and Intensity Levels, and send Alerts if required
def checkHEVLevel(lightValues):
    harmfulHEVIntensity = sum(lightValues[harmfulHEVMask])/sum(lightValues)
    print(harmfulHEVIntensity)
    if (harmfulHEVIntensity > HEVThresholdValue):
        send_tele_message(norm_user_IDs, 'High blue light intensity alert!')
        send_tele_message(pat_user_IDs, 'High blue light intensity alert!')
        #lastsent_time = messagesend_time
    return harmfulHEVIntensity

def checkIntensityLevel(lightValues):
    overallLightIntensity = min(sum(lightValues)/(5*maxSensorReading),1)
    print(overallLightIntensity)
    if (overallLightIntensity > LightThresholdValue):
        send_tele_message(norm_user_IDs, 'High light intensity alert!')
    return overallLightIntensity

# process raw data
''' 
To be done on laptopClient
def prepareData(harmfulHEVIntensity,overallLightIntensity):
    global HEVTmpVar, IntensityTmpVar
    HEVTmpVar = max(HEVTmpVar,harmfulHEVIntensity)
    IntensityTmpVar += overallLightIntensity
    print(HEVTmpVar,IntensityTmpVar)
'''

while True:
    # Wait for data to be ready
    while not sensor.data_ready:
        time.sleep(0.1)
    timeNow = datetime.datetime.now().strftime("%d-%b-%y %H:%M:%S")
    piCounter += 1
    print(f"Count Value is now: {piCounter}.")

    lightValues = np.array([sensor.violet, sensor.blue, sensor.green, sensor.yellow, sensor.orange, sensor.red])
    print(lightValues)
    # print(f"1 if Artificial {identifyArtificialLight(lightValues)}")

    # harmfulHEVIntensity = sum(lightValues[harmfulHEVMask])/sum(lightValues)
    # overallLightIntensity = min(sum(lightValues)/(5*maxSensorReading),1)

    # Check levels and send immediate alerts if required
    harmfulHEVIntensity=checkHEVLevel(lightValues)
    overallLightIntensity=checkIntensityLevel(lightValues)
    artificialLightBool=identifyArtificialLight(lightValues)
    #print(f'Light Intensity: {overallLightIntensity}; HEV Intensity: {harmfulHEVIntensity}.\n')

    # Log and process data
    # prepareData(harmfulHEVIntensity,overallLightIntensity) #to be done on laptopClient?
    
    dataPackageDict[piCounter]=[timeNow,harmfulHEVIntensity, overallLightIntensity, artificialLightBool]
    print(len(dataPackageDict))
    if piCounter == piPublishFrequency:
        '''
        dataPackageDict = {
            "TimeNow": timeNow,
            "HEVIntensity": HEVTmpVar,
            "LightIntensity": IntensityTmpVar,
        }
        '''
        print(dataPackageDict)

        # publish data
        dataPackageJson = json.dumps(dataPackageDict)
        MSG_INFO = client.publish(MqttTopic,dataPackageJson)
        print('Published')

        # reset tmp variables
        # HEVTmpVar = 0
        # IntensityTmpVar = 0
        piCounter = 0
        dataPackageDict={}
    time.sleep(sensorReadFrequency)

