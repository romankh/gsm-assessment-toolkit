# -*- coding: utf-8 -*-
from adapter.hlrlookups_com_adapter import HlrLookupsComAdapter, HlrLookupError
from core.plugin.interface import plugin, PluginBase, arg, cmd, subcmd


@plugin(name='HLR Lookup', description='Performs HLR lookup.')
class HlrlookupPlugin(PluginBase):
    @cmd(name="hlr", description="Lookup a phone number in HLR using hlr-lookup.com.", parent=True)
    def hlr(self, args):
        pass

    @arg('msisdn', action="store", help="MSISDN to query (i.e. +43123456789).")
    @subcmd(name="lookup", help="Lookup a phone number in HLR using hlr-lookup.com.", parent="hlr")
    def hlr_lookup(self, args):
        """
        Perform a lookup at hlrlookups.com
        """
        adapter = HlrLookupsComAdapter(self._config_provider)
        try:
            result = adapter.lookup(args.msisdn)
            output = "HLR lookup result for %s (ID: %s):\n\n" % (result['msisdn'], result['id'])
            output += "Valid: %s\n" % result['isvalid']
            output += "Status: %s\n" % result['subscriberstatus']
            output += "MCC / MNC: %s %s\n" % (result['mcc'], result['mnc'])
            output += "IMSI: %s\n" % result['imsi']
            output += "Network (Country): %s (%s)\n" % (result['originalnetworkname'], result['originalcountryname'])
            output += "Serving MSC / HLR: %s / %s\n" % (result['servingmsc'], result['servinghlr'])
            output += "Is roaming: %s\n" % result['isroaming']
            if result['isroaming'] == 'Yes':
                output += "Roaming Network (Country): %s (%s)\n" % (result['roamingnetworkname'],
                                                                    result['roamingcountryname'])
            self.printmsg(output)

        except HlrLookupError as e:
            self.printmsg("ERROR: HLR lookup of %s failed" % args.msisdn)
            self.printmsg("Message was: %s" % e.message)

    @subcmd(name='balance', help='Lookup your account balance at hlr-lookup.com.', parent="hlr")
    def hlr_balance(self, args):
        """
        Get the current balance in EURO from hlrlookups.com
        """
        adapter = HlrLookupsComAdapter(self._config_provider)
        try:
            result = adapter.get_balance()
            self.printmsg("Current balance is: EUR %.2f" % float(result))

        except HlrLookupError as e:
            self.printmsg("ERROR: HLR balance inquiry failed")
            self.printmsg("Message was: %s" % e.message)
