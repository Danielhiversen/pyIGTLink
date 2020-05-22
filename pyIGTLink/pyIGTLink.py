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
import string

if sys.version_info >= (3, 0):
    import socketserver as SocketServer
else:
    import SocketServer

IGTL_HEADER_VERSION = 1
IGTL_IMAGE_HEADER_VERSION = 1
IGTL_HEADER_SIZE = 58
IGTL_EXTENDED_HEADER_SIZE = 12

IGTL_TYPE_UNDEFINED = "?"
IGTL_TYPE_SERVER = "S"
IGTL_TYPE_CLIENT = "C"

class PyIGTLink():

  def __init__(self):
      self.buffer_size = 100
      self.server_stop = False
      self.server_running = False

      self.connection_type = IGTL_TYPE_UNDEFINED

      self._shut_down = False
      self._running = False
      self._connected = False

      self.incoming_messages = {}
      self.message_queue = collections.deque(maxlen=self.buffer_size)

      self.lock_received_messages = threading.Lock()
      self.lock_server_thread = threading.Lock()

  def start(self):
      return False

  def stop(self):
      return False

  def send_message(self, message, wait=False):
      return self._add_message_to_send_queue(message, wait)

  def get_latest_messages(self):
      messages = []
      with self.lock_received_messages:
          for device_name in self.incoming_messages:
              message = self.incoming_messages[device_name]
              messages.append(message)
          self.incoming_messages = {}
      return messages

  def _add_message_to_send_queue(self, message, wait=False):
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
          return False
      return True

  def _send_queued_message_from_socket(self, socket):
      with self.lock_server_thread:
          if len(self.message_queue) > 0:
            message = self.message_queue.popleft()
            response_data = message.get_binary_message()
            try:
                socket.sendall(response_data)
            except Exception as exp:
                self.update_connected_status(False)
                _print('ERROR, FAILED TO SEND DATA. \n'+str(exp))

  def _send_message_from_socket(self, message, socket):
      if socket is None:
          return False
      binary_message = message.get_binary_message()
      try:
          socket.sendall(binary_message)
      except Exception as exp:
          self.update_connected_status(False)
          _print('ERROR, FAILED TO SEND DATA. \n'+str(exp))
          return

  def _receive_message_from_socket(self, socket):
      header = []
      len_count = 0
      header = b""
      while len_count < IGTL_HEADER_SIZE:
          header += socket.recv(IGTL_HEADER_SIZE - len_count)
          if (len(header) == 0):
            return False
          len_count = len(header)

      base_message = MessageBase()
      package = base_message.unpack(header)
      body_size = package['body_size']
      type = package['type']

      body = b""
      len_count = 0
      while len_count < body_size:
          body += socket.recv(body_size - len_count)
          if (len(body) == 0):
            return False
          len_count = len(body)
      try:
        message = None
        if type == "TRANSFORM":
            message = TransformMessage(np.eye(4))
        if type == "IMAGE":
            message = ImageMessage(np.zeros((2, 2), dtype=np.uint8))
        if type == "STRING":
            message = StringMessage("")
      except Exception as e:
        print(e)

      if message is None:
        #TODO: error message
        return False

      try:
        message.unpack(header)
        valid = message.unpack_body(body)
      except Exception as e:
        print(e)

      if not valid:
          return False

      device_name = message._device_name
      with self.lock_received_messages:
          self.incoming_messages[device_name] = message
      return True

  def is_connected(self):
      return self._connected

  def update_connected_status(self, val):
      self._connected = val


class PyIGTLinkServer(SocketServer.TCPServer, PyIGTLink):

    """ For streaming data over TCP with IGTLink"""
    def __init__(self, port=18944, localServer=False, iface='eth0'):
        """
        port - port number
        """
        PyIGTLink.__init__(self)

        self.connection_type = IGTL_TYPE_SERVER

        if localServer:
            host = "127.0.0.1"
        else:
            if sys.platform.startswith('win32'):
                host = socket.gethostbyname(socket.gethostname())
            elif sys.platform.startswith('linux'):
                import fcntl
                soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    ifname = iface
                    host = socket.inet_ntoa(fcntl.ioctl(soc.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])
                    # http://code.activestate.com/recipes/439094-get-the-ip-address-associated-with-a-network-inter/
                except: # noqa
                    ifname = 'lo'
                    host = socket.inet_ntoa(fcntl.ioctl(soc.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])
            else:
                # the iface can be also an ip address in systems where the previous code won't work
                host = iface

        SocketServer.TCPServer.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self, (host, port), TCPRequestHandler)

        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def start(self):
        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        thread = threading.Thread(target=self._print_ip_adress_and_port_no)
        thread.daemon = True
        thread.start()

    def stop(self):
      self.close_server()

    def get_ip_adress(self):
        return self.server_address[0]

    def get_port_no(self):
        return self.server_address[1]

    def _signal_handler(self, signum, stackframe):
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.close_server()
            _print('YOU KILLED ME, BUT I CLOSED THE SERVER BEFORE I DIED')
            sys.exit(signum)

    def close_server(self):
        """Will close connection and shutdown server"""
        self._connected = False
        with self.lock_server_thread:
            self.server_stop = True
        self.shutdown()
        self.server_close()
        _print("\nServer closed\n")

    def _print_ip_adress_and_port_no(self):
        while True:
            while not self._connected:
                with self.lock_server_thread:
                    if self.server_stop:
                        _print("No connections\nIp adress: " + str(self.get_ip_adress()) + "\nPort number: " + str(self.get_port_no()))
                        break
                time.sleep(5)
            time.sleep(10)
            with self.lock_server_thread:
                if self.server_stop:
                    self.server_running = True
                    break


class PyIGTLinkClient(PyIGTLink):
    def __init__(self, host="127.0.0.1", port=18944):
        PyIGTLink.__init__(self)

        self.connection_type = IGTL_TYPE_CLIENT

        self.socket = None
        self.host = host
        self.port = port
        self._client_thread = threading.Thread(target=self._client_thread_function)
        self._client_thread.daemon = True

        self.lock_client_thread = threading.Lock()

    def start(self):
        if self._running:
          return True
        self._client_thread.start()
        with self.lock_client_thread:
            self.server_stop = False
            self.server_running = False
            self._running = True
        return True

    def stop(self):
        if not self._running:
          return True

        with self.lock_client_thread:
          self.server_stop = True
        while True:
          with self.lock_client_thread:
            if self.server_running:
              return True

        self._connected = False
        self._running = False
        return False

    def _client_thread_function(self):
        while True:
            with self.lock_client_thread:
                if self.server_stop:
                    if self.socket is not None:
                      self.socket.close()
                    self.server_running = True
                    break

            if self.socket is None:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(0.1)
                self._connected = False

            if not self._connected:
                try:
                  self.socket.connect((self.host, self.port))
                  self._connected = True
                except Exception as exp:
                  self.socket = None

            if not self._connected:
             continue

            try:
              if not self._receive_message_from_socket(self.socket):
                self._connected = False
                continue
            except Exception as exp:
              pass

            self._send_queued_message_from_socket(self.socket)

class TCPRequestHandler(SocketServer.BaseRequestHandler):
    """
    Help class for PyIGTLink
    """
    def handle(self):
        self.server.update_connected_status(True)
        self.request.settimeout(0.1)
        try:
            self.server._receive_message_from_socket(self.request)
        except Exception as exp:
            pass

        # Send
        if len(self.server.message_queue) > 0:
            with self.server.lock_server_thread:
                message = self.server.message_queue.popleft()
                response_data = message.get_binary_message()
                try:
                    self.request.sendall(response_data)
                except Exception as exp:
                    self.server.update_connected_status(False)
                    _print('ERROR, FAILED TO SEND DATA. \n'+str(exp))

# Help functions and help classes:
def _print(text):
    print("**********PyIGTLink*********\n" + text + "\n****************************")


# http://openigtlink.org/protocols/v2_header.html
class MessageBase(object):
    """message"""
    def __init__(self):
        self._valid_message = False
        # Version number The version number field specifies the header format version. Currently the version number is 1.
        # Please note that this is different from the protocol version.
        self._version = IGTL_HEADER_VERSION
        # The type field is an ASCII character string specifying the type of the data contained in
        # the message body e.g. TRANSFORM. The length of the type name must be within 12 characters.
        self._type = ""
        # The device name field contains an ASCII character string specifying the name of the the message.
        self._device_name = ""
        # The timestamp field contains a 64-bit timestamp indicating when the data is generated.
        # Please refer http://openigtlink.org/protocols/v2_timestamp.html for the format of the 64-bit timestamp.
        self._timestamp = time.time() * 1000

        self._endian = ">"  # big-endian
        self.crc = None

        self._metadata_size = 0
        self._binary_body = None
        self._binary_head = None
        self._body_pack_size = 0
        self._body_size = 0

    def pack(self):
        binary_body = self.get_binary_body()
        self._body_size = self.get_body_pack_size()
        self.crc = CRC64(binary_body)
        _timestamp1 = int(self._timestamp / 1000)
        _timestamp2 = _igtl_nanosec_to_frac(int((self._timestamp / 1000.0 - _timestamp1)*10**9))
        binary_message = struct.pack(self._endian+"H", self._version)
        binary_message = binary_message + struct.pack(self._endian+"12s", self._type.encode('utf-8'))
        binary_message = binary_message + struct.pack(self._endian+"20s", self._device_name.encode('utf-8'))
        binary_message = binary_message + struct.pack(self._endian+"II", _timestamp1, _timestamp2)
        binary_message = binary_message + struct.pack(self._endian+"Q", self._body_size)
        binary_message = binary_message + struct.pack(self._endian+"Q", self.crc)

        self._binary_head = binary_message

    def unpack(self, message):
        s = struct.Struct('> H 12s 20s II Q Q')  # big-endian
        values = s.unpack(message)
        self._version = values[0]

        self._type = values[1].decode().rstrip(' \t\r\n\0')
        self._device_name = values[2].decode().rstrip(' \t\r\n\0')

        seconds = float(values[3])
        frac_of_second = int(values[4])

        nanoseconds = float(_igtl_frac_to_nanosec(frac_of_second))
        self._timestamp = seconds + (nanoseconds * 1e-9)

        self._body_size = values[5]
        valid = False
        return {'type': self._type,
                'device_name': self._device_name,
                'timestamp': self._timestamp,
                'valid': valid,
                'body_size': self._body_size}

    def unpack_extended_header(self, message):
        s = struct.Struct('> H H I I')  # big-endian
        values = s.unpack(message)
        self._extended_header_size = values[0]
        self._metadata_header_size = values[1]
        self._metadata_size = values[2]
        self._message_id = values[3]
        return {'metadata_size': self._metadata_size,
                'message_id': self._message_id,}

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
    def __init__(self, image, spacing=[1, 1, 1], timestamp=None, device_name=''):
        """
        Image package
        image - image data
        spacing - spacing in mm
        timestamp - milliseconds since 1970
        device_name - name of the image
        """

        MessageBase.__init__(self)
        self._valid_message = True
        self._type = "IMAGE"
        self._device_name = device_name
        if timestamp:
            self._timestamp = timestamp
        self._metadata_size = 0

        try:
            self._image = np.asarray(image)
        except Exception as exp:
            _print('ERROR, INVALID IMAGE. \n' + str(exp))
            self._valid_message = False
            return

        if len(self._image.shape) < 2:
            self._valid_message = False
            _print('ERROR, INVALID IMAGE SIZE. \n')
            return


# Only int8 is supported now
#        if self._image.dtype == np.int8:
#            self._datatype_s = 2
#            self._format_data = "b"
#        elif self._image.dtype == np.uint8:
#            self._datatype_s = 3
#            self._format_data = "B"
#        elif self._image.dtype == np.int16:
#            self._datatype_s = 4
#            self._format_data = "h"
#        elif self._image.dtype == np.uint16:
#            self._datatype_s = 5
#            self._format_data = "H"
#        elif self._image.dtype == np.int32:
#            self._datatype_s = 6
#            self._format_data = "i"
#        elif self._image.dtype == np.uint32:
#            self._datatype_s = 7
#            self._format_data = "I"
#        elif self._image.dtype == np.float32:
#            self._datatype_s = 10
#            self._format_data = "f"
#        elif self._image.dtype == np.float64:
#            self._datatype_s = 11
#            self._format_data = "f"
#        else:
#            pass
        self._image = np.array(self._image, dtype=np.uint8)
        self._datatype_s = 3
        self._format_data = "B"

        self._spacing = spacing
        self._matrix = np.identity(4)  # A matrix representing the origin and the orientation of the image.

    def pack_body(self):
        binary_message = struct.pack(self._endian+"H", IGTL_IMAGE_HEADER_VERSION)
        # Number of Image Components (1:Scalar, >1:Vector). (NOTE: Vector data is stored fully interleaved.)
        binary_message += struct.pack(self._endian+"B", self._image.shape[3])
        binary_message += struct.pack(self._endian+"B", self._datatype_s)

        if self._image.dtype.byteorder == "<":
            byteorder = "F"
            binary_message += struct.pack(self._endian+"B", 2)  # Endian for image data (1:BIG 2:LITTLE)
            # (NOTE: values in image header is fixed to BIG endian)
        else:
            self._image.dtype.byteorder == ">"
            byteorder = "C"
            binary_message += struct.pack(self._endian+"B", 1)  # Endian for image data (1:BIG 2:LITTLE)
            # (NOTE: values in image header is fixed to BIG endian)

        binary_message += struct.pack(self._endian+"B", 1)  # image coordinate (1:RAS 2:LPS)

        binary_message += struct.pack(self._endian+"H", self._image.shape[2])
        binary_message += struct.pack(self._endian+"H", self._image.shape[1])
        binary_message += struct.pack(self._endian+"H", self._image.shape[0])

        origin = np.zeros(3)
        norm_i = np.zeros(3)
        norm_j = np.zeros(3)
        norm_k = np.zeros(3)
        for i in range(3):
            norm_i[i] = self._matrix[i][0]
            norm_j[i] = self._matrix[i][1]
            norm_k[i] = self._matrix[i][2]
            origin[i] = self._matrix[i][3]

        binary_message += struct.pack(self._endian+"f", norm_i[0] * self._spacing[0])
        binary_message += struct.pack(self._endian+"f", norm_i[1] * self._spacing[0])
        binary_message += struct.pack(self._endian+"f", norm_i[2] * self._spacing[0])
        binary_message += struct.pack(self._endian+"f", norm_j[0] * self._spacing[1])
        binary_message += struct.pack(self._endian+"f", norm_j[1] * self._spacing[1])
        binary_message += struct.pack(self._endian+"f", norm_j[2] * self._spacing[1])
        binary_message += struct.pack(self._endian+"f", norm_k[0] * self._spacing[2])
        binary_message += struct.pack(self._endian+"f", norm_k[1] * self._spacing[2])
        binary_message += struct.pack(self._endian+"f", norm_k[2] * self._spacing[2])
        binary_message += struct.pack(self._endian+"f", origin[0])
        binary_message += struct.pack(self._endian+"f", origin[1])
        binary_message += struct.pack(self._endian+"f", origin[2])

        binary_message += struct.pack(self._endian+"H", 0)      # Starting index of subvolume
        binary_message += struct.pack(self._endian+"H", 0)      # Starting index of subvolume
        binary_message += struct.pack(self._endian+"H", 0)      # Starting index of subvolume

        binary_message += struct.pack(self._endian+"H", self._image.shape[0])  # number of pixels of subvolume
        binary_message += struct.pack(self._endian+"H", self._image.shape[1])
        if len(self._image.shape) > 2:
            binary_message += struct.pack(self._endian+"H", self._image.shape[2])
        else:
            binary_message += struct.pack(self._endian+"H", 1)

        binary_message += self._image.tostring(byteorder)  # struct.pack(fmt,*data)
        self._body_pack_size = len(binary_message)

        self._binary_body = binary_message

    def unpack_body(self, body):

        if self._version > 1:
          len_count = 0
          self.unpack_extended_header(body[:IGTL_EXTENDED_HEADER_SIZE])
        else:
          self._extended_header_size=0
          self._metadata_header_size=0

        header_portion_len = 12 + (12 * 4) + 12
        s_head = \
            struct.Struct('> H B B B B H H H f f f f f f f f f f f f H H H H H H')
        values_header = s_head.unpack(body[self._extended_header_size:self._extended_header_size + header_portion_len])

        numberOfComponents = values_header[1]
        endian = values_header[3]
        size_x = values_header[23]
        size_y = values_header[24]
        size_z = values_header[25]

        if endian == 2:
            endian = '<'
        else:
            endian = '>'

        if self._metadata_size + self._metadata_header_size > 0:
          values_img = body[self._extended_header_size + header_portion_len:-(self._metadata_size+self._metadata_header_size)]
        else:
          values_img = body[self._extended_header_size + header_portion_len:]

        dt = np.dtype(np.uint8)
        dt = dt.newbyteorder(endian)
        data = np.frombuffer(values_img, dtype=dt)

        self._image = np.reshape(data, [size_z, size_y, size_x, numberOfComponents])

        valid = True
        return valid


class Tdata(MessageBase):
    def __init__(self, msg, timestamp=None, device_name=''):
        MessageBase.__init__(self)
        self._valid_message = True
        self._name = "TDATA"
        self._device_name = device_name
        if timestamp:
            self._timestamp = timestamp

        self._data = np.asarray(msg, dtype=np.float32)

        self._data = np.array(self._data, dtype=np.float32)

        self._format_data = "f"

        self._matrix = self._data  # A matrix representing the origin pose.
        self._body_type = 4
        self._body_name = "input0"
        self._body_reserved = 5

    def pack_body(self):
        binary_message = struct.pack(self._endian + "20s", self._body_name.encode('utf-8'))
        binary_message += struct.pack(self._endian + "B", self._body_type)
        binary_message += struct.pack(self._endian + "B", self._body_reserved)
        binary_message += struct.pack(self._endian + self._format_data, self._matrix[0, 0])  # R11
        binary_message += struct.pack(self._endian + self._format_data, self._matrix[1, 0])  # R21
        binary_message += struct.pack(self._endian + self._format_data, self._matrix[2, 0])  # R31

        binary_message += struct.pack(self._endian + self._format_data, self._matrix[0, 1])  # R12
        binary_message += struct.pack(self._endian + self._format_data, self._matrix[1, 1])  # R22
        binary_message += struct.pack(self._endian + self._format_data, self._matrix[2, 1])  # R32

        binary_message += struct.pack(self._endian + self._format_data, self._matrix[0, 2])  # R13
        binary_message += struct.pack(self._endian + self._format_data, self._matrix[1, 2])  # R23
        binary_message += struct.pack(self._endian + self._format_data, self._matrix[2, 2])  # R33

        binary_message += struct.pack(self._endian + self._format_data, self._matrix[0, 3])  # TX
        binary_message += struct.pack(self._endian + self._format_data, self._matrix[1, 3])  # TY
        binary_message += struct.pack(self._endian + self._format_data, self._matrix[2, 3])  # TZ

        self._body_pack_size = len(binary_message)

        self._binary_body = binary_message


class TransformMessage(MessageBase):
    def __init__(self, tform, timestamp=None, device_name=''):
        """
        Transform package
        tform - tform data
        timestamp - milliseconds since 1970
        device_name - name of the tool
        """

        MessageBase.__init__(self)
        self._valid_message = True
        self._type = "TRANSFORM"
        self._device_name = device_name
        if timestamp:
            self._timestamp = timestamp

        try:
            self._matrix = np.asarray(tform, dtype=np.float32)
        except Exception as exp:
            _print('ERROR, INVALID TRANSFORM. \n' + str(exp))
            self._valid_message = False
            return

        if len(self._matrix.shape) != 2:
            self._valid_message = False
            _print('ERROR, INVALID TRANSFORM SIZE. \n')
            return


# transforms are floats
#        if self._matrix.dtype == np.int8:
#            self._datatype_s = 2
#            self._format_data = "b"
#        elif self._matrix.dtype == np.uint8:
#            self._datatype_s = 3
#            self._format_data = "B"
#        elif self._matrix.dtype == np.int16:
#            self._datatype_s = 4
#            self._format_data = "h"
#        elif self._matrix.dtype == np.uint16:
#            self._datatype_s = 5
#            self._format_data = "H"
#        elif self._matrix.dtype == np.int32:
#            self._datatype_s = 6
#            self._format_data = "i"
#        elif self._matrix.dtype == np.uint32:
#            self._datatype_s = 7
#            self._format_data = "I"
#        elif self._matrix.dtype == np.float32:
#            self._datatype_s = 10
#            self._format_data = "f"
#        elif self._matrix.dtype == np.float64:
#            self._datatype_s = 11
#            self._format_data = "f"
#        else:
#            pass
        self._matrix = np.array(self._matrix, dtype=np.float32) # A matrix representing the origin pose.
        self._datatype_s = 10
        self._format_data = "f"

    def pack_body(self):
        # binary_message = struct.pack(self._endian+"H", IGTL_TRANSFORM_HEADER_VERSION)
        # transform data, following protocol specification
        binary_message = struct.pack(self._endian + "f", self._matrix[0, 0])  # R11
        binary_message += struct.pack(self._endian + "f", self._matrix[1, 0])  # R21
        binary_message += struct.pack(self._endian + "f", self._matrix[2, 0])  # R31

        binary_message += struct.pack(self._endian + "f", self._matrix[0, 1])  # R12
        binary_message += struct.pack(self._endian + "f", self._matrix[1, 1])  # R22
        binary_message += struct.pack(self._endian + "f", self._matrix[2, 1])  # R32

        binary_message += struct.pack(self._endian + "f", self._matrix[0, 2])  # R13
        binary_message += struct.pack(self._endian + "f", self._matrix[1, 2])  # R23
        binary_message += struct.pack(self._endian + "f", self._matrix[2, 2])  # R33

        binary_message += struct.pack(self._endian + "f", self._matrix[0, 3])  # TX
        binary_message += struct.pack(self._endian + "f", self._matrix[1, 3])  # TY
        binary_message += struct.pack(self._endian + "f", self._matrix[2, 3])  # TZ

        self._body_pack_size = len(binary_message)

        self._binary_body = binary_message

    def unpack_body(self, message):
        s = struct.Struct('> f f f f f f f f f f f f')
        values = s.unpack(message)
        self._matrix = np.asarray([[values[0], values[3], values[6], values[9]],
                                   [values[1], values[4], values[7], values[10]],
                                   [values[2], values[5], values[8], values[11]],
                                   [0, 0, 0, 1]])

        valid = True
        return valid

class StringMessage(MessageBase):
    def __init__(self, string, timestamp=None, device_name='', encoding=3):

        MessageBase.__init__(self)
        self._valid_message = True
        self._type = "STRING"
        if timestamp:
            self._timestamp = timestamp
        self._device_name = device_name
        self._encoding = encoding  # Character encoding type as MIBenum value. Default=3 (US-ASCII).
        self._string = string

    def pack_body(self):
        binary_message = struct.pack(self._endian+"H", self._encoding)
        binary_message += struct.pack(self._endian+"H", len(self._string))
        binary_message += self._string.encode("utf-8")

        self._body_pack_size = len(binary_message)
        self._binary_body = binary_message

    def unpack_body(self, message):
        header_portion_len = 2 + 2
        s_head = struct.Struct('> H H')

        values_header = s_head.unpack(message[:header_portion_len])
        self._encoding = values_header[0]
        self._string = str(message[header_portion_len:])

        valid = True
        return valid

class ImageMessageMatlab(ImageMessage):
    def __init__(self, image, dim, spacing=[1, 1, 1], timestamp=None):
        """
        Image package from Matlab
        image - image data as vector  reshape(data,1,dim(1)*dim(2))
        dim - image dimension  [dim(1), dim(2)]
        spacing - spacing in mm
        timestamp - milliseconds since 1970
        """
        try:
            data = np.asarray(image)
        except Exception as e:
            _print('ERROR, INVALID IMAGE. \n' + str(e))
            self._valid_message = False
            return
        data = data.reshape(dim)
        ImageMessage.__init__(self, data, spacing, timestamp)


# http://slicer-devel.65872.n3.nabble.com/OpenIGTLinkIF-and-CRC-td4031360.html
CRC64 = crcmod.mkCrcFun(0x142F0E1EBA9EA3693, rev=False, initCrc=0x0000000000000000, xorOut=0x0000000000000000)


# https://github.com/openigtlink/OpenIGTLink/blob/cf9619e2fece63be0d30d039f57b1eb4d43b1a75/Source/igtlutil/igtl_util.c#L168
def _igtl_nanosec_to_frac(nanosec):
    base = 1000000000  # 10^9
    mask = 0x80000000
    r = 0x00000000
    while mask:
        base += 1
        base >>= 1
        if (nanosec >= base):
            r |= mask
            nanosec = nanosec - base
        mask >>= 1
    return r

# https://github.com/openigtlink/OpenIGTLink/blob/cf9619e2fece63be0d30d039f57b1eb4d43b1a75/Source/igtlutil/igtl_util.c#L193
def _igtl_frac_to_nanosec(frac):
    base = 1000000000 # 10^9
    mask = 0x80000000
    r = 0x00000000
    while mask:
        base += 1
        base >>= 1
        r += base if (frac & mask) else 0
        mask >>= 1
    return r


if __name__ == "__main__":
    """
    Usage:
    pyIGTLink.py
    Run as local server sending random tissue data

    """
    if len(sys.argv) == 1:
        print("\n\n   Run as server, sending random data\n\n  ")
        server = PyIGTLinkServer(localServer=True)
        server.start()

        samples = 500
        beams = 100
        k = 0

        while True:
            if server.is_connected():
                k = k+1
                print(k)
                _data = np.random.randn(samples, beams)*50+100
                # data[:, :, 1] = data[:, :, 1] + 90
                image_message = ImageMessage(_data, device_name="ImageMessage")
                transform_message = TransformMessage(np.random.rand(4,4).astype(dtype=np.float32), device_name="TransformMessage")
                string_message = StringMessage("TestingString_"+str(k), device_name="StringMessage")
                server.send_message(image_message)
                server.send_message(transform_message)
                server.send_message(string_message)
                messages = server.get_latest_messages()
                for message in messages:
                  print(message._device_name)

            time.sleep(0.1)

    elif len(sys.argv) == 2:
        print("\n\n   Run as server, sending moving circle \n\n  ")
        server = PyIGTLinkServer(localServer=True)

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

                image_message = ImageMessage(_data, device_name="OpenIGTLink")
                server._add_message_to_send_queue(image_message)
            time.sleep(0.1)
