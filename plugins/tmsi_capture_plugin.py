# -*- coding: utf-8 -*-
import os

import grgsm

from adapter.grgsm.tmsi import TmsiCapture
from core.plugin.interface import plugin, PluginBase, cmd, arg_group, arg, arg_exclusive, PluginError


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
