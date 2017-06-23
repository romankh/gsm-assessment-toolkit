# -*- coding: utf-8 -*-
import grgsm
from gnuradio import gr

from gat.core.plugin.interface import plugin, PluginBase, cmd, arg, subcmd


@plugin(name="Burstfile Plugin", description="Provides functionality for filtering burst files")
class BurstfilePlugin(PluginBase):
    @cmd(name="bursts", description="Provides functionality for filtering burst files.", parent=True)
    def bursts(self, args):
        pass

    @arg("-a", action="store", dest="after", type=int,
         help="Allow only framenumbers greater than or equal the specified one")
    @arg("-b", action="store", dest="before", type=int,
         help="Allow only framenumbers less than or equal the specified one")
    @arg("-t", action="store", dest="timeslot", type=int, help="Allow only bursts on the specified timeslot")
    @arg("-s", action="store", dest="subslot", type=int, help="Allow only bursts on the specified subslot")
    @arg("-d", action="store", dest="remove_dummy", type=bool, default=False, help="Remove dummy bursts")
    @arg("input_burst_file", action="store_path", help="The source burst file")
    @arg("output_burst_file", action="store_path", help="The destination burst file")
    @subcmd(name="filter", help="Prints frequency information for an ARFCN.", parent="bursts")
    def filter(self, args):
        block = BurstFilter(args.input_burst_file, args.output_burst_file, args.after, args.before, args.timeslot,
                            args.subslot, args.remove_dummy)
        block.start()
        block.wait()


class BurstFilter(gr.top_block):
    def __init__(self, source, destination, framenr_ge=None, framenr_le=None, timeslot=None, subslot=None,
                 filter_dummy_bursts=False):
        gr.top_block.__init__(self, "Top Block")

        self.burst_file_source = grgsm.burst_file_source(source)
        self.burst_file_sink = grgsm.burst_file_sink(destination)

        lastblock = self.burst_file_source

        if framenr_ge is not None:
            self.burst_fnr_filterge = grgsm.burst_fnr_filter(grgsm.FILTER_GREATER_OR_EQUAL, framenr_ge)
            self.msg_connect((lastblock, 'out'), (self.burst_fnr_filterge, 'in'))
            lastblock = self.burst_fnr_filterge

        if framenr_le is not None:
            self.burst_fnr_filterle = grgsm.burst_fnr_filter(grgsm.FILTER_LESS_OR_EQUAL, framenr_le)
            self.msg_connect((lastblock, 'out'), (self.burst_fnr_filterle, 'in'))
            lastblock = self.burst_fnr_filterle

        if timeslot is not None:
            self.burst_timeslot_filter = grgsm.burst_timeslot_filter(timeslot)
            self.msg_connect((lastblock, 'out'), (self.burst_timeslot_filter, 'in'))
            lastblock = self.burst_timeslot_filter

        if subslot is not None:
            self.burst_sdcch_subslot_filter = grgsm.burst_sdcch_subslot_filter(grgsm.SS_FILTER_SDCCH8, subslot)
            self.msg_connect((lastblock, 'out'), (self.burst_sdcch_subslot_filter, 'in'))
            lastblock = self.burst_sdcch_subslot_filter

        if filter_dummy_bursts:
            self.dummy_burst_filter = grgsm.dummy_burst_filter()
            self.msg_connect((lastblock, 'out'), (self.dummy_burst_filter, 'in'))
            lastblock = self.dummy_burst_filter

        self.msg_connect((lastblock, 'out'), (self.burst_file_sink, 'in'))
