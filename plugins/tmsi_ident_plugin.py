# -*- coding: utf-8 -*-
import Queue
import os
import time

import grgsm

from adapter.gat_app_sms_adapter import GatAppSmsAdapter
from core.adapterinterfaces.types import SmsType
from core.plugin.interface import plugin, PluginBase, cmd, arg_group, arg, arg_exclusive
from core.plugin.silencer import Silencer


@plugin(name='TMSI Identification Plugin', description='Provides TMSI-MSISDN correlation')
class TmsiIdentificationPlugin(PluginBase):
    channel_modes = ['BCCH', 'BCCH_SDCCH4']

    # anzahl der iterationen
    @arg("-n", action="store", dest="max_sms", type=int, help="Max number of type 0 SMS messages to send.", default=6)
    @arg('-w', '--wait-for-response', action="store", dest="wait", type=int, default=15,
         help="Wait n seconds for a response to a SMS ping.")
    @arg("-m", action="store", dest="mode", choices=channel_modes, help="Channel mode.", default="BCCH")
    @arg_group(name="RTL-SDR configuration", args=[
        arg("-p", action="store", dest="ppm", type=int, help="Set ppm. Default: value from config file."),
        arg("-s", action="store", dest="samp_rate", type=float,
            help="Set sample rate. Default: value from config file."),
        arg("-g", action="store", type=float, dest="gain", help="Set gain. Default: value from config file.")
    ])
    @arg_exclusive(args=[
        arg("-a", action="store", dest="arfcn", type=int, help="ARFCN of the BTS."),
        arg("-f", action="store", dest="freq", type=float, help="Frequency of the BTS.")
    ])
    @arg("-b", action="store", dest="band", choices=(grgsm.arfcn.get_bands()), help="GSM band of the ARFCN.")
    @arg("-t", action="store", dest="timeslot", type=int, help="Timeslot of the CCCH.", default=0)
    @arg('msisdn', action="store", help="MSISDN to correlate (i.e. +43123456789).")
    @cmd(name="tmsi_correlation", description="Perform TMSI-MSISDN correlation.")
    def tmsi_correlation(self, args):
        mode = args.mode
        freq = args.freq
        arfcn = args.arfcn
        band = args.band
        ppm = args.ppm
        sample_rate = args.samp_rate
        gain = args.gain
        timeslot = args.timeslot
        max_iterations = args.max_sms
        msisdn = args.msisdn
        wait = args.wait

        if ppm is None:
            ppm = self._config_provider.getint("rtl_sdr", "ppm")
        if sample_rate is None:
            sample_rate = self._config_provider.getint("rtl_sdr", "sample_rate")
        if gain is None:
            gain = self._config_provider.getint("rtl_sdr", "gain")

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

        # todo: stop if max_iterations < 6

        response_queue = Queue.Queue()

        def callback(msg):
            response_queue.put(msg)

        adapter = GatAppSmsAdapter(self._config_provider, wait)
        adapter.register_read_callback(callback)

        candidates = set()
        i = 0

        try:
            while i < max_iterations:
                flowgraph = TmsiLiveCapture(timeslot=timeslot, chan_mode=mode, fc=freq, arfcn=arfcn,
                                            samp_rate=sample_rate,
                                            ppm=ppm, gain=gain)
                with Silencer():
                    flowgraph.start()
                    response_received = False
                    adapter.send(sms_type=SmsType.MWID_Report, msisdn=msisdn, text=None)

                    start = time.time()
                    now = start

                    while (now - start) < 15:
                        if not response_queue.empty():
                            response = response_queue.get()
                            # self.printmsg("response: " + response)
                            if "Connection refused" in response.strip('\n'):
                                self.printmsg("Failed to connect to GAT app")
                                break

                            response_msg = self.parse_response(response)

                            response_type = response_msg[0]
                            response_msisdn = response_msg[1]
                            response_status = response_msg[2]

                            if response_type == "sms-status":
                                if response_status != "OK":
                                    self.printmsg("Sending to %s failed" % response_msisdn)
                                else:
                                    pass
                                    # self.printmsg("SMS message to %s was sent." % response_msisdn)
                            elif response_type == "sms-rcv":
                                # recipient got our message
                                response_received = True
                                break

                            if response_type == "sms-send" and response_status != "OK":
                                self.printmsg("Sending to %s failed" % response_msisdn)
                            elif response_type == "sms-delivery":
                                if response_status != "OK":
                                    self.printmsg("Delivery to %s failed." % response_msisdn)
                                else:
                                    self.printmsg("Response from %s received." % response_msisdn)

                        time.sleep(0.2)  # ToDo: No busy waiting !
                        now = time.time()

                    if not response_received:
                        self.printmsg("Timeout: no response to the ping")
                        # return

                    flowgraph.wait()
                    flowgraph.stop()
                    flowgraph = None

                iteration_candidates = self.read_tmsi_file()
                if i == 0:
                    candidates = candidates.union(iteration_candidates)
                else:
                    candidates = candidates.intersection(iteration_candidates)

                print "candidates: " + str(len(candidates))

                if len(candidates) == 0:
                    if i > 0:
                        self.printmsg("No intersection found.")
                        break
                    else:
                        self.printmsg("No TMSIs captured.")
                        break
                elif len(candidates) == 1:
                    result = candidates.pop()
                    self.printmsg("Found TMSI: {}".format(result))
                    break

                i += 1

        except Exception, e:
            print e
        finally:
            adapter.unregister_read_callback()

    def read_tmsi_file(self):
        tmsi_set = set()
        with open("tmsicount.txt", mode="r+") as file:
            content = file.readlines()
            for line in content:
                # print line
                segments = line.strip().split("-")
                if segments[0] != "0":
                    key = segments[0]
                else:
                    key = segments[2]

                tmsi_set.add(key)
        os.remove("tmsicount.txt")
        return tmsi_set

    def parse_response(self, response):
        response_msg = response.strip('\n').split("#")
        response_type = response_msg[0]
        response_msisdn = response_msg[1]
        response_status = response_msg[2]
        return (response_type, response_msisdn, response_status)
