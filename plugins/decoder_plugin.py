# -*- coding: utf-8 -*-
import collections
import imp
import os

import grgsm

from core.plugin.interface import plugin, PluginBase, cmd, arg, arg_exclusive, arg_group


@plugin(name='Decoder Plugin', description='Decodes Control and Traffic channels.')
class DecoderPlugin(PluginBase):
    channel_modes = ['BCCH', 'BCCH_SDCCH4', 'SDCCH8', 'TCHF']
    tch_codecs = collections.OrderedDict([
        ('FR', grgsm.TCH_FS),
        ('EFR', grgsm.TCH_EFR),
        ('AMR12.2', grgsm.TCH_AFS12_2),
        ('AMR10.2', grgsm.TCH_AFS10_2),
        ('AMR7.95', grgsm.TCH_AFS7_95),
        ('AMR7.4', grgsm.TCH_AFS7_4),
        ('AMR6.7', grgsm.TCH_AFS6_7),
        ('AMR5.9', grgsm.TCH_AFS5_9),
        ('AMR5.15', grgsm.TCH_AFS5_15),
        ('AMR4.75', grgsm.TCH_AFS4_75)
    ])

    @arg("-m", action="store", dest="mode", choices=channel_modes, help="Channel mode.", default="BCCH")
    @arg("-t", action="store", dest="timeslot", type=int, help="Timeslot to decode.", default=0)
    @arg("--subslot", action="store", dest="subslot", type=int,
         help="Subslot to decode. Use in combination with channel type BCCH_SDCCH4 and SDCCH8.")
    @arg_exclusive(args=[
        arg("--cfile", action="store_path", dest="cfile", help="cfile."),
        arg("--bursts", action="store_path", dest="bursts", help="bursts.")
    ])
    @arg("--print-messages", action="store_true", dest="print_messages", help="Print decoded messages.",
         default=False)
    @arg("--print-bursts", action="store_true", dest="print_bursts", help="Print decoded messages.",
         default=False)
    @arg_group(name="Cfile Options", args=[
        arg("-a", action="store", dest="arfcn", type=int, help="ARFCN of the cfile capture."),
        arg("-f", action="store", dest="freq", type=float, help="Frequency of the cfile capture."),
        arg("-b", action="store", dest="band", choices=grgsm.arfcn.get_bands(), help="GSM of the cfile capture."),
        arg("-p", action="store", dest="ppm", type=int, help="Set ppm. Default: value from config file."),
        arg("-s", action="store", dest="samp_rate", type=float,
            help="Set sample rate. Default: value from config file."),
        arg("-g", action="store", type=float, dest="gain", help="Set gain. Default: value from config file.")
    ])
    @arg_group(name="Decryption Options", args=[
        arg("-5", "--a5", action="store", dest="a5", type=int, help="A5 version.", default=1),
        arg("-k", "--kc", action="store", dest="kc", help="A5 session key Kc. Valid formats are "
                                                                      "'0x12,0x34,0x56,0x78,0x90,0xAB,0xCD,0xEF' "
                                                                      "and '1234567890ABCDEF'"),
    ])
    @arg_group(name="TCH Options", args=[
        arg("-c", action="store", dest="speech_codec", choices=tch_codecs.keys(), help="TCH-F speech codec."),
        arg("-o", action="store", dest="speech_output_file", help="TCH/F speech output file"),
        arg("--voice-boundary-detect", action="store_true", dest="enable_voice_boundary_detection",
            help="Enable voice boundary detection for traffic channels. This can help reduce noice in the output.",
            default=False),
    ])
    @cmd(name="decode", description="Decodes GSM messages.")
    def decode(self, args):
        path = self._config_provider.get("gr-gsm", "apps_path")
        decoder = imp.load_source("", os.path.join(path, "grgsm_decode"))

        timeslot = args.timeslot
        subslot = args.subslot
        mode = args.mode

        burstfile = None
        cfile = None

        freq = args.freq
        arfcn = args.arfcn
        band = args.band
        ppm = args.ppm
        sample_rate = args.samp_rate
        gain = args.gain

        verbose = args.print_messages
        kc = []

        def kc_parse(kc, value):

            """ Callback function that parses Kc """

            # format 0x12,0x34,0x56,0x78,0x90,0xAB,0xCD,0xEF
            if ',' in value:
                value_str = value.split(',')

                for s in value_str:
                    val = int(s, 16)
                    if val < 0 or val > 255:
                        pass  # error
                    kc.append(val)
                if len(kc) != 8:
                    kc = []  # error
            elif len(value) == 16:
                for i in range(8):
                    s = value[2 * i: 2 * i + 2]
                    val = int(s, 16)
                    if val < 0 or val > 255:
                        pass  # error
                        # parser.error("Invalid Kc % s\n" % s)
                    kc.append(val)
            else:
                pass  # error

        if args.kc is not None:
            kc_parse(kc, args.kc)


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

        tb = decoder.grgsm_decoder(timeslot=timeslot, subslot=subslot, chan_mode=mode,
                                   burst_file=burstfile,
                                   cfile=cfile, fc=freq, samp_rate=sample_rate,
                                   a5=args.a5, a5_kc=kc,
                                   speech_file=args.speech_output_file,
                                   speech_codec=self.tch_codecs.get(args.speech_codec),
                                   enable_voice_boundary_detection=False,
                                   verbose=verbose,
                                   print_bursts=args.print_bursts, ppm=ppm)
        tb.start()
        tb.wait()
