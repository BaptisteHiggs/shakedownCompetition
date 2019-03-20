# uncompyle6 version 3.2.5
# Python bytecode 2.7 (62211)
# Decompiled from: Python 2.7.15 (v2.7.15:ca079a3ea3, Apr 30 2018, 16:22:17) [MSC v.1500 32 bit (Intel)]
# Embedded file name: d:\BVN\grideye-urinal-rt\grideye-rt\GridEyeKit.py
# Compiled at: 2018-12-10 19:52:29
"""
Created on Sun Sep 06 18:17:12 2015

@author: 70E0481
"""
import serial, sys, struct, numpy as np, threading
if sys.version_info > (3, 0):
    from queue import Queue
else:
    from Queue import Queue
import glob
from time import sleep

class GridEYEKit:

    def __init__(self):
        self._connected = False
        self.ser = serial.Serial()
        self.tarr_queue = Queue(1)
        self.thermistor_queue = Queue(1)
        self.multiplier_tarr = 0.25
        self.multiplier_th = 0.0125
        self._error = 0
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

            for port in ports_available:
                self.ser = serial.Serial(port=port, baudrate=57600, timeout=0.5)
                for i in range(5):
                    if self.serial_readline(bytes_timeout=300):
                        self._connected = True
                        return True

                self.ser.close()

            self._connected = False
            return False

    def _list_serial_ports(self):
        """ This function is taken from Stackoverflow and will list all serial ports"""
        if sys.platform.startswith('win'):
            ports = [ 'COM' + str(i + 1) for i in range(256) ]
        else:
            if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
                ports = glob.glob('/dev/tty[A-Za-z]*')
            else:
                if sys.platform.startswith('darwin'):
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
                pass

        return result

    def _get_GridEye_data(self):
        """ get grid Eye data fron serial port and convert it to numpy array - also for further calculations"""
        tarr = np.zeros((8, 8))
        thermistor = 0
        data = self.serial_readline()
        if len(data) >= 135:
            self._error = 0
            if not data[1] & 8 == 0:
                data[1] &= 7
                thermistor = -struct.unpack('<h', data[0:2])[0] * self.multiplier_th
            else:
                thermistor = struct.unpack('<h', data[0:2])[0] * self.multiplier_th
            r = 0
            c = 0
            for i in range(2, 130, 2):
                if not data[i + 1] & 8 == 0:
                    data[(i + 1)] |= 248
                tarr[r][c] = struct.unpack('<h', data[i:i + 2])[0] * self.multiplier_tarr
                c = c + 1
                if c == 8:
                    r = r + 1
                    c = 0

        else:
            self._error = self._error + 1
            print 'Serial Fehler'
        return (
         thermistor, tarr)

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
                if self._error > 10:
                    try:
                        self.ser.close()
                    except:
                        pass

                    self._connected = False
                    self._error = 0

    def get_thermistor(self):
        try:
            return self.thermistor_queue.get(True, 1)
        except:
            sleep(0.1)
            return 0

    def get_temperatures(self):
        try:
            return self.tarr_queue.get(True, 1)
        except:
            sleep(0.1)
            return np.zeros((8, 8))

    def get_raw(self):
        try:
            return self.ser.readline()
        except:
            sleep(0.1)
            return np.zeros((8, 8))

    def close(self):
        self._connected = False
        try:
            self.ser.close()
        except:
            pass

    def serial_readline(self, eol='***', bytes_timeout=300):
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
                if len(line) > bytes_timeout:
                    return []
            else:
                break

        return line