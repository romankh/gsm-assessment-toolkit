# -*- coding: utf-8 -*-
from abc import abstractmethod


class HlrLookupAdapter(object):
    @abstractmethod
    def __init__(self, config_provider):
        pass

    @abstractmethod
    def lookup(self, msisdn):
        """
        :param msisdn:
        :return:
        :rtype: HlrResult
        """
        pass

    @abstractmethod
    def get_balance(self):
        pass


class HlrResult(dict):
    def __init__(self, iterable=None, **kwargs):
        hlrkeys = [('id', None), ('msisdncountrycode', None), ('msisdn', None), ('statuscode', None),
                   ('subscriberstatus', None), ('imsi', None), ('mcc', None), ('mnc', None), ('msin', None),
                   ('servingmsc', None), ('servinghlr', None), ('originalnetworkname', None),
                   ('originalcountryname', None), ('originalcountrycode', None),
                   ('originalcountryprefix', None), ('roamingnetworkname', None), ('roamingcountryname', None),
                   ('roamingcountrycode', None),
                   ('roamingcountryprefix', None), ('isvalid', None), ('isroaming', None), ('isported', None),
                   ('usercharge', None)]
        super(HlrResult, self).__init__(hlrkeys, **kwargs)
