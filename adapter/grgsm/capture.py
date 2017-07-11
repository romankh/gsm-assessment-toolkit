# -*- coding: utf-8 -*-
from math import pi

import grgsm
import osmosdr
import pmt
from gnuradio import blocks
from gnuradio import gr


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
