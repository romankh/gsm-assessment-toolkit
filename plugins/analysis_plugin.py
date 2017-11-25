# -*- coding: utf-8 -*-
import os

from adapter.grgsm.info_extractor import InfoExtractor
from adapter.grgsm.systeminfo_extractor import SystemInfoExtractor
from adapter.grgsm.tmsi import TmsiCapture
from core.plugin.interface import plugin, PluginBase, arg, cmd, subcmd, PluginError
from core.util.text_utils import columnize

channel_modes_cch = ['BCCH_SDCCH4', 'SDCCH8']
channel_modes = ['BCCH'] + channel_modes_cch


@plugin(name='Analysis Plugin',
        description='Provides analysis of captures. Currently only Immediate Assignments and Cipher Mode Commands.')
class AnalysisPlugin(PluginBase):
    @cmd(name="analyze", description="Provides functionality for analyzing burst files.", parent=True)
    def analyze(self, args):
        pass

    @arg("-m", action="store", dest="mode", choices=channel_modes_cch, help="Channel mode.", default="SDCCH8")
    @arg("-t", action="store", dest="timeslot", type=int, help="Timeslot of the CCCH.", default=0)
    @arg("--bursts", action="store_path", dest="bursts", help="bursts.")
    @subcmd(name='cipher', help='Analyze Cipher Mode Command messages in a capture.', parent="analyze")
    def cipher_mode_commands(self, args):
        extractor = InfoExtractor(args.timeslot, args.bursts, args.mode, False)
        extractor.start()
        extractor.wait()

        cmc_fnrs = extractor.gsm_extract_cmc.get_framenumbers()
        cmc_a5vs = extractor.gsm_extract_cmc.get_a5_versions()

        if len(cmc_fnrs) > 0:
            self.printmsg("CMCs:")
            for i in range(0, len(cmc_fnrs)):
                self.printmsg("Framenumber: %s   A5/%s" % (cmc_fnrs[i], cmc_a5vs[i]))

    @arg("--gprs-assignments", action="store_true", dest="gprs", help="Show GPRS related immediate assignments.")
    @arg("-m", action="store", dest="mode", choices=channel_modes_cch, help="Channel mode.", default="BCCH_SDCCH4")
    @arg("-t", action="store", dest="timeslot", type=int, help="Timeslot of the CCCH.", default=0)
    @arg("--bursts", action="store_path", dest="bursts", help="bursts.")
    @subcmd(name="immediate", help="Analyze Immediate Assignment messages in the capture file.", parent="analyze")
    def immediate_assignments(self, args):
        extractor = InfoExtractor(args.timeslot, args.bursts, args.mode, args.gprs)
        extractor.start()
        extractor.wait()

        ia_fnrs = extractor.gsm_extract_immediate_assignment.get_frame_numbers()
        ia_channeltypes = extractor.gsm_extract_immediate_assignment.get_channel_types()
        ia_timeslots = extractor.gsm_extract_immediate_assignment.get_timeslots()
        ia_subchannels = extractor.gsm_extract_immediate_assignment.get_subchannels()
        ia_hopping = extractor.gsm_extract_immediate_assignment.get_hopping()
        ia_maios = extractor.gsm_extract_immediate_assignment.get_maios()
        ia_hsns = extractor.gsm_extract_immediate_assignment.get_hsns()
        ia_arfcns = extractor.gsm_extract_immediate_assignment.get_arfcns()
        ia_tas = extractor.gsm_extract_immediate_assignment.get_timing_advances()
        ia_mobileallocations = extractor.gsm_extract_immediate_assignment.get_mobile_allocations()

        if len(ia_fnrs) == 0:
            self.printmsg("No Immediate Assignment messages found.")
        else:
            strings = ["FNR", "TYPE", "TIMESLOT", "TIMING ADVANCE", "SUBCHANNEL", "HOPPING"]

            self.printmsg("FNR  TYPE  TIMESLOT  TIMING ADVANCE  SUBCHANNEL HOPPING")
            for i in range(0, len(ia_fnrs)):
                strings.append(str(ia_fnrs[i]))
                strings.append(
                    str(ia_channeltypes[i][:4]) if ia_channeltypes[i].startswith("GPRS") else str(ia_channeltypes[i]))
                strings.append(str(ia_timeslots[i]))
                strings.append(str(ia_tas[i]))
                strings.append(str(ia_subchannels[i]))
                strings.append("Y" if ia_hopping[i] == 1 else "N")

            self.printmsg(columnize(strings, 6))

    @arg("-v", action="store_true", dest="verbose", help="If set, the captured TMSI / IMSI are printed.")
    @arg("-o", action="store", dest="dest_file",
         help="If set, the captured TMSI / IMSI are stored in the specified file.")
    @arg("-m", action="store", dest="mode", choices=channel_modes_cch, help="Channel mode.", default="BCCH")
    @arg("-t", action="store", dest="timeslot", type=int, help="Timeslot of the CCCH.", default=0)
    @arg("--bursts", action="store_path", dest="bursts", help="bursts.")
    @subcmd(name="tmsi", help="Output TMSIs in a capture.", parent="analyze")
    def tmsi(self, args):
        verbose = args.verbose
        destfile = None
        mode = args.mode
        timeslot = args.timeslot
        burstfile = None

        if args.bursts is None:
            raise PluginError("Provide a burst file.")

        if args.dest_file is not None:
            destfile = self._data_access_provider.getfilepath(args.dest_file)
        if args.bursts is not None:
            burstfile = self._data_access_provider.getfilepath(args.bursts)

        flowgraph = TmsiCapture(timeslot=timeslot, chan_mode=mode,
                                burst_file=burstfile,
                                cfile=None, fc=None, samp_rate=None, ppm=None)
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

    @arg("-m", action="store", dest="mode", choices=channel_modes, help="Channel mode.", default="SDCCH8")
    @arg("-t", action="store", dest="timeslot", type=int, help="Timeslot of the CCCH.", default=0)
    @arg("--bursts", action="store_path", dest="bursts", help="bursts.")
    @subcmd(name="system_info", help="Print system information in the capture file.", parent="analyze")
    def system_information(self, args):
        extractor = SystemInfoExtractor(args.timeslot, args.bursts, 'BCCH', False)
        extractor.start()
        extractor.wait()

        chans = extractor.gsm_extract_system_info.get_chans()  # arfcn
        pwrs = extractor.gsm_extract_system_info.get_pwrs()
        cell_id = extractor.gsm_extract_system_info.get_cell_id()
        lac = extractor.gsm_extract_system_info.get_lac()
        mcc = extractor.gsm_extract_system_info.get_mcc()
        mnc = extractor.gsm_extract_system_info.get_mnc()
        ccch_conf = extractor.gsm_extract_system_info.get_ccch_conf()  # 0 = ccch, not combined with SDCCHs

        class CellInfo:
            def __init__(self, arfcn, pwr, ci, lac, mcc, mnc, ccch_conf, cell_arfcns, neighbour_arfcns):
                self.arfcn = arfcn
                self.pwr = str(pwr) + " dbm"
                self.cell_identity = ci
                self.location_are_code = lac
                self.mcc = mcc
                self.mnc = mnc
                self.ccch_conf = ccch_conf
                self.cell_arfcns = cell_arfcns
                self.neighbour_arfcns = neighbour_arfcns

        found_cellinfos = dict()

        for i in range(0, len(chans)):
            current_arfcn = chans[i]
            if current_arfcn not in found_cellinfos:
                channel_config = 'BCCH' if ccch_conf[i] == 0 else 'BCCH_SDCCH' if ccch_conf[i] == 1 else ''
                cell_arfcns = extractor.gsm_extract_system_info.get_cell_arfcns(current_arfcn)
                neighbour_arfcns = extractor.gsm_extract_system_info.get_neighbours(current_arfcn)

                current_cell_info = CellInfo(current_arfcn, pwrs[i], cell_id[i], lac[i],
                                             mcc[i], mnc[i], channel_config,
                                             cell_arfcns, neighbour_arfcns
                                             )
                found_cellinfos[current_arfcn] = current_cell_info

        if len(found_cellinfos) < 1:
            self.printmsg("No system information found.")
        else:
            strings = ["ARFCN", "PWR", "CI", "LAC", "MCC", "MNC", "CONFIG", "CELL ARFCNs", "NEIGHBOUR ARFCNs"]
            for arfcn in found_cellinfos:
                cell_info = found_cellinfos[arfcn]
                strings.append(str(cell_info.arfcn))
                strings.append(str(cell_info.pwr))
                strings.append(str(cell_info.cell_identity))
                strings.append(str(cell_info.location_are_code))
                strings.append(str(cell_info.mcc))
                strings.append(str(cell_info.mnc))
                strings.append(str(cell_info.ccch_conf))
                strings.append(", ".join(str(entry) for entry in cell_info.cell_arfcns))
                strings.append(", ".join(str(entry) for entry in cell_info.neighbour_arfcns))

            self.printmsg(columnize(strings, 9))
