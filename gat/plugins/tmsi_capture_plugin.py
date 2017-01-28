# -*- coding: utf-8 -*-
import os

import grgsm
from gnuradio import blocks
from gnuradio import gr

from gat.core.plugin.interface import plugin, PluginBase, cmd, arg_group, arg, arg_exclusive, PluginError


@plugin(name='TMSI Plugin', description='Provides TMSI capturing')
class TmsiPlugin(PluginBase):
    channel_modes = ['BCCH', 'BCCH_SDCCH4']

    @arg("-v", action="store_true", dest="verbose", help="If set, the captured TMSI / IMSI are printed.")
    @arg("-o", action="store", dest="dest_file",
         help="If set, the captured TMSI / IMSI are stored in the specified file.")
    @arg("-m", action="store", dest="mode", choices=channel_modes, help="Channel mode.", default="BCCH")
    @arg_group(name="Cfile Options", args=[
        arg("-a", action="store", dest="arfcn", type=int, help="ARFCN of the cfile capture."),
        arg("-f", action="store", dest="freq", type=float, help="Frequency of the cfile capture."),
        arg("-b", action="store", dest="band", choices=grgsm.arfcn.get_bands(), help="GSM of the cfile capture."),
        arg("-p", action="store", dest="ppm", type=int, help="Set ppm. Default: value from config file."),
        arg("-s", action="store", dest="samp_rate", type=float,
            help="Set sample rate. Default: value from config file."),
        arg("-g", action="store", type=float, dest="gain", help="Set gain. Default: value from config file.")
    ])
    @arg("-t", action="store", dest="timeslot", type=int, help="Timeslot of the CCCH.", default=0)
    @arg_exclusive(args=[
        arg("--cfile", action="store_path", dest="cfile", help="cfile."),
        arg("--bursts", action="store_path", dest="bursts", help="bursts.")
    ])
    @cmd(name="tmsi_capture", description="TMSI capturing.")
    def tmsi_capture(self, args):
        verbose = args.verbose
        destfile = None
        mode = args.mode
        freq = args.freq
        arfcn = args.arfcn
        band = args.band
        ppm = args.ppm
        sample_rate = args.samp_rate
        gain = args.gain
        timeslot = args.timeslot
        cfile = None
        burstfile = None

        if args.cfile is None and args.bursts is None:
            raise PluginError("Provide a cfile or burst file.")

        if args.dest_file is not None:
            destfile = self._data_access_provider.getfilepath(args.dest_file)
        if args.cfile is not None:
            cfile = self._data_access_provider.getfilepath(args.cfile)
        if args.bursts is not None:
            burstfile = self._data_access_provider.getfilepath(args.bursts)

        flowgraph = TmsiCapture(timeslot=timeslot, chan_mode=mode,
                                burst_file=burstfile,
                                cfile=cfile, fc=freq, samp_rate=sample_rate, ppm=ppm)
        flowgraph.start()
        flowgraph.wait()

        tmsis = dict()
        imsis = dict()

        with open("tmsicount.txt") as file:
            content = file.readlines()

            for line in content:
                segments = line.strip().split("-")
                if segments[0] != "0":
                    key = segments[0]
                    if tmsis.has_key(key):
                        tmsis[key] += 1
                    else:
                        tmsis[key] = 1
                else:
                    key = segments[2]
                    if imsis.has_key(key):
                        imsis[key] += 1
                    else:
                        imsis[key] = 1

        self.printmsg("Captured {} TMSI, {} IMSI\n".format(len(tmsis), len(imsis)))

        if verbose or destfile is not None:
            sorted_tmsis = sorted(tmsis, key=tmsis.__getitem__, reverse=True)
            sorted_imsis = sorted(imsis, key=imsis.__getitem__, reverse=True)

            if destfile is not None:
                with open(destfile, "w") as file:
                    for key in sorted_tmsis:
                        file.write("{}:{}\n".format(key, tmsis[key]))
                    for key in sorted_imsis:
                        file.write("{}:{}\n".format(key, imsis[key]))

            if verbose:
                for key in sorted_tmsis:
                    self.printmsg("{} ({} times)".format(key, tmsis[key]))
                for key in sorted_imsis:
                    self.printmsg("{} ({} times)".format(key, imsis[key]))

        os.remove("tmsicount.txt")


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
