# SPDX-FileCopyrightText: 2020 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import numpy as np

# for I2C use:
from adafruit_as726x import AS726x_I2C

# # for UART use:
# # from adafruit_as726x import AS726x_UART

# maximum value for sensor reading
max_val = 16000

# # max number of characters in each graph
# max_graph = 80

user = 'general' #'specialized'
userDict = {'specialized': 0, 'general': 1}

HEVThresholdList = [0.25, 0.4] # HEV = High Energy Visible Light; 0: low, 1: high
LightThresholdList = [0.3,0.6]

HEVThresholdValue = HEVThresholdList[userDict[user]]
LightThresholdValue = LightThresholdList[userDict[user]]

harmfulHEVMask = np.array([1,1,0,0,0,0],dtype=np.bool) # violet and blue are HEV

# def graph_map(x):
#     return min(int(x * max_graph / max_val), max_graph)

# for I2C use:
i2c = board.I2C()
sensor = AS726x_I2C(i2c)
sensor.conversion_mode = sensor.MODE_2

while True:
    # Wait for data to be ready
    while not sensor.data_ready:
        time.sleep(0.1)

    lightValues = np.array([sensor.violet, sensor.blue, sensor.green, sensor.yellow, sensor.orange, sensor.red])
    print(lightValues)
    harmfulHEVIntensity = sum(lightValues[harmfulHEVMask])/sum(lightValues)
    overallLightIntensity = min(sum(lightValues)/(5*max_val),1)
    print(f'Light Intensity: {overallLightIntensity}; HEV Intensity: {harmfulHEVIntensity}.\n')

    if harmfulHEVIntensity > HEVThresholdValue:
        print('WARNING! Turn on Night Light Mode NOW! \n')
    if overallLightIntensity > LightThresholdValue:
        print('WARNING! Turn down Screen Brightness NOW! \n')
    
       
    # plot plot the data
    # print("\n")
    # print("V: " + str(graph_map(sensor.violet))) # * "=")
    # print("B: " + str(graph_map(sensor.blue))) # * "=")
    # print("G: " + str(graph_map(sensor.green))) # * "=")
    # print("Y: " + str(graph_map(sensor.yellow))) # * "=")
    # print("O: " + str(graph_map(sensor.orange))) # * "=")
    # print("R: " + str(graph_map(sensor.red))) # * "=")

    time.sleep(1)
