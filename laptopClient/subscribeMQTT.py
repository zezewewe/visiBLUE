# Reference to https://techtutorialsx.com/2017/04/23/python-subscribing-to-mqtt-topic/

import paho.mqtt.client as mqtt
import time
import json
import csv
import sys

Connected = False 

broker_address = "test.mosquitto.org"
port = 1883

# Connect to broker using Paho library
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker")
        global Connected                #Use global variable
        Connected = True                #Signal connection 
    else:
        print("Connection failed")

# csv_columns = ['Time', 'HEVIntensity', 'LightIntensity', 'artificialLight']
csv_file = 'dataLog.csv'

# Callback function executes when message is received
def on_message(client,userdata,message):
    print(f"Topic name: {message.topic}")
    payloadReceivedDict = json.loads(message.payload)
    print('Received Package')
    # print(payloadReceivedDict)
    
    with open(csv_file,'a',newline='') as f:
        w = csv.writer(f)
        # w.writerow(payloadReceivedDict.keys())
        # w.writerow([])
        for values in payloadReceivedDict.values():
            w.writerow(values)


# Callback attribute of client instance points to our callback function
client.on_connect = on_connect
client.on_message = on_message

# client.tls_set(ca_certs="mosquitto.org.crt",certfile="client.crt",keyfile="client.key")
client.connect(broker_address,port=port) # returns 0 if successful
client.loop_start()

while Connected != True:
    time.sleep(0.1)

client.subscribe("IC.embedded/GOEL/#")

try:
    while True:
        time.sleep(1)
  
except KeyboardInterrupt:
    print("exiting")
    client.disconnect()
    client.loop_stop()
