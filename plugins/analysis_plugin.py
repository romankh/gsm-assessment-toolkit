# -*- coding: utf-8 -*-

from adapter.grgsm.info_extractor import InfoExtractor
from core.plugin.interface import plugin, PluginBase, arg, cmd, subcmd

channel_modes = ['BCCH_SDCCH4', 'SDCCH8']


@plugin(name='Analysis Plugin',
        description='Provides analysis of captures. Currently only Immediate Assignments and Cipher Mode Commands.')
class AnalysisPlugin(PluginBase):
    @cmd(name="analyze", description="Provides functionality for analyzing burst files.", parent=True)
    def analyze(self, args):
        pass

    @arg("-m", action="store", dest="mode", choices=channel_modes, help="Channel mode.", default="SDCCH8")
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
    @arg("-m", action="store", dest="mode", choices=channel_modes, help="Channel mode.", default="SDCCH8")
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

        if len(ia_fnrs) > 0:
            self.printmsg("IAs:")
            self.printmsg("FNR  TYPE  TIMESLOT  TIMING ADVANCE  SUBCHANNEL HOPPING")
            for i in range(0, len(ia_fnrs)):
                self.printmsg("%s %s %s %s %s %s" % (ia_fnrs[i],
                                                     ia_channeltypes[i][:4] if ia_channeltypes[i].startswith(
                                                         "GPRS") else
                                                     ia_channeltypes[i],
                                                     ia_timeslots[i],
                                                     ia_tas[i],
                                                     ia_subchannels[i],
                                                     "Y" if ia_hopping[i] == 1 else "N",))
