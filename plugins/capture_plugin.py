# -*- coding: utf-8 -*-
import signal
from core.common import arfcn_converter
from adapter.grgsm.capture import grgsm_capture
from core.plugin.interface import plugin, arg_group, arg, PluginBase, arg_exclusive, cmd


@plugin(name='Capture Plugin', description='Captures transmissions.')
class CapturePlugin(PluginBase):
    @arg_group(name="Capturing", args=[
        arg("--gsmtap", action="store_true", dest="gsmtap", help="Output to GSMTap.", default=False),
        arg("--print-bursts", action="store_true", dest="print_bursts", help="Print captured bursts.",
            default=False),
        arg("--length", action="store", dest="length", type=int, help="Length of the record in seconds."),
        arg("--cfile", action="store_path", dest="cfile", help="cfile."),
        arg("--bursts", action="store_path", dest="bursts", help="bursts."),
    ])
    @arg_group(name="RTL-SDR configuration", args=[
        arg("-p", action="store", dest="ppm", type=int, help="Set ppm. Default: value from config file."),
        arg("-s", action="store", dest="samp_rate", type=float,
            help="Set sample rate. Default: value from config file."),
        arg("-g", action="store", type=float, dest="gain", help="Set gain. Default: value from config file.")
    ])
    @arg_exclusive(args=[
        arg("-a", action="store", dest="arfcn", type=int, help="ARFCN of the BTS."),
        arg("-f", action="store", dest="freq", type=float, help="Frequency of the BTS.")
    ])
    @arg("-b", action="store", dest="band", choices=(arfcn_converter.get_bands()), help="GSM band of the ARFCN.")
    @cmd(name="capture_rtlsdr", description="Capture and save GSM transmissions using a RTL-SDR device.")
    def capture_rtlsdr(self, args):
        path = self._config_provider.get("gr-gsm", "apps_path")
        freq = args.freq
        arfcn = args.arfcn
        band = args.band
        ppm = args.ppm
        sample_rate = args.samp_rate
        gain = args.gain
        cfile = None
        burstfile = None
        verbose = args.print_bursts
        gsmtap = args.gsmtap
        length = args.length

        if freq is not None:
            if band:
                if not arfcn_converter.is_valid_downlink(freq, band):
                    self.printmsg("Frequency is not valid in the specified band")
                    return
                else:
                    arfcn = arfcn_converter.downlink2arfcn(freq, band)
            else:
                for band in arfcn_converter.get_bands():
                    if arfcn_converter.is_valid_downlink(freq, band):
                        arfcn = arfcn.downlink2arfcn(freq, band)
                        break
        elif arfcn is not None:
            if band:
                if not arfcn_converter.is_valid_arfcn(arfcn, band):
                    self.printmsg("ARFCN is not valid in the specified band")
                    return
                else:
                    freq = arfcn_converter.arfcn2downlink(arfcn, band)
            else:
                for band in arfcn_converter.get_bands():
                    if arfcn_converter.is_valid_arfcn(arfcn, band):
                        freq = arfcn_converter.arfcn2downlink(arfcn, band)
                        break

        if ppm is None:
            ppm = self._config_provider.getint("rtl_sdr", "ppm")
        if sample_rate is None:
            sample_rate = self._config_provider.getint("rtl_sdr", "sample_rate")
        if gain is None:
            gain = self._config_provider.getint("rtl_sdr", "gain")

        if args.cfile is not None:
            cfile = self._data_access_provider.getfilepath(args.cfile)
        if args.bursts is not None:
            burstfile = self._data_access_provider.getfilepath(args.bursts)

        if cfile is None and burstfile is None:
            self.printmsg("You must provide either a cfile or a burst file as destination.")
            return

        tb = grgsm_capture(fc=freq, gain=gain, samp_rate=sample_rate,
                           ppm=ppm, arfcn=arfcn, cfile=cfile,
                           burst_file=burstfile, band=band, verbose=verbose, gsmtap=gsmtap, rec_length=length)

        def signal_handler(signal, frame):
            tb.stop()
            tb.wait()

        signal.signal(signal.SIGINT, signal_handler)

        tb.start()
        tb.wait()
