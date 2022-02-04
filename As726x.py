# SPDX-FileCopyrightText: 2020 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import datetime
import board
import numpy as np
import json
import paho.mqtt.client as mqtt

# set up MQTT 
client = mqtt.Client()
client.tls_set(ca_certs="mosquitto.org.crt",certfile="client.crt",keyfile="client.key")
client.connect("test.mosquitto.org",port=8884) # returns 0 if successful

MqttTopic = "IC.embedded/GOEL/test"

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

normalizedStdDevThresholdValue = 100 # param to decide natural or screen light
maxSensorReading = 16000 # maximum value for sensor reading

sensorReadFrequency = 1 # min
piPublishFrequency = 15 # min
piCounter = 0

HEVTmpVar = 0
IntensityTmpVar = 0

harmfulHEVMask = np.array([1,1,0,0,0,0],dtype=np.bool) # violet and blue are HEV

# screen vs natural light
def identifyNaturalLight(lightValues):
    '''Takes in array of 6 frequencies from sensor; Outputs whether light is natural or artifical.'''
    normalizedStdDev = np.std(lightValues)/np.mean(lightValues)
    return normalizedStdDev < normalizedStdDevThresholdValue # True if Natural light

# obtain HEV Level and Intensity Levels, and send Alerts if required
def checkHEVLevel(lightValues):
    harmfulHEVIntensity = sum(lightValues[harmfulHEVMask])/sum(lightValues)
    print(harmfulHEVIntensity)
    if harmfulHEVIntensity > HEVThresholdValue:
        print('Send Telgram HEV Alert!\n')
    return harmfulHEVIntensity

def checkIntensityLevel(lightValues):
    overallLightIntensity = min(sum(lightValues)/(5*maxSensorReading),1)
    print(overallLightIntensity)
    if overallLightIntensity > LightThresholdValue:
        print('Send Telegram Brightness Alert!\n')
    return overallLightIntensity

# process raw data
def prepareData(harmfulHEVIntensity,overallLightIntensity):
    global HEVTmpVar, IntensityTmpVar
    HEVTmpVar = max(HEVTmpVar,harmfulHEVIntensity)
    IntensityTmpVar += overallLightIntensity
    print(HEVTmpVar,IntensityTmpVar)


while True:
    # Wait for data to be ready
    while not sensor.data_ready:
        time.sleep(0.1)
    timeNow = datetime.datetime.now().strftime("%d-%b-%y %H:%M")
    piCounter += 1
    print(f"Count Value is now: {piCounter}.")

    lightValues = np.array([sensor.violet, sensor.blue, sensor.green, sensor.yellow, sensor.orange, sensor.red])
    print(lightValues)

    # harmfulHEVIntensity = sum(lightValues[harmfulHEVMask])/sum(lightValues)
    # overallLightIntensity = min(sum(lightValues)/(5*maxSensorReading),1)

    # Check levels and send immediate alerts if required
    harmfulHEVIntensity=checkHEVLevel(lightValues)
    overallLightIntensity=checkIntensityLevel(lightValues)
    print(f'Light Intensity: {overallLightIntensity}; HEV Intensity: {harmfulHEVIntensity}.\n')

    # Log and process data
    prepareData(harmfulHEVIntensity,overallLightIntensity)
    

    if piCounter == piPublishFrequency:
        dataPackageDict = {
            "TimeNow": timeNow,
            "HEVIntensity": HEVTmpVar,
            "LightIntensity": IntensityTmpVar,
        }
        
        # publish data
        dataPackageJson = json.dumps(dataPackageDict)
        MSG_INFO = client.publish(MqttTopic,dataPackageJson)

        # reset tmp variables
        HEVTmpVar = 0
        IntensityTmpVar = 0
        piCounter = 0

    time.sleep(sensorReadFrequency)

