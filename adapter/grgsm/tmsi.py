# -*- coding: utf-8 -*-
import grgsm
from gnuradio import blocks
from gnuradio import gr


class TmsiCapture(gr.top_block):
    def __init__(self, timeslot=0, chan_mode='BCCH',
                 burst_file=None,
                 cfile=None, fc=None, samp_rate=2e6, ppm=0):

        gr.top_block.__init__(self, "gr-gsm TMSI Capture")

        ##################################################
        # Parameters
        ##################################################
        self.timeslot = timeslot
        self.chan_mode = chan_mode
        self.burst_file = burst_file
        self.cfile = cfile
        self.fc = fc
        self.samp_rate = samp_rate
        self.ppm = ppm

        ##################################################
        # Blocks
        ##################################################

        if self.burst_file:
            self.burst_file_source = grgsm.burst_file_source(burst_file)
        elif self.cfile:
            self.file_source = blocks.file_source(gr.sizeof_gr_complex * 1, self.cfile, False)
            self.receiver = grgsm.receiver(4, ([0]), ([]))
            if self.fc is not None:
                self.input_adapter = grgsm.gsm_input(ppm=ppm, osr=4, fc=self.fc, samp_rate_in=samp_rate)
                self.offset_control = grgsm.clock_offset_control(self.fc, self.samp_rate)
            else:
                self.input_adapter = grgsm.gsm_input(ppm=ppm, osr=4, samp_rate_in=samp_rate)

        self.dummy_burst_filter = grgsm.dummy_burst_filter()
        self.timeslot_filter = grgsm.burst_timeslot_filter(self.timeslot)

        if self.chan_mode == 'BCCH':
            self.bcch_demapper = grgsm.gsm_bcch_ccch_demapper(self.timeslot)
        elif self.chan_mode == 'BCCH_SDCCH4':
            self.bcch_sdcch4_demapper = grgsm.gsm_bcch_ccch_sdcch4_demapper(self.timeslot)

        self.cch_decoder = grgsm.control_channels_decoder()
        self.tmsi_dumper = grgsm.tmsi_dumper()
        self.socket_pdu_server = blocks.socket_pdu("UDP_SERVER", "127.0.0.1", "4729", 10000)
        self.socket_pdu = blocks.socket_pdu("UDP_CLIENT", "127.0.0.1", "4729", 10000)

        ##################################################
        # Asynch Message Connections
        ##################################################

        if self.burst_file:
            self.msg_connect(self.burst_file_source, "out", self.dummy_burst_filter, "in")
        elif self.cfile:
            self.connect((self.file_source, 0), (self.input_adapter, 0))
            self.connect((self.input_adapter, 0), (self.receiver, 0))
            if self.fc is not None:
                self.msg_connect(self.offset_control, "ctrl", self.input_adapter, "ctrl_in")
                self.msg_connect(self.receiver, "measurements", self.offset_control, "measurements")
            self.msg_connect(self.receiver, "C0", self.dummy_burst_filter, "in")

        self.msg_connect(self.dummy_burst_filter, "out", self.timeslot_filter, "in")

        if self.chan_mode == 'BCCH':
            self.msg_connect(self.timeslot_filter, "out", self.bcch_demapper, "bursts")
            self.msg_connect(self.bcch_demapper, "bursts", self.cch_decoder, "bursts")
            self.msg_connect(self.cch_decoder, "msgs", self.socket_pdu, "pdus")
            self.msg_connect(self.cch_decoder, "msgs", self.tmsi_dumper, "msgs")

        elif self.chan_mode == 'BCCH_SDCCH4':
            self.msg_connect(self.timeslot_filter, "out", self.bcch_sdcch4_demapper, "bursts")
            self.msg_connect(self.bcch_sdcch4_demapper, "bursts", self.cch_decoder, "bursts")
            self.msg_connect(self.cch_decoder, "msgs", self.socket_pdu, "pdus")
            self.msg_connect(self.cch_decoder, "msgs", self.tmsi_dumper, "msgs")


class TmsiLiveCapture(gr.top_block):
    def __init__(self, timeslot=0, chan_mode='BCCH', fc=None, arfcn=0, samp_rate=2e6, ppm=0, gain=30):
        gr.top_block.__init__(self, "gr-gsm TMSI Capture")
        self.rec_length = 15

        ##################################################
        # Parameters
        ##################################################
        self.timeslot = timeslot
        self.chan_mode = chan_mode
        self.fc = fc
        self.arfcn = arfcn
        self.samp_rate = samp_rate
        self.ppm = ppm
        self.gain = gain
        self.shiftoff = shiftoff = 400e3
        self.args = ""

        ##################################################
        # Blocks
        ##################################################

        self.rtlsdr_source = osmosdr.source(args="numchan=" + str(1) + " " + self.args)
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

        self.blocks_head = blocks.head(gr.sizeof_gr_complex, int(samp_rate * self.rec_length))

        self.gsm_receiver = grgsm.receiver(4, ([self.arfcn]), ([]))
        self.gsm_input = grgsm.gsm_input(
            ppm=0,
            osr=4,
            fc=fc,
            samp_rate_in=samp_rate,
        )
        self.gsm_clock_offset_control = grgsm.clock_offset_control(fc - shiftoff, samp_rate, osr=4)
        self.dummy_burst_filter = grgsm.dummy_burst_filter()
        self.timeslot_filter = grgsm.burst_timeslot_filter(self.timeslot)

        if self.chan_mode == 'BCCH':
            self.bcch_demapper = grgsm.gsm_bcch_ccch_demapper(self.timeslot)
        elif self.chan_mode == 'BCCH_SDCCH4':
            self.bcch_sdcch4_demapper = grgsm.gsm_bcch_ccch_sdcch4_demapper(self.timeslot)

        self.cch_decoder = grgsm.control_channels_decoder()
        self.tmsi_dumper = grgsm.tmsi_dumper()
        self.socket_pdu_server = blocks.socket_pdu("UDP_SERVER", "127.0.0.1", "4729", 10000)
        self.socket_pdu = blocks.socket_pdu("UDP_CLIENT", "127.0.0.1", "4729", 10000)

        ##################################################
        # Asynch Message Connections
        ##################################################

        self.connect((self.rtlsdr_source, 0), (self.blocks_head, 0))
        self.connect((self.blocks_head, 0), (self.blocks_rotator, 0))
        self.connect((self.gsm_input, 0), (self.gsm_receiver, 0))
        self.connect((self.blocks_rotator, 0), (self.gsm_input, 0))
        self.msg_connect(self.gsm_clock_offset_control, "ctrl", self.gsm_input, "ctrl_in")
        self.msg_connect(self.gsm_receiver, "measurements", self.gsm_clock_offset_control, "measurements")

        self.msg_connect(self.gsm_receiver, "C0", self.dummy_burst_filter, "in")
        self.msg_connect(self.dummy_burst_filter, "out", self.timeslot_filter, "in")

        if self.chan_mode == 'BCCH':
            self.msg_connect(self.timeslot_filter, "out", self.bcch_demapper, "bursts")
            self.msg_connect(self.bcch_demapper, "bursts", self.cch_decoder, "bursts")
            self.msg_connect(self.cch_decoder, "msgs", self.socket_pdu, "pdus")
            self.msg_connect(self.cch_decoder, "msgs", self.tmsi_dumper, "msgs")

        elif self.chan_mode == 'BCCH_SDCCH4':
            self.msg_connect(self.timeslot_filter, "out", self.bcch_sdcch4_demapper, "bursts")
            self.msg_connect(self.bcch_sdcch4_demapper, "bursts", self.cch_decoder, "bursts")
            self.msg_connect(self.cch_decoder, "msgs", self.socket_pdu, "pdus")
            self.msg_connect(self.cch_decoder, "msgs", self.tmsi_dumper, "msgs")
