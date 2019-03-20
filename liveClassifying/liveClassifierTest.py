# -*- coding: utf-8 -*-
"""
First created on Fri Mar 23 12:19:32 2018 (since updated)

@author: Baptiste Higgs
"""












class GridEYEKit():
    def __init__(self):
        self._connected = False
        self.ser = serial.Serial() #serial port object
        self.tarr_queue = Queue(1)
        self.thermistor_queue = Queue(1)
        self.multiplier_tarr = 0.25
        self.multiplier_th = 0.0125
        self._error = 0
       # if not self.connect():
       #     print "please connect Eval Kit"
        t = threading.Thread(target=self._connected_thread).start()

    def connect(self):
        """trys to open ports and look for valid data
        returns: true - connection good
        returns: False - not found / unsupported plattform
        """
        if self.ser.isOpen():
            self.ser.close()
        else:
            try:
                ports_available = self._list_serial_ports()
            except EnvironmentError:
                self._connected = False
                return False
            """try if kit is connected to com port"""
            for port in ports_available:
                self.ser = serial.Serial(port=port,baudrate=57600, timeout=0.5) #COM Port error is handled in list serial ports
                for i in range(5):
                    if self.serial_readline(bytes_timeout=300): #if 3 bytes identifyer found
                        self._connected = True
                        return True # GridEye found
                self.ser.close()
            self._connected = False
            return False


    def _list_serial_ports(self):
        """ This function is taken from Stackoverflow and will list all serial ports"""
        """Lists serial ports

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of available serial ports
        """
        if sys.platform.startswith('win'):
            ports = ['COM' + str(i + 1) for i in range(256)]

        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this is to exclude your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')

        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')

        else:
            raise EnvironmentError('Unsuppteorted platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass`
        return result

    def _get_GridEye_data(self):
        """ get grid Eye data fron serial port and convert it to numpy array - also for further calculations"""
        tarr = np.zeros((8,8))
        thermistor = 0
        data = self.serial_readline() # read grideye value
        if  len(data) >= 135:
            self._error = 0
            if not data[1] & 0b00001000 == 0: # Grid-Eye uses 12 bit signed data for calculating thermistor
                data[1] &= 0b00000111
                thermistor = -struct.unpack('<h',data[0:2])[0]*self.multiplier_th
            else:
                thermistor = struct.unpack('<h',data[0:2])[0]*self.multiplier_th
            r = 0
            c = 0
            for i in range(2,130,2):# 2,130
                # convert data to array
                if not data[i+1] & 0b00001000 == 0: # Grid-Eye uses 12 bit two's complement for calculating data
                    data[i+1] |= 0b11111000 # if 12 bit complement, set bits 12 to 16 to convert to 16 bit two's complement
                tarr[r][c] = struct.unpack('<h',data[i:i+2])[0]*self.multiplier_tarr #combine hign and low byte to short int and calculate temperature
                c= c+1
                if c==8:
                    r = r+1
                    c=0
        else:
            self._error = self._error+1
            print("Serial Fehler")
        """ Flip Image L-R or U-D"""""
        # tarr = np.fliplr(tarr)
        # tarr = np.flipud(tarr)
        return thermistor,tarr


    def _connected_thread(self):
        """" Background task reads Serial port and puts one value to queue"""
        while True:
            if self._connected == True:
                data = self._get_GridEye_data()
                if self.tarr_queue.full():
                    self.tarr_queue.get()
                    self.tarr_queue.put(data[1])
                else:
                    self.tarr_queue.put(data[1])

                if self.thermistor_queue.full():
                    self.thermistor_queue.get()
                    self.thermistor_queue.put(data[0])
                else:
                    self.thermistor_queue.put(data[0])
                # was arbitrarily 5?
                if self._error > 10:
                    try:
                        self.ser.close()
                    except:
                        pass
                    self._connected = False
                    self._error = 0

    def get_thermistor(self):
        try:
            return self.thermistor_queue.get(True,1)
        except:
            sleep(0.1)
            return 0


    def get_temperatures(self):
        try:
            return self.tarr_queue.get(True,1)
        except:
            sleep(0.1)
            return np.zeros((8,8))

    def get_raw(self):
        try:
            return self.ser.readline()
        except:
            sleep(0.1)
            return np.zeros((8,8))

    def close(self):
        self._connected = False
        try:
            self.ser.close()
        except:
            pass

    def serial_readline(self,eol='***', bytes_timeout=300):
        """ in python 2.7 serial.readline is not able to handle special EOL strings - own implementation
        Returns byte array if EOL found in a message of max timeout_bytes byte
        Returns empty array with len 0 if not"""
        length = len(eol)
        line = bytearray()
        while True:
            c = self.ser.read(1)
            if c:
                line += c
                if line[-length:] == eol:
                    break
                if len(line) > bytes_timeout: #timeout
                    return []
            else:
                break
        return line


















#from GridEyeKit import GridEYEKit
import time
import numpy as np
import keyboard
import json


import serial
import sys
import struct
import Queue

import pickle
from sklearn.linear_model import LogisticRegression
from sklearn import metrics
from sklearn.model_selection import train_test_split
import pandas as pd


def openClassifier(fileName):
    with open(fileName, "rb") as myFile:
        return pickle.load(myFile)


def checkClassifications():
    # "temps": [[int(num*4) for num in tempList] for tempList in therm_array.tolist()]
    #get an 8x8 matrix (2d list)
    therm_array = g.get_temperatures()
    therm_array = np.flip(therm_array,1)

    #print therm_array
    #print(type(therm_array))
    
    thermArray = np.concatenate(therm_array).reshape(1, -1)

    print("\nIshaan's prediction: " + str(logRegClassifier.predict(thermArray)[0]))
    print("Aiden's prediction: " + str(svmClassifier.predict(thermArray)[0]))
    print("Baptiste's prediction: " + str(nNetClassifier.predict(thermArray)[0]))


logRegClassifier = openClassifier("logisticRegression_Ishaan.pkl")
svmClassifier = openClassifier("supportVectorMachine_Aiden.pkl")
nNetClassifier = openClassifier("neuralNetwork_Baptiste.pkl")

print("Connecting to grideye...\n")

g_status_connect = False
attempts = 0
while not g_status_connect:
    try:
        print("attempt {}".format(attempts))
        g = GridEYEKit()
        g_status_connect = g.connect()
        break
    except Exception as e:
        attempts += 1 
        print("attempt {} failed: {}".format(attempts, e))
        g.close()

print("Connected\n")

while True:
    checkClassifications()