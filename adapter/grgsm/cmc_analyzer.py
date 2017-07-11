# -*- coding: utf-8 -*-
import grgsm
from gnuradio import gr

from core.adapterinterfaces.a5 import A5BurstSet, A5ReconstructionAdapter


class CMCAnalyzer(gr.top_block):
    def __init__(self, timeslot, burst_file, mode, fnr_start, fnr_end):
        gr.top_block.__init__(self, "Top Block")

        self.burst_file_source = grgsm.burst_file_source(burst_file)
        self.timeslot_filter = grgsm.burst_timeslot_filter(timeslot)
        self.fnr_filter_start = grgsm.burst_fnr_filter(grgsm.FILTER_GREATER_OR_EQUAL, fnr_start)
        self.fnr_filter_end = grgsm.burst_fnr_filter(grgsm.FILTER_LESS_OR_EQUAL, fnr_end)
        if mode == 'BCCH_SDCCH4':
            self.subslot_splitter = grgsm.burst_sdcch_subslot_splitter(grgsm.SPLITTER_SDCCH4)
            self.subslot_analyzers = [CMCAnalyzerArm() for x in range(4)]
            self.demapper = grgsm.gsm_bcch_ccch_sdcch4_demapper(timeslot_nr=timeslot, )
        else:
            self.subslot_splitter = grgsm.burst_sdcch_subslot_splitter(grgsm.SPLITTER_SDCCH8)
            self.subslot_analyzers = [CMCAnalyzerArm() for x in range(8)]
            self.demapper = grgsm.gsm_sdcch8_demapper(timeslot_nr=timeslot, )

        self.control_channels_decoder = grgsm.control_channels_decoder()
        self.burst_sink = grgsm.burst_sink()

        self.msg_connect((self.burst_file_source, 'out'), (self.timeslot_filter, 'in'))
        self.msg_connect((self.timeslot_filter, 'out'), (self.fnr_filter_start, 'in'))
        self.msg_connect((self.fnr_filter_start, 'out'), (self.fnr_filter_end, 'in'))
        self.msg_connect((self.fnr_filter_end, 'out'), (self.demapper, 'bursts'))
        self.msg_connect((self.demapper, 'bursts'), (self.burst_sink, 'in'))
        self.msg_connect((self.demapper, 'bursts'), (self.subslot_splitter, 'in'))
        for i in range(4 if mode == 'BCCH_SDCCH4' else 8):
            self.msg_connect((self.subslot_splitter, 'out' + str(i)), (self.subslot_analyzers[i], 'in'))

        self.bursts = None
        self.cmcs = None

    def wait(self):
        """
        Override gr.top_block's wait method.
        """
        gr.top_block.wait(self)
        self.__create_data_dict()
        self.__create_cmc_dict()
        self.__create_sacch_dict()

    def is_a51_cmc(self, framenumber_cmc):
        if framenumber_cmc in self.cmcs and self.cmcs[framenumber_cmc][1] == 1:
            return True
        return False

    def createLapdmUiBurstSets(self, framenumber_cmc):
        """
        Creates a list of A5 burst sets with Lapdm UI plaintext messages

        :param framenumber_cmc: the framenumber of the cipher mode command
        :return: a list of A5 burst sets
        """
        burst_sets = []

        for i in range(1, 6):  # starting from the first message after cmc, we try 5 messages
            fnr_of_msg = framenumber_cmc + i * 51
            for j in range(0, 4):  # a message has 4 bursts
                fnr = fnr_of_msg + j
                check_burst_index = 0 if j > 0 else 1

                burst_sets.append(
                    A5BurstSet(
                        fnr,  # framenumber of the burst we want to use
                        self.bursts[fnr],  # data (payload) of the burst we want to use
                        A5ReconstructionAdapter.lapdm_ui[j],  # plaintext data (payload) of a lapdm ui message
                        fnr_of_msg + check_burst_index,  # framenumber of verification burst.
                        # we use the first burst of the message as check burst, if j > 0
                        self.bursts[fnr_of_msg + check_burst_index],  # data (payload) of the verification burst
                        A5ReconstructionAdapter.lapdm_ui[check_burst_index]  # plaintextdata (payload) of
                        # the verification burst
                    )
                )
        return burst_sets

    def get_subchannel(self, framenumber_cmc):
        """
        Get the subchannel of the CMC specified by its frame number.
        :param framenumber_cmc: the framenumber of the cmc.
        :return: the numeric value of the subchannel. Can be None if an invalid frame number was provided.
        """
        if framenumber_cmc in self.cmcs:
            return self.cmcs[framenumber_cmc][0]
        return None

    def __create_data_dict(self):
        self.bursts = dict()
        fnrs = self.burst_sink.get_framenumbers()
        data = self.burst_sink.get_burst_data()
        for i in range(len(fnrs)):
            self.bursts[fnrs[i]] = data[i][3:60] + data[i][88:145]  # take burst payload only

    def __create_cmc_dict(self):
        self.cmcs = dict()
        for subchannel in range(len(self.subslot_analyzers)):
            analyzer = self.subslot_analyzers[subchannel]
            cmc_a5_versions = analyzer.extract_cmc.get_a5_versions()
            cmc_fnrs = analyzer.extract_cmc.get_framenumbers()
            for i in range(len(cmc_fnrs)):
                self.cmcs[cmc_fnrs[i]] = (subchannel, cmc_a5_versions[i])  # tuple: subchannel and A5 version

    def __create_sacch_dict(self):
        self.sacch_sits = dict()
        for subchannel in range(len(self.subslot_analyzers)):
            analyzer = self.subslot_analyzers[subchannel]
            sit_fnrs = analyzer.collect_system_info.get_framenumbers()
            sit_types = analyzer.collect_system_info.get_system_information_type()
            sit_data = analyzer.collect_system_info.get_data()
            for i in range(len(sit_fnrs)):
                if sit_types[i].startswith("System Information Type 5") or sit_types[i].startswith(
                        "System Information Type 6"):
                    self.sacch_sits[sit_fnrs[i]] = (subchannel, sit_types[i], sit_data[i])


class CMCAnalyzerArm(gr.hier_block2):
    def __init__(self):
        gr.hier_block2.__init__(
            self, "Cmc Analyzer Block",
            gr.io_signature(0, 0, 0),
            gr.io_signature(0, 0, 0),
        )
        self.message_port_register_hier_in("in")

        self.decoder = grgsm.control_channels_decoder()
        self.extract_system_info = grgsm.extract_system_info()
        self.extract_cmc = grgsm.extract_cmc()
        self.collect_system_info = grgsm.collect_system_info()

        self.msg_connect((self.decoder, 'msgs'), (self.extract_cmc, 'msgs'))
        self.msg_connect((self.decoder, 'msgs'), (self.extract_system_info, 'msgs'))
        self.msg_connect((self.decoder, 'msgs'), (self.collect_system_info, 'msgs'))
        self.msg_connect((self, 'in'), (self.decoder, 'bursts'))


class ImmediateAssignmentExtractor(gr.top_block):
    def __init__(self, burst_file, timeslot, mode, framenumber):
        gr.top_block.__init__(self, "Top Block")

        self.burst_file_source = grgsm.burst_file_source(burst_file)
        self.timeslot_filter = grgsm.burst_timeslot_filter(timeslot)
        self.fnr_filter_start = grgsm.burst_fnr_filter(grgsm.FILTER_GREATER_OR_EQUAL, framenumber)
        if mode == 'BCCH_SDCCH4':
            self.demapper = grgsm.gsm_bcch_ccch_sdcch4_demapper(timeslot_nr=timeslot, )
        else:
            self.demapper = grgsm.gsm_sdcch8_demapper(timeslot_nr=timeslot, )

        self.decoder = grgsm.control_channels_decoder()

        self.extract_immediate_assignment = grgsm.extract_immediate_assignment()

        self.msg_connect((self.burst_file_source, 'out'), (self.timeslot_filter, 'in'))
        self.msg_connect((self.timeslot_filter, 'out'), (self.fnr_filter_start, 'in'))
        self.msg_connect((self.fnr_filter_start, 'out'), (self.demapper, 'bursts'))
        self.msg_connect((self.demapper, 'bursts'), (self.decoder, 'bursts'))
        self.msg_connect((self.decoder, 'msgs'), (self.extract_immediate_assignment, 'msgs'))


class CMCFinder(gr.top_block):
    def __init__(self, burst_file, timeslot, subchannel, mode, fnr_start):
        gr.top_block.__init__(self, "Top Block")

        self.burst_file_source = grgsm.burst_file_source(burst_file)
        self.timeslot_filter = grgsm.burst_timeslot_filter(timeslot)
        self.fnr_filter_start = grgsm.burst_fnr_filter(grgsm.FILTER_GREATER_OR_EQUAL, fnr_start)
        # we only listen for a timespan of 12 SDCCH messages for the CMC
        self.fnr_filter_end = grgsm.burst_fnr_filter(grgsm.FILTER_LESS_OR_EQUAL, fnr_start + 51 * 10000)

        if mode == "BCCH_SDCCH4":
            self.subchannel_filter = grgsm.burst_sdcch_subslot_filter(grgsm.SS_FILTER_SDCCH4, subchannel)
            self.demapper = grgsm.gsm_bcch_ccch_sdcch4_demapper(timeslot_nr=timeslot, )
        else:
            self.subchannel_filter = grgsm.burst_sdcch_subslot_filter(grgsm.SS_FILTER_SDCCH8, subchannel)
            self.demapper = grgsm.gsm_sdcch8_demapper(timeslot_nr=timeslot, )

        self.demapper = grgsm.gsm_sdcch8_demapper(timeslot_nr=timeslot, )
        self.decoder = grgsm.control_channels_decoder()
        self.extract_cmc = grgsm.extract_cmc()

        self.msg_connect((self.burst_file_source, 'out'), (self.timeslot_filter, 'in'))
        self.msg_connect((self.timeslot_filter, 'out'), (self.subchannel_filter, 'in'))
        self.msg_connect((self.subchannel_filter, 'out'), (self.fnr_filter_start, 'in'))
        self.msg_connect((self.fnr_filter_start, 'out'), (self.fnr_filter_end, 'in'))
        self.msg_connect((self.fnr_filter_end, 'out'), (self.demapper, 'bursts'))
        self.msg_connect((self.demapper, 'bursts'), (self.decoder, 'bursts'))
        self.msg_connect((self.decoder, 'msgs'), (self.extract_cmc, 'msgs'))

    def get_cmc(self):
        fnrs = self.extract_cmc.get_framenumbers()
        if len(fnrs) > 0:
            return self.extract_cmc.get_framenumbers()[0]
        return None


class SICollector(gr.top_block):
    def __init__(self, timeslot, burst_file, mode):
        gr.top_block.__init__(self, "Top Block")

        self.si_messages = dict()

        self.burst_file_source = grgsm.burst_file_source(burst_file)
        self.timeslot_filter = grgsm.burst_timeslot_filter(timeslot)
        if mode == 'BCCH_SDCCH4':
            self.demapper = grgsm.gsm_bcch_ccch_sdcch4_demapper(timeslot_nr=timeslot, )
        else:
            self.demapper = grgsm.gsm_sdcch8_demapper(timeslot_nr=timeslot, )

        self.decoder = grgsm.control_channels_decoder()
        self.control_channels_decoder = grgsm.control_channels_decoder()
        self.collect_system_info = grgsm.collect_system_info()

        self.msg_connect((self.burst_file_source, 'out'), (self.timeslot_filter, 'in'))
        self.msg_connect((self.timeslot_filter, 'out'), (self.demapper, 'bursts'))
        self.msg_connect((self.demapper, 'bursts'), (self.decoder, 'bursts'))
        self.msg_connect((self.decoder, 'msgs'), (self.collect_system_info, 'msgs'))

    def wait(self):
        """
        Override gr.top_block's wait method.
        """
        gr.top_block.wait(self)
        self.__analyze_sacch_messages()

    def __analyze_sacch_messages(self):
        si_types = self.collect_system_info.get_system_information_type()
        si_data = self.collect_system_info.get_data()

        def __is_sacch(si_type):
            if si_type.startswith("System Information Type 5") or si_type.startswith("System Information Type 6"):
                return True
            return False

        for i in range(len(self.collect_system_info.get_framenumbers())):
            if __is_sacch(si_types[i]) and not self.si_messages.has_key(si_types[i]):
                self.si_messages[si_types[i]] = si_data[i]

            if len(self.si_messages) >= 4:  # there can only be 4 different SI message types on SACCH
                break
