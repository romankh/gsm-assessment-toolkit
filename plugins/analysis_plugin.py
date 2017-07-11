# -*- coding: utf-8 -*-

from adapter.grgsm.info_extractor import InfoExtractor
from core.plugin.interface import plugin, PluginBase, arg, cmd

channel_modes = ['BCCH_SDCCH4', 'SDCCH8']


@plugin(name='Analysis Plugin',
        description='Provides analysis of captures. Currently only Immediate Assignments and Cipher Mode Commands.')
class AnalysisPlugin(PluginBase):
    @arg("--gprs-assignments", action="store_true", dest="gprs", help="Show GPRS related immediate assignments.")
    @arg("-m", action="store", dest="mode", choices=channel_modes, help="Channel mode.", default="SDCCH8")
    @arg("-t", action="store", dest="timeslot", type=int, help="Timeslot of the CCCH.", default=0)
    @arg("--bursts", action="store_path", dest="bursts", help="bursts.")
    @cmd(name='analyze', description='Analyze Immediate Assignments and Cipher Mode Commands in a capture.')
    def analyze(self, args):
        extractor = InfoExtractor(args.timeslot, args.bursts, args.mode, args.gprs)
        extractor.start()
        extractor.wait()

        cmc_fnrs = extractor.gsm_extract_cmc.get_framenumbers()
        cmc_a5vs = extractor.gsm_extract_cmc.get_a5_versions()

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

        if len(cmc_fnrs) > 0:
            self.printmsg("CMCs:")
            for i in range(0, len(cmc_fnrs)):
                self.printmsg("Framenumber: %s   A5/%s" % (cmc_fnrs[i], cmc_a5vs[i]))

        if len(ia_fnrs) > 0:
            self.printmsg("IAs:")
            self.printmsg("FNR  TYPE  TIMESLOT  SUBCHANNEL HOPPING")
            for i in range(0, len(ia_fnrs)):
                self.printmsg("%s %s %s %s %s" % (ia_fnrs[i],
                                                  ia_channeltypes[i][:4] if ia_channeltypes[i].startswith("GPRS") else
                                                  ia_channeltypes[i],
                                                  ia_timeslots[i],
                                                  ia_subchannels[i],
                                                  "Y" if ia_hopping[i] == 1 else "N",))