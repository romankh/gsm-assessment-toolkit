# -*- coding: utf-8 -*-
import Queue
import os
import time
from math import pi

import grgsm
import osmosdr
from gnuradio import blocks
from gnuradio import gr

from gat.adapter.gat_app_sms_adapter import GatAppSmsAdapter
from gat.core.adapterinterfaces.types import SmsType
from gat.core.plugin.interface import plugin, PluginBase, cmd, arg_group, arg, arg_exclusive
from gat.core.plugin.silencer import Silencer


@plugin(name='TMSI Identification Plugin', description='Provides TMSI-MSISDN correlation')
class TmsiIdentificationPlugin(PluginBase):
    channel_modes = ['BCCH', 'BCCH_SDCCH4']

    # anzahl der iterationen
    @arg("-n", action="store", dest="max_sms", type=int, help="Max number of type 0 SMS messages to send.", default=6)
    @arg('-w', '--wait-for-response', action="store", dest="wait", type=int, default=15,
         help="Wait n seconds for a response to a SMS ping.")
    @arg("-m", action="store", dest="mode", choices=channel_modes, help="Channel mode.", default="BCCH")
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
    @arg("-t", action="store", dest="timeslot", type=int, help="Timeslot of the CCCH.", default=0)
    @arg('msisdn', action="store", help="MSISDN to correlate (i.e. +43123456789).")
    @cmd(name="tmsi_correlation", description="TMSI capturing.")
    def tmsi_correlation(self, args):

        # tmsi_correlation -n 1 -b P-GSM -a 13 067762475917
        # verbose = args.verbose
        mode = args.mode
        freq = args.freq
        arfcn = args.arfcn
        band = args.band
        ppm = args.ppm
        sample_rate = args.samp_rate
        gain = args.gain
        timeslot = args.timeslot
        max_iterations = args.max_sms
        msisdn = args.msisdn
        wait = args.wait

        if ppm is None:
            ppm = self._config_provider.getint("rtl_sdr", "ppm")
        if sample_rate is None:
            sample_rate = self._config_provider.getint("rtl_sdr", "sample_rate")
        if gain is None:
            gain = self._config_provider.getint("rtl_sdr", "gain")

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

        # todo: stop if max_iterations < 6

        response_queue = Queue.Queue()

        def callback(msg):
            response_queue.put(msg)

        adapter = GatAppSmsAdapter(self._config_provider, wait)
        adapter.register_read_callback(callback)

        candidates = set()
        i = 0

        try:
            while i < max_iterations:
                flowgraph = TmsiLiveCapture(timeslot=timeslot, chan_mode=mode, fc=freq, arfcn=arfcn,
                                            samp_rate=sample_rate,
                                            ppm=ppm, gain=gain)
                with Silencer():
                    flowgraph.start()
                    response_received = False
                    adapter.send(sms_type=SmsType.MWID_Report, msisdn=msisdn, text=None)

                    start = time.time()
                    now = start

                    while (now - start) < 15:
                        if not response_queue.empty():
                            response = response_queue.get()
                            # self.printmsg("response: " + response)
                            if "Connection refused" in response.strip('\n'):
                                self.printmsg("Failed to connect to GAT app")
                                break

                            response_msg = response.strip('\n').split("#")

                            response_type = response_msg[0]
                            response_msisdn = response_msg[1]

                            if response_type == "sms-status":
                                response_status = response_msg[2]
                                if response_status != "OK":
                                    self.printmsg("Sending to %s failed" % response_msisdn)
                                else:
                                    pass
                                    # self.printmsg("SMS message to %s was sent." % response_msisdn)
                            elif response_type == "sms-rcv":
                                # recipient got our message
                                response_received = True
                                break

                        time.sleep(0.2)  # ToDo: No busy waiting !
                        now = time.time()

                    if not response_received:
                        self.printmsg("Timeout: no response to the ping")
                        # return

                    flowgraph.wait()
                    flowgraph.stop()
                    flowgraph = None

                iteration_candidates = self.read_tmsi_file()
                if i == 0:
                    candidates = candidates.union(iteration_candidates)
                else:
                    candidates = candidates.intersection(iteration_candidates)

                print "candidates: " + str(len(candidates))

                if len(candidates) == 0:
                    if i > 0:
                        self.printmsg("No intersection found.")
                        break
                    else:
                        self.printmsg("No TMSIs captured.")
                        break
                elif len(candidates) == 1:
                    result = candidates.pop()
                    self.printmsg("Found TMSI: {}".format(result))
                    break

                i += 1

        except Exception, e:
            print e
        finally:
            adapter.unregister_read_callback()

    def read_tmsi_file(self):
        tmsi_set = set()
        with open("tmsicount.txt", mode="r+") as file:
            content = file.readlines()
            for line in content:
                # print line
                segments = line.strip().split("-")
                if segments[0] != "0":
                    key = segments[0]
                else:
                    key = segments[2]

                tmsi_set.add(key)
        os.remove("tmsicount.txt")
        return tmsi_set


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
