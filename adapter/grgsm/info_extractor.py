# -*- coding: utf-8 -*-
import grgsm
from gnuradio import gr


class InfoExtractor(gr.top_block):
    def __init__(self, timeslot, burst_file, mode, show_gprs):
        gr.top_block.__init__(self, "Top Block")

        self.gsm_burst_file_source = grgsm.burst_file_source(burst_file)
        self.gsm_burst_timeslot_filter = grgsm.burst_timeslot_filter(timeslot)

        if mode == 'BCCH_SDCCH4':
            self.demapper = grgsm.gsm_bcch_ccch_sdcch4_demapper(timeslot_nr=timeslot, )
        else:
            self.demapper = grgsm.gsm_sdcch8_demapper(timeslot_nr=timeslot, )

        self.gsm_control_channels_decoder = grgsm.control_channels_decoder()
        self.gsm_extract_cmc = grgsm.extract_cmc()
        # self.gsm_extract_immediate_assignment = grgsm.extract_immediate_assignment(False, True, True)
        self.gsm_extract_immediate_assignment = grgsm.extract_immediate_assignment(False, not show_gprs, True)

        self.msg_connect((self.gsm_burst_file_source, 'out'), (self.gsm_burst_timeslot_filter, 'in'))
        self.msg_connect((self.gsm_burst_timeslot_filter, 'out'), (self.demapper, 'bursts'))
        self.msg_connect((self.demapper, 'bursts'), (self.gsm_control_channels_decoder, 'bursts'))
        self.msg_connect((self.gsm_control_channels_decoder, 'msgs'), (self.gsm_extract_cmc, 'msgs'))
        self.msg_connect((self.gsm_control_channels_decoder, 'msgs'), (self.gsm_extract_immediate_assignment, 'msgs'))
