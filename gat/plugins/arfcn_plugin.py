# -*- coding: utf-8 -*-
import grgsm

from gat.core.plugin.interface import plugin, arg, cmd, PluginBase


@plugin(name='ARFCN Calculator', description='Prints frequency information for an ARFCN.')
class ArfcnPlugin(PluginBase):
    @arg('arfcn', action="store", type=int, nargs="?", help="ARFCN to display information for.")
    @arg('-b', action="store", dest="band", choices=(grgsm.arfcn.get_bands()), help="Frequency band of the ARFCN.")
    @cmd(name='channelinfo', description='Prints frequency information for an ARFCN.')
    def channelinfo(self, args):
        """
        Print channel info for an ARFCN.
        """
        if args.arfcn is not None:
            if args.band is not None:
                self.__print_arfcn_info(args.arfcn, args.band)
            else:
                for b in grgsm.arfcn.get_bands():
                    self.__print_arfcn_info(args.arfcn, b)
        else:
            if args.band is not None:
                # print the starting channels and end channels of the band
                arfcn_range = grgsm.arfcn.get_arfcn_ranges(args.band)[0]
                arfcn_start = arfcn_range[0]
                f_down_start = grgsm.arfcn.arfcn2downlink(arfcn_start, args.band) / 1e6
                f_up_start = grgsm.arfcn.arfcn2uplink(arfcn_start, args.band) / 1e6

                arfcn_end = arfcn_range[1]
                f_down_end = grgsm.arfcn.arfcn2downlink(arfcn_end, args.band) / 1e6
                f_up_end = grgsm.arfcn.arfcn2uplink(arfcn_end, args.band) / 1e6

                self.printmsg("ARFCN %i-%i (%s): Downlink: %4.1f-%4.1f MHz, Uplink: %4.1f-%4.1f MHz"
                              % (arfcn_start, arfcn_end, args.band, f_down_start, f_down_end, f_up_start, f_up_end))
            else:
                for band in grgsm.arfcn.get_bands():
                    arfcn_range = grgsm.arfcn.get_arfcn_ranges(band)[0]
                    # print the starting channels and end channels of the band
                    arfcn_start = arfcn_range[0]
                    f_down_start = grgsm.arfcn.arfcn2downlink(arfcn_start, band) / 1e6
                    f_up_start = grgsm.arfcn.arfcn2uplink(arfcn_start, band) / 1e6

                    arfcn_end = arfcn_range[1]
                    f_down_end = grgsm.arfcn.arfcn2downlink(arfcn_end, band) / 1e6
                    f_up_end = grgsm.arfcn.arfcn2uplink(arfcn_end, band) / 1e6

                    self.printmsg("ARFCN %i-%i (%s): Downlink: %4.1f-%4.1f MHz, Uplink: %4.1f-%4.1f MHz"
                                  % (arfcn_start, arfcn_end, band, f_down_start, f_down_end, f_up_start, f_up_end))

    @arg('freq', action="store", type=float, help="Frequency to display information for.")
    @arg('-b', action="store", dest="band", choices=(grgsm.arfcn.get_bands()))
    @cmd(name='frequencyinfo', description='Prints information for a frequency.')
    def frequencyinfo(self, args):
        """
        Print information for a frequency.
        """
        if 200 < args.freq < 4000:
            args.freq *= 1e6

        if args.band is not None:
            if not grgsm.arfcn.is_valid_downlink(args.freq, args.band) and not grgsm.arfcn.is_valid_uplink(args.freq,
                                                                                                           args.band):
                self.printmsg("Freq %4.1f MHz is NOT valid in band %s" % (args.freq, args.band))

            if grgsm.arfcn.is_valid_downlink(args.freq, args.band):
                channel = grgsm.arfcn.downlink2arfcn(args.freq, args.band)
                self.printmsg(
                    "Freq %4.1f MHz (Downlink) is ARFCN %i in band %s" % (args.freq / 1e6, channel, args.band))
            if grgsm.arfcn.is_valid_uplink(args.freq, args.band):
                channel = grgsm.arfcn.uplink2arfcn(args.freq, args.band)
                self.printmsg("Freq %4.1f MHz (Uplink) is ARFCN %i in band %s" % (args.freq / 1e6, channel, args.band))
        else:
            for b in grgsm.arfcn.get_bands():
                if not grgsm.arfcn.is_valid_downlink(args.freq, b) and not grgsm.arfcn.is_valid_uplink(args.freq, b):
                    self.printmsg("Freq %4.1f MHz is NOT valid in band %s" % (args.freq / 1e6, b))

                if grgsm.arfcn.is_valid_downlink(args.freq, b):
                    channel = grgsm.arfcn.downlink2arfcn(args.freq, b)
                    self.printmsg("Freq %4.1f MHz (Downlink) is ARFCN %i in band %s" % (args.freq / 1e6, channel, b))
                if grgsm.arfcn.is_valid_uplink(args.freq, b):
                    channel = grgsm.arfcn.uplink2arfcn(args.freq, b)
                    self.printmsg("Freq %4.1f MHz (Uplink) is ARFCN %i in band %s" % (args.freq / 1e6, channel, b))

    def __print_arfcn_info(self, arfcn, band):
        if grgsm.arfcn.is_valid_arfcn(arfcn, band):
            f_down = grgsm.arfcn.arfcn2downlink(arfcn, band) / 1e6
            f_up = grgsm.arfcn.arfcn2uplink(arfcn, band) / 1e6

            self.printmsg("ARFCN %i (%s): Downlink: %4.1f MHz, Uplink: %4.1f MHz"
                          % (arfcn, band, f_down, f_up))
        else:
            self.printmsg("ARFCN %i is NOT valid in %s" % (arfcn, band))
