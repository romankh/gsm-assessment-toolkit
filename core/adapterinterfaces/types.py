# -*- coding: utf-8 -*-

from enum import Enum, unique


@unique
class SmsType(Enum):
    SMS = 0
    SMS_Report = 1
    CLASS0 = 2
    CLASS0_Report = 3
    TYPE0 = 4
    TYPE0_Report = 5
    MWIA = 6
    MWID = 7
    MWID_Report = 8

    @staticmethod
    def get_description(sms_type):
        if sms_type == SmsType.SMS:
            return "Regular SMS"
        elif sms_type == SmsType.SMS_Report:
            return "Regular SMS with delivery report"
        elif sms_type == SmsType.CLASS0:
            return "Class 0 SMS (Flash SMS)"
        elif sms_type == SmsType.CLASS0_Report:
            return "Class 0 SMS (Flash SMS) with delivery report"
        elif sms_type == SmsType.TYPE0:
            return "Type 0 SMS (Silent SMS)"
        elif sms_type == SmsType.TYPE0_Report:
            return "Type 0 SMS (Silent SMS) with delivery report"
        elif sms_type == SmsType.MWIA:
            return "Message Waiting Indicator Activate message"
        elif sms_type == SmsType.MWID:
            return "Message Waiting Indicator Deactivate message"
        elif sms_type == SmsType.MWID_Report:
            return "Message Waiting Indicator Deactivate message with delivery report"
        else:
            return "No description found"

    @staticmethod
    def get_names():
        names = []
        for item in SmsType:
            names.append(item.name)
        return names
