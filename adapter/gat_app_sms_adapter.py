# -*- coding: utf-8 -*-
import socket
import thread

from core.adapterinterfaces.sms import SmsAdapter
from core.adapterinterfaces.types import SmsType


class GatAppSmsAdapter(SmsAdapter):
    def __init__(self, config_provider, timeout=10):
        super(GatAppSmsAdapter, self).__init__(config_provider, timeout)
        self.__connected = False
        self.__config_provider = config_provider
        self.__gat_host = config_provider.get('gat-app', 'host')
        self.__gat_port = config_provider.getint('gat-app', 'port')
        self.__callback = None
        self.__read_thread = None
        self.__timeout = timeout

    def register_read_callback(self, callback):
        if not self.__connected:
            self.__connect()
        self.__callback = callback

    def send(self, sms_type, msisdn, text):
        if sms_type not in SmsType:
            self.__handle_message("Unrecognized SMS type: %s" % sms_type)
            return

        if not self.__connected:
            self.__connect()

        if self.__connected:
            cmd = "sms-send#{0}#{1}#{2}\n".format(sms_type.value, msisdn, (text or ''))
            self.__sock.send(cmd)
        else:
            self.__handle_message("Error: not connected")

        # if no read callback registered, disconnect
        if self.__callback is None:
            self.__disconnect()

    def unregister_read_callback(self):
        if self.__connected:
            self.__disconnect()
        self.__callback = None

    def __connect(self):
        remote_address = (self.__gat_host, self.__gat_port)
        try:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__sock.settimeout(self.__timeout)
            self.__sock.connect(remote_address)
        except socket.error as msg:
            self.__handle_message("Connection to GAT-App failed: %s" % msg)
            self.__sock.close()
            self.__sock = None
            return False

        # start a new thread for the communication
        self.__connected = True
        self.__read_thread = thread.start_new_thread(self.__read_handler, ())

        return True

    def __disconnect(self):
        """
        Disconnect from app.
        """
        self.__sock.send("quit\n")
        self.__sock.close()
        self.__connected = False

    def __read_handler(self):
        """
        Handler for responses from the connection to the app.
        """
        while self.__connected:
            msg = None
            try:
                msg = self.__sock.recv(1024)
            except Exception, e:
                print "Error occurred: %s " % e
                pass

            if msg is None:
                break
            else:
                self.__handle_message(msg)

    def __handle_message(self, msg):  # Todo: Make response independent from implementation, i.e. use response codes
        if self.__callback is not None:
            self.__callback(msg)
