import requests

from gat.core.adapterinterfaces.hlr import HlrLookupAdapter, HlrResult


class HlrLookupError(Exception):
    """
    Signals an exception while performing a HLR lookup.
    """
    pass


class HlrLookupsComAdapter(HlrLookupAdapter):
    """
    Provides methods for performing lookups at hlrlookups.com
    """

    def __init__(self, config_provider):
        super(HlrLookupsComAdapter, self).__init__(config_provider)
        self.__username = config_provider.get("hlrlookups.com", "user")
        self.__password = config_provider.get("hlrlookups.com", "password")

    ACTION_LOOKUP = 'submitSyncLookupRequest'
    ACTION_BALANCE = 'getBalance'
    api_url = 'https://www.hlr-lookups.com/api'

    #  MSISDN in international format, e.g. +491780000000.
    def lookup(self, msisdn):
        """
        Perform a lookup at hlrlookups.com

        :param msisdn: the phone number in international format, e.g. +491780000000.
        :return: a dictionary with the retrieved values
        :rtype: HlrResult
        """
        params = {'action': self.ACTION_LOOKUP,
                  'msisdn': msisdn,
                  'username': self.__username,
                  'password': self.__password}

        response = requests.get(self.api_url, params=params)
        if response.status_code != 200:
            msg = 'Lookup request to hlrlookups.com failed with status code %s' % response.status_code
            raise HlrLookupError(msg)

        data = response.json()

        if not data['success']:
            msg = 'Lookup request to hlrlookups.com was not successful:\n'
            for m in data['errors']['globalErrors']:
                msg += 'global error: %s\n' % m
            for m in data['errors']['fieldErrors']:
                msg += 'field error: %s\n' % m
            raise HlrLookupError(msg)

        r = data['results'][0]

        result = HlrResult()

        if data['results'][0]:
            result['id'] = r['id']
            result['msisdncountrycode'] = r['msisdncountrycode']
            result['msisdn'] = r['msisdn']
            result['statuscode'] = r['statuscode']
            result['subscriberstatus'] = r['subscriberstatus']
            result['imsi'] = r['imsi']
            result['mcc'] = r['mcc']
            result['mnc'] = r['mnc']
            result['msin'] = r['msin']
            result['servingmsc'] = r['servingmsc']
            result['servinghlr'] = r['servinghlr']
            result['originalnetworkname'] = r['originalnetworkname']
            result['originalcountryname'] = r['originalcountryname']
            result['originalcountrycode'] = r['originalcountrycode']
            result['originalcountryprefix'] = r['originalcountryprefix']
            result['roamingnetworkname'] = r['roamingnetworkname']
            result['roamingcountryname'] = r['roamingcountryname']
            result['roamingcountrycode'] = r['roamingcountrycode']
            result['roamingcountryprefix'] = r['roamingcountryprefix']
            result['isvalid'] = r['isvalid']
            result['isroaming'] = r['isroaming']
            result['isported'] = r['isported']
            result['usercharge'] = r['usercharge']
        return result

    # returns balance in euro
    def get_balance(self):
        """
        Get the current balance at hlrlookups.com in EURO.
        :param username: username at hlrlookups.com
        :param password: password at hlrlookups.com
        :return: balance in EURO
        """

        username, password = "", ""

        params = {'action': self.ACTION_BALANCE,
                  'username': self.__username,
                  'password': self.__password}

        response = requests.get(self.api_url, params=params)
        if response.status_code != 200:
            msg = 'Balance request to hlrlookups.com failed with status code %s' % response.status_code
            raise HlrLookupError(msg)

        data = response.json()
        if not data['success']:
            msg = 'Lookup request to hlrlookups.com was not successful:\n'
            for m in data['errors']['globalErrors']:
                msg += 'global error: %s\n' % m
            for m in data['errors']['fieldErrors']:
                msg += 'field error: %s\n' % m
            raise HlrLookupError(msg)

        return data['results']['balance']
