# -*- coding: utf-8 -*-
import imp
import os
import signal
from math import pi

import grgsm
import osmosdr
import pmt
from gnuradio import blocks
from gnuradio import gr

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
    @arg("-b", action="store", dest="band", choices=(grgsm.arfcn.get_bands()), help="GSM band of the ARFCN.")
    @cmd(name="capture_rtlsdr", description="Capture and save GSM transmissions using a RTL-SDR device.")
    def capture_rtlsdr(self, args):
        path = self._config_provider.get("gr-gsm", "apps_path")
        capture = imp.load_source("", os.path.join(path, "grgsm_capture.py"))

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
                if not grgsm.arfcn.is_valid_downlink(freq, band):
                    self.printmsg("Frequency is not valid in the specified band")
                    return
                else:
                    arfcn = grgsm.arfcn.downlink2arfcn(freq, band)
            else:
                for band in grgsm.arfcn.get_bands():
                    if grgsm.arfcn.is_valid_downlink(freq, band):
                        arfcn = grgsm.arfcn.downlink2arfcn(freq, band)
                        break
        elif arfcn is not None:
            if band:
                if not grgsm.arfcn.is_valid_arfcn(arfcn, band):
                    self.printmsg("ARFCN is not valid in the specified band")
                    return
                else:
                    freq = grgsm.arfcn.arfcn2downlink(arfcn, band)
            else:
                for band in grgsm.arfcn.get_bands():
                    if grgsm.arfcn.is_valid_arfcn(arfcn, band):
                        freq = grgsm.arfcn.arfcn2downlink(arfcn, band)
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


class grgsm_capture(gr.top_block):
    def __init__(self, fc, gain, samp_rate, ppm, arfcn, cfile=None, burst_file=None, band=None, verbose=False,
                 gsmtap=False, rec_length=None, args=""):

        gr.top_block.__init__(self, "Gr-gsm Capture")

        ##################################################
        # Parameters
        ##################################################
        self.fc = fc
        self.gain = gain
        self.samp_rate = samp_rate
        self.ppm = ppm
        self.arfcn = arfcn
        self.cfile = cfile
        self.burst_file = burst_file
        self.band = band
        self.verbose = verbose
        self.gsmtap = gsmtap
        self.shiftoff = shiftoff = 400e3
        self.rec_length = rec_length

        ##################################################
        # Processing Blocks
        ##################################################

        self.rtlsdr_source = osmosdr.source(args="numchan=" + str(1) + " " + args)
        self.rtlsdr_source.set_sample_rate(samp_rate)
        self.rtlsdr_source.set_center_freq(fc - shiftoff, 0)
        self.rtlsdr_source.set_freq_corr(ppm, 0)
        self.rtlsdr_source.set_dc_offset_mode(2, 0)
        self.rtlsdr_source.set_iq_balance_mode(2, 0)
        self.rtlsdr_source.set_gain_mode(True, 0)
        self.rtlsdr_source.set_gain(gain, 0)
        self.rtlsdr_source.set_if_gain(20, 0)
        self.rtlsdr_source.set_bb_gain(20, 0)
        self.rtlsdr_source.set_antenna("", 0)
        self.rtlsdr_source.set_bandwidth(250e3 + abs(shiftoff), 0)
        self.blocks_rotator = blocks.rotator_cc(-2 * pi * shiftoff / samp_rate)

        if self.rec_length is not None:
            self.blocks_head_0 = blocks.head(gr.sizeof_gr_complex, int(samp_rate * rec_length))

        if self.verbose or self.burst_file:
            self.gsm_receiver = grgsm.receiver(4, ([self.arfcn]), ([]))
            self.gsm_input = grgsm.gsm_input(
                ppm=0,
                osr=4,
                fc=fc,
                samp_rate_in=samp_rate,
            )
            self.gsm_clock_offset_control = grgsm.clock_offset_control(fc - shiftoff, samp_rate, osr=4)

        if self.burst_file:
            self.gsm_burst_file_sink = grgsm.burst_file_sink(self.burst_file)

        if self.cfile:
            self.blocks_file_sink = blocks.file_sink(gr.sizeof_gr_complex * 1, self.cfile, False)
            self.blocks_file_sink.set_unbuffered(False)

        if self.verbose:
            self.gsm_bursts_printer_0 = grgsm.bursts_printer(pmt.intern(""),
                                                             False, False, False, False)
        if self.gsmtap:
            self.bcch_demapper = grgsm.gsm_bcch_ccch_demapper(0)
            self.cch_decoder = grgsm.control_channels_decoder()
            self.socket_pdu_server = blocks.socket_pdu("UDP_SERVER", "127.0.0.1", "4729", 10000)
            self.socket_pdu = blocks.socket_pdu("UDP_CLIENT", "127.0.0.1", "4729", 10000)

        ##################################################
        # Connections
        ##################################################

        if self.rec_length is not None:  # if recording length is defined connect head block after the source
            self.connect((self.rtlsdr_source, 0), (self.blocks_head_0, 0))
            self.connect((self.blocks_head_0, 0), (self.blocks_rotator, 0))
        else:
            self.connect((self.rtlsdr_source, 0), (self.blocks_rotator, 0))

        if self.cfile:
            self.connect((self.blocks_rotator, 0), (self.blocks_file_sink, 0))

        if self.verbose or self.burst_file:
            self.connect((self.gsm_input, 0), (self.gsm_receiver, 0))
            self.connect((self.blocks_rotator, 0), (self.gsm_input, 0))
            self.msg_connect(self.gsm_clock_offset_control, "ctrl", self.gsm_input, "ctrl_in")
            self.msg_connect(self.gsm_receiver, "measurements", self.gsm_clock_offset_control, "measurements")

            if self.burst_file:
                self.msg_connect(self.gsm_receiver, "C0", self.gsm_burst_file_sink, "in")
            if self.verbose:
                self.msg_connect(self.gsm_receiver, "C0", self.gsm_bursts_printer_0, "bursts")
            if self.gsmtap:
                self.msg_connect(self.gsm_receiver, "C0", self.bcch_demapper, "bursts")
                self.msg_connect(self.bcch_demapper, "bursts", self.cch_decoder, "bursts")
                self.msg_connect(self.cch_decoder, "msgs", self.socket_pdu, "pdus")
