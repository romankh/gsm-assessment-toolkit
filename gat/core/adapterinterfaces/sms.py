# -*- coding: utf-8 -*-
from abc import abstractmethod


class SmsAdapter(object):
    @abstractmethod
    def __init__(self, config_provider):
        pass

    @abstractmethod
    def register_read_callback(self, callback):
        pass

    @abstractmethod
    def send(self, sms_type, msisdn, text):
        pass

    @abstractmethod
    def unregister_read_callback(self):
        pass
