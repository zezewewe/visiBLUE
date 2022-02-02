import smbus
import time
import sys
import csv

# Get I2C bus
bus = smbus.SMBus(1)
bus.write_byte(0x40, 0xF5)
 
time.sleep(0.3)
 
# SI7021 address, 0x40  Read 2 bytes, Humidity
data0 = bus.read_byte(0x40)
data1 = bus.read_byte(0x40)
 
# Convert the data
humidity = ((data0 * 256 + data1) * 125 / 65536.0) - 6
 
time.sleep(0.3)
bus.write_byte(0x40, 0xF3)
time.sleep(0.3)
 
# SI7021 address, 0x40 Read data 2 bytes, Temperature
data0 = bus.read_byte(0x40)
data1 = bus.read_byte(0x40)
 
# Convert the data and output it
celsTemp = ((data0 * 256 + data1) * 175.72 / 65536.0) - 46.85
fahrTemp = celsTemp * 1.8 + 32

original_stdout = sys.stdout

with open('/home/pi/EmbeddedSystemsProj1/outputs.txt','w') as f:
	sys.stdout=f
	print(time.strftime("%H:%M:%S",time.localtime()))
	print("Relative Humidity is : %.2f %%" %humidity)
	print("Temperature in Celsius is : %.2f C" %celsTemp)
	print("Temperature in Fahrenheit is : %.2f F" %fahrTemp)
	sys.stdout=original_stdout

def store_data(time,temp,humidity):
	append = [time,temp,humidity]
	with open('/home/pi/EmbeddedSystemsProj1/tempLog.csv','a') as csvFile:
		writer=csv.writer(csvFile)
		writer.writerow(append)
	csvFile.close()

store_data(time.localtime(),celsTemp,humidity)


