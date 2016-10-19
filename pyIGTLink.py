# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 19:17:05 2015

@author: Daniel Hoyer Iversen
"""

from __future__ import print_function
import crcmod
import numpy as np
import signal
import collections
import socket
import sys
import struct
import threading
import time
if sys.version_info >= (3, 0):
    import socketserver as SocketServer
else:
    import SocketServer

IGTL_HEADER_VERSION = 1
IGTL_IMAGE_HEADER_VERSION = 1


class PyIGTLink(SocketServer.TCPServer):
    """ For streaming data over TCP with GE-protocol"""
    def __init__(self, port=18944, localServer=False):
        """
        port - port number
        """
        buffer_size = 100
        if localServer:
            host = "127.0.0.1"
        else:
            if sys.platform.startswith('win32'):
                host = socket.gethostbyname(socket.gethostname())
            elif sys.platform.startswith('linux'):
                import fcntl
                soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    ifname = 'eth0'
                    host = socket.inet_ntoa(fcntl.ioctl(soc.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])
                    # http://code.activestate.com/recipes/439094-get-the-ip-address-associated-with-a-network-inter/
                except:
                    ifname = 'lo'
                    host = socket.inet_ntoa(fcntl.ioctl(soc.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])

        SocketServer.TCPServer.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self, (host, port), TCPRequestHandler)

        self.message_queue = collections.deque(maxlen=buffer_size)
        self.lock_server_thread = threading.Lock()

        self._connected = False
        self.shuttingdown = False

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        thread = threading.Thread(target=self._print_ip_adress_and_port_no)
        thread.daemon = True
        thread.start()

    def get_ip_adress(self):
        return self.server_address[0]

    def get_port_no(self):
        return self.server_address[1]

    def add_message_to_send_queue(self, message, wait=False):
        """
            Returns True if sucessfull
        """
        if not isinstance(message, MessageBase) or not message.is_valid():
            _print("Warning: Only accepts valid messages of class message")
            return False

        if self._connected:
            with self.lock_server_thread:
                self.message_queue.append(message)  # copy.deepcopy(message))
            while wait and len(self.message_queue) > 0:
                time.sleep(0.001)
        else:
            if len(self.message_queue) > 0:
                with self.lock_server_thread:
                    self.message_queue = collections.clear()
        return True

    def _signal_handler(self, signum, stackframe):
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.close_server()
            _print('YOU KILLED ME, BUT I CLOSED THE SERVER BEFORE I DIED')
            sys.exit(signum)

    def is_connected(self):
        return self._connected

    def update_connected_status(self, val):
        self._connected = val

    def close_server(self):
        """Will close connection and shutdown server"""
        self._connected = False
        with self.lock_server_thread:
            self.shuttingdown = True
        self.shutdown()
        self.server_close()
        _print("\nServer closed\n")

    def _print_ip_adress_and_port_no(self):
        while True:
            while not self._connected:
                with self.lock_server_thread:
                    if self.shuttingdown:
                        _print("No connections\nIp adress: " + str(self.get_ip_adress()) + "\nPort number: " + str(self.get_port_no()))
                        break
                time.sleep(5)
            time.sleep(10)
            with self.lock_server_thread:
                if self.shuttingdown:
                    break


class TCPRequestHandler(SocketServer.BaseRequestHandler):
    """
    Help class for PyIGTLink
    """
    def handle(self):
        self.server.update_connected_status(True)
        while True:
            # print(len(self.server.message_queue))
            if len(self.server.message_queue) > 0:
                with self.server.lock_server_thread:
                    message = self.server.message_queue.popleft()
                    response_data = message.get_binary_message()
                    # print "Send: " + str(message._timestamp)
                    try:
                        self.request.sendall(response_data)
                    except Exception as exp:
                        self.server.update_connected_status(False)
                        _print('ERROR, FAILED TO SEND DATA. \n'+str(exp))
                        return
            else:
                time.sleep(1/1000.0)
                with self.server.lock_server_thread:
                    if self.server.shuttingdown:
                        break


# Help functions and help classes:
def _print(text):
    print("**********PyIGTLink*********\n" + text + "\n****************************")


# http://slicer-devel.65872.n3.nabble.com/OpenIGTLinkIF-and-CRC-td4031360.html
CRC64 = crcmod.mkCrcFun(0x142F0E1EBA9EA3693, rev=False, initCrc=0x0000000000000000, xorOut=0x0000000000000000)


# http://openigtlink.org/protocols/v2_header.html
class MessageBase(object):
    """message"""
    def __init__(self):
        self._valid_message = False
        # Version number The version number field specifies the header format version. Currently the version number is 1.
        # Please note that this is different from the protocol version.
        self._version = IGTL_HEADER_VERSION
        # The type name field is an ASCII character string specifying the type of the data contained in the message body e.g. â€œTRANSFORMâ€?.
        # The length of the type name must be within 12 characters.
        self._name = ""
        # The device name field contains an ASCII character string specifying the name of the the message.
        self._device_name = ""
        # The timestamp field contains a 64-bit timestamp indicating when the data is generated.
        # Please refer http://openigtlink.org/protocols/v2_timestamp.html for the format of the 64-bit timestamp.
        self._timestamp = int(time.time())

        self._endian = ">"  # big-endian

        self._binary_body = None
        self._binary_head = None
        self._body_pack_size = 0

    def pack(self):
        binary_body = self.get_binary_body()
        body_size = self.get_body_pack_size()
        crc = CRC64(binary_body)

        binary_message = struct.pack(self._endian+"H", self._version)
        binary_message = binary_message + struct.pack(self._endian+"12s", self._name)
        binary_message = binary_message + struct.pack(self._endian+"20s", self._device_name)
        binary_message = binary_message + struct.pack(self._endian+"II", self._timestamp, 0)
        binary_message = binary_message + struct.pack(self._endian+"Q", body_size)
        binary_message = binary_message + struct.pack(self._endian+"Q", crc)

        self._binary_head = binary_message

    def get_binary_message(self):
        if not self._binary_head:
            self.pack()
        return self._binary_head + self.get_binary_body()

    def get_binary_body(self):
        if not self._binary_body:
            self.pack_body()
        return self._binary_body

    def pack_body(self):
        self._binary_body = b""

    def is_valid(self):
        return self._valid_message

    def get_body_pack_size(self):
        return self._body_pack_size


# http://openigtlink.org/protocols/v2_image.html
class ImageMessage(MessageBase):
    def __init__(self, image, spacing=[1, 1, 1], timestamp=None):
        MessageBase.__init__(self)
        self._valid_message = True
        self._name = "IMAGE"
        if timestamp:
            self._timestamp = timestamp

        try:
            self._data = np.asarray(image)
        except Exception as exp:
            _print('ERROR, INVALID IMAGE. \n' + str(exp))
            self._valid_message = False
            return

        if len(self._data.shape) < 2:
            self._valid_message = False
            _print('ERROR, INVALID IMAGE SIZE. \n')
            return


# Only int8 is suppoerted now
#        if self._data.dtype == np.int8:
#            self._datatype_s = 2
#            self._format_data = "b"
#        elif self._data.dtype == np.uint8:
#            self._datatype_s = 3
#            self._format_data = "B"
#        elif self._data.dtype == np.int16:
#            self._datatype_s = 4
#            self._format_data = "h"
#        elif self._data.dtype == np.uint16:
#            self._datatype_s = 5
#            self._format_data = "H"
#        elif self._data.dtype == np.int32:
#            self._datatype_s = 6
#            self._format_data = "i"
#        elif self._data.dtype == np.uint32:
#            self._datatype_s = 7
#            self._format_data = "I"
#        elif self._data.dtype == np.float32:
#            self._datatype_s = 10
#            self._format_data = "f"
#        elif self._data.dtype == np.float64:
#            self._datatype_s = 11
#            self._format_data = "f"
#        else:
#            pass
        self._data = np.array(self._data, dtype=np.uint8)
        self._datatype_s = 3
        self._format_data = "B"

        self._spacing = spacing
        self._matrix = np.identity(4)  # A matrix representing the origin and the orientation of the image.

    def pack_body(self):
        binary_message = struct.pack(self._endian+"H", IGTL_IMAGE_HEADER_VERSION)
        # Number of Image Components (1:Scalar, >1:Vector). (NOTE: Vector data is stored fully interleaved.)
        binary_message = binary_message + struct.pack(self._endian+"B", len(self._data.shape) - 1)
        binary_message = binary_message + struct.pack(self._endian+"B", self._datatype_s)

        if self._data.dtype.byteorder == "<":
            byteorder = "F"
            binary_message = binary_message + struct.pack(self._endian+"B", 2)  # Endian for image data (1:BIG 2:LITTLE) (NOTE: values in image header is fixed to BIG endian)
        else:
            self._data.dtype.byteorder == ">"
            byteorder = "C"
            binary_message = binary_message + struct.pack(self._endian+"B", 1)  # Endian for image data (1:BIG 2:LITTLE) (NOTE: values in image header is fixed to BIG endian)

        binary_message = binary_message + struct.pack(self._endian+"B", 1)  # image coordinate (1:RAS 2:LPS)

        binary_message = binary_message + struct.pack(self._endian+"H", self._data.shape[0])
        binary_message = binary_message + struct.pack(self._endian+"H", self._data.shape[1])
        if len(self._data.shape) > 2:
            binary_message = binary_message + struct.pack(self._endian+"H", self._data.shape[2])
        else:
            binary_message = binary_message + struct.pack(self._endian+"H", 1)

        origin = np.zeros(3)
        norm_i = np.zeros(3)
        norm_j = np.zeros(3)
        norm_k = np.zeros(3)
        for i in range(3):
            norm_i[i] = self._matrix[i][0]
            norm_j[i] = self._matrix[i][1]
            norm_k[i] = self._matrix[i][2]
            origin[i] = self._matrix[i][3]

        binary_message = binary_message + struct.pack(self._endian+"f", norm_i[0] * self._spacing[0])
        binary_message = binary_message + struct.pack(self._endian+"f", norm_i[1] * self._spacing[0])
        binary_message = binary_message + struct.pack(self._endian+"f", norm_i[2] * self._spacing[0])
        binary_message = binary_message + struct.pack(self._endian+"f", norm_j[0] * self._spacing[1])
        binary_message = binary_message + struct.pack(self._endian+"f", norm_j[1] * self._spacing[1])
        binary_message = binary_message + struct.pack(self._endian+"f", norm_j[2] * self._spacing[1])
        binary_message = binary_message + struct.pack(self._endian+"f", norm_k[0] * self._spacing[2])
        binary_message = binary_message + struct.pack(self._endian+"f", norm_k[1] * self._spacing[2])
        binary_message = binary_message + struct.pack(self._endian+"f", norm_k[2] * self._spacing[2])
        binary_message = binary_message + struct.pack(self._endian+"f", origin[0])
        binary_message = binary_message + struct.pack(self._endian+"f", origin[1])
        binary_message = binary_message + struct.pack(self._endian+"f", origin[2])

        binary_message = binary_message + struct.pack(self._endian+"H", 0)      # Starting index of subvolume
        binary_message = binary_message + struct.pack(self._endian+"H", 0)      # Starting index of subvolume
        binary_message = binary_message + struct.pack(self._endian+"H", 0)      # Starting index of subvolume

        binary_message = binary_message + struct.pack(self._endian+"H", self._data.shape[0])  # number of pixels of subvolume
        binary_message = binary_message + struct.pack(self._endian+"H", self._data.shape[1])
        if len(self._data.shape) > 2:
            binary_message = binary_message + struct.pack(self._endian+"H", self._data.shape[2])
        else:
            binary_message = binary_message + struct.pack(self._endian+"H", 1)

        binary_message = binary_message + self._data.tostring(byteorder)  # struct.pack(fmt,*data)
        self._body_pack_size = len(binary_message)

        self._binary_body = binary_message


class ImageMessageMatlab(ImageMessage):
    def __init__(self, image, dim, spacing=[1, 1, 1], timestamp=None):
        try:
            data = np.asarray(image)
        except Exception as e:
            _print('ERROR, INVALID IMAGE. \n' + str(e))
            self._valid_message = False
            return
        data = data.reshape(dim)
        ImageMessage.__init__(self, data, spacing, timestamp)


if __name__ == "__main__":
    """
    Usage:
    pyIGTLink.py
    Run as local server sending random tissue data

    """

    if len(sys.argv) == 1:
        print("\n\n   Run as server, sending random data\n\n  ")
        server = PyIGTLink(localServer=True)

        samples = 500
        beams = 100
        k = 0

        while True:
            if server.is_connected():
                k = k+1
                print(k)
                _data = np.random.randn(samples, beams)*50+100
                # data[:, :, 1] = data[:, :, 1] + 90
                image_message = ImageMessage(_data)
                server.add_message_to_send_queue(image_message)
            time.sleep(0.1)

    elif len(sys.argv) == 2:
        print("\n\n   Run as server, sending moving circle \n\n  ")
        server = PyIGTLink(localServer=True)

        n = 500
        r = 90

        k = 0
        while True:
            if server.is_connected():
                k = k+1
                print(k)
                a = np.mod(10*k, n)
                b = np.mod((400*k)/n+30, n)
                y, x = np.ogrid[-a:n-a, -b:n-b]
                mask = x*x + y*y <= r*r

                _data = np.ones((n, n))
                _data[mask] = 255

                print(_data.shape)

                image_message = ImageMessage(_data)
                server.add_message_to_send_queue(image_message)
            time.sleep(0.1)
