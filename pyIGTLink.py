# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 19:17:05 2015

@author: Daniel Hoyer Iversen
"""

import numpy as np
import signal
import collections
import socket
import SocketServer
import sys
import struct
import threading
import time


IGTL_HEADER_VERSION  = 1
IGTL_IMAGE_HEADER_VERSION = 1


class PyIGTLink(SocketServer.TCPServer):
    """ For streaming data over TCP with GE-protocol"""
    def __init__(self,port=18944,localServer=False):
        """
        port - port number
        """
        buffer_size=100
        if localServer:
            host="127.0.0.1"
        else:
            if sys.platform.startswith('win32'):
                host = socket.gethostbyname(socket.gethostname())
            elif sys.platform.startswith('linux'):
                 import fcntl
                 s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                 try:
                     ifname='eth0'
                     host= socket.inet_ntoa(fcntl.ioctl( s.fileno(), 0x8915, struct.pack('256s', ifname[:15])  )[20:24])
                     #http://code.activestate.com/recipes/439094-get-the-ip-address-associated-with-a-network-inter/
                 except:
                     ifname='lo'
                     host= socket.inet_ntoa(fcntl.ioctl( s.fileno(), 0x8915, struct.pack('256s', ifname[:15])  )[20:24])

        SocketServer.TCPServer.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self,(host, port), TCPRequestHandler)

        self._message_queue=collections.deque(maxlen=buffer_size)
        self._lock_message_queue = threading.Lock()

        self._connected=False
        self._shuttingDown=False
        self._lock_connected_shuttingDown = threading.Lock()

        signal.signal(signal.SIGTERM, self._SignalHandler)
        signal.signal(signal.SIGINT, self._SignalHandler)
            
        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        thread = threading.Thread(target=self._PrintIpAdressAndPortNo)
        thread.daemon = True
        thread.start()


    def GetIpAdress(self):
        return self.server_address[0]

    def GetPortNo(self):
        return self.server_address[1] 

    def AddMessageToSendQueue(self,message,wait=False):
        """
            Returns True if sucessfull
        """
        if not isinstance(message,MessageBase) or not message.IsValid():
            _Print("Warning: Only accepts valid messages of class message")
            return False
    
        if self._connected:
            with self._lock_message_queue:
                self._message_queue.append(message)#copy.deepcopy(message))
            while wait and len(self._message_queue)>0:
                time.sleep(0.001)
                return True
        else:
            if len(self._message_queue)>0:
                with self._lock_message_queue:
                    self._message_queue=collections.clear()
            return False


    def _SignalHandler(self,signum,stackframe):
            if signum == signal.SIGTERM or signum == signal.SIGINT: 
                    with self._lock_connected_shuttingDown:
                            self._shuttingDown=True
                    self.CloseConnection()
                    _Print('YOU KILLED ME, BUT I CLOSED THE SERVER BEFORE I DIED')
                    sys.exit(signum)
                    

    def isConnected(self):
           return self._connected


    def CloseConnection(self):
            """Will close connection and shutdown server"""
            self._connected=False
            with self._lock_connected_shuttingDown:
                    self._shuttingDown=True
            self.shutdown()
            _Print("\nServer closed\n")

    def _PrintIpAdressAndPortNo(self):
            while True:
                    while not self._connected:
                            with self._lock_connected_shuttingDown:
                                    if self._shuttingDown:
                                            break
                            _Print("No connections\nIp adress: " +str(self.GetIpAdress()) +"\nPort number: " +str(self.GetPortNo()))
                            time.sleep(5)
                    
                    time.sleep(10)
                    with self._lock_connected_shuttingDown:
                            if self._shuttingDown:
                                    break



class TCPRequestHandler(SocketServer.BaseRequestHandler):
    """
    Help class for PyIGTLink
    """
    def handle(self):
        self.server._connected=True
        while True :
            if len(self.server._message_queue)>0:
                with self.server._lock_message_queue:
                    message=self.server._message_queue.popleft()
                    response_data=message.Pack()
                    #print "Send: " + str(message._timestamp)
                    try:
                        self.request.sendall(response_data)
                    except Exception as inst:
                        self.server._connected=False
                        _Print('ERROR, FAILED TO SEND DATA' )
                        print inst.args
                        return
            else:
                time.sleep(1/1000.0)
                with self.server._lock_connected_shuttingDown:
                    if self.server._shuttingDown:
                        break

#Help functions and help classes:
def _Print(text):
    print "********PyIGTLink********\n" + text +"\n****************************"
     




class MessageBase(object):
    """message"""
    def __init__(self):
        self._validMessage = False
        
        self._version = IGTL_HEADER_VERSION  # Version number The version number field specifies the header format version. Currently the version number is 1. Please note that this is different from the protocol version.
        self._name = ""                      # The type name field is an ASCII character string specifying the type of the data contained in the message body e.g. “TRANSFORM”. The length of the type name must be within 12 characters.
        self._device_name = ""               # The device name field contains an ASCII character string specifying the name of the the message.
        self._timestamp = 0	                # The timestamp field contains a 64-bit timestamp indicating when the data is generated. Please refer http://openigtlink.org/protocols/v2_timestamp.html for the format of the 64-bit timestamp.
        self._body_size = None               # Size of body in bytes
        self._crc = None                     # CRC The 64-bit CRC used in OpenIGTLink protocol is based on ECMA-182 standard. An example code is available in igtl_util.c in the OpenIGTLink library.

        self._endian = ">"                   # big-endian

    def Pack(self):
        binaryBody = self.PackBody()
        self._body_size = self.GetBodyPackSize();
        self._crc = 0
        
        binaryMessage = struct.pack(self._endian+"H",self._version)
        for k in range(12):
            if k < len(self._name):
                c = self._name[k]
            else:
                c = " "
            binaryMessage = binaryMessage + struct.pack(self._endian+"s",c)
        for k in range(20):
            if k < len(self._device_name):
                c = self._device_name[k]
            else:
                c = " "
            binaryMessage = binaryMessage + struct.pack(self._endian+"s",c)
        binaryMessage = binaryMessage + struct.pack(self._endian+"Q",self._timestamp)
        binaryMessage = binaryMessage + struct.pack(self._endian+"Q",self._body_size)
        binaryMessage = binaryMessage + struct.pack(self._endian+"Q",self._crc)
        binaryMessage = binaryMessage + binaryBody

        return binaryMessage

    def PackBody(self):
        raise RuntimeError('Should be implemented in child class')

    def GetBodyPackSize(self):
        raise RuntimeError('Should be implemented in child class')


    def IsValid(self):
        return self._validMessage



#http://openigtlink.org/protocols/v2_header.html
class ImageMessage(MessageBase):   
    def __init__(self,data):
        MessageBase.__init__(self)
        self._name = "IMAGE"
        self._data = data
        self._validMessage = True

    def PackBody(self):
        binaryMessage = struct.pack(self._endian+"H",IGTL_IMAGE_HEADER_VERSION)
        binaryMessage = binaryMessage + struct.pack(self._endian+"I",1) # Number of Image Components (1:Scalar, >1:Vector). (NOTE: Vector data is stored fully interleaved.)
        if self._data.dtype == np.int8:
             s=2
        elif self._data.dtype == np.uint8:
            s=3
        elif self._data.dtype == np.int16:
            s=4
        elif self._data.dtype == np.uint16:
            s=5
        elif self._data.dtype == np.int32:
            s=6
        elif self._data.dtype == np.uint32:
            s=7
        elif self._data.dtype == np.float32:
            s=10
        elif self._data.dtype == np.float64:
            s=11
        else:
            return
        binaryMessage = binaryMessage + struct.pack(self._endian+"I",s) 
        binaryMessage = binaryMessage + struct.pack(self._endian+"I",1)  # Endian for image data (1:BIG 2:LITTLE) (NOTE: values in image header is fixed to BIG endian)

        binaryMessage = binaryMessage + struct.pack(self._endian+"H",self._data.shape)  

        return binaryMessage

    def GetBodyPackSize(self):
        pass