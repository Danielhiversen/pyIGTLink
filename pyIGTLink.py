# -*- coding: utf-8 -*-
"""
Created on Tue Nov  3 19:17:05 2015

@author: dahoiv
"""

 IGTL_IMAGE_HEADER_VERSION = 1


class pyDataExport(SocketServer.TCPServer):
        """ For streaming data over TCP with GE-protocol"""
        def __init__(self,protocolVer=3,port=6543,localServer=False):
                """
                protocolVer - version of streaming protocol, latest will always be default
                              protocolVer=1:
                                ProtocolVersionRev     2
                                ProtocolVersionYear  2013
                                ProtocolVersionDay     04
                                ProtocolVersionMonth   03
                
                              protocolVer=2:
                                ProtocolVersionRev     2
                                ProtocolVersionYear  2013
                                ProtocolVersionDay     22
                                ProtocolVersionMonth   05

                              protocolVer=3:

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


                self._protocolVer=protocolVer

                self._packet_queue=collections.deque(maxlen=buffer_size)
                self._lock_packet_queue = threading.Lock()

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

        def AddPacketToSendQueue(self,packet,wait=False):
                """
                Returns True if sucessfull
                """
                if not isinstance(packet,Packet) or not packet.IsValid():
                        _Print("Warning: Only accepts valid packets of class Packet")
                        return False
        
                if self._connected:
                        with self._lock_packet_queue:
                                self._packet_queue.append(packet)#copy.deepcopy(packet))
	                while wait and len(self._packet_queue)>0:
	                        time.sleep(0.001)

                        return True
                else:
                        if len(self._packet_queue)>0:
                                with self._lock_packet_queue:
                                        self._packet_queue=collections.clear()
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
                _Print( "\nServer closed\n")

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
        Help class for pyDataExport
        """
        def handle(self):
                self.server._connected=True
                while True :
                        if len(self.server._packet_queue)>0:
                                with self.server._lock_packet_queue:
                                        packet=self.server._packet_queue.popleft()
                                        response_data=packet.GetBinaryPacket(self.server._protocolVer)
                                        #print "Send: " + str(packet._timestamp)
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





class Packet(object):
    pass



#http://openigtlink.org/protocols/v2_header.html
class ImageMessage(Packet):   
\