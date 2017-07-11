# -*- coding: utf-8 -*-
from adapter.grgsm.bursts import BurstFilter
from core.plugin.interface import plugin, PluginBase, cmd, arg, subcmd


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
