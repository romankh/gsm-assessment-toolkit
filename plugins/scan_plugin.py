# -*- coding: utf-8 -*-
import imp
import numpy
import os
import subprocess

import grgsm

from core.plugin.interface import PluginBase, plugin, cmd, arg, arg_group, PluginError
from core.plugin.silencer import Silencer


@plugin(name='Scan Plugin', description='Scan Plugin provides methods for scanning a GSM band for active BTS')
class ScanPlugin(PluginBase):
    @arg("--speed", action="store", dest="speed", type=int, help="Scan speed. Value range 0-5.", default=4)
    @arg_group(name="RTL-SDR configuration", args=[
        arg("-p", action="store", dest="ppm", type=int, help="Set ppm. Default: value from config file."),
        arg("-s", action="store", dest="samp_rate", type=float,
            help="Set sample rate. Default: value from config file."),
        arg("-g", action="store", type=float, dest="gain", help="Set gain. Default: value from config file.")
    ])
    @arg("-b", action="store", dest="band", choices=(grgsm.arfcn.get_bands()), help="GSM band of the ARFCN.")
    @cmd(name="scan_rtlsdr", description="Scan a GSM band using a RTL-SDR device.")
    def scan_rtlsdr(self, args):

        if args.speed < 0 or args.speed > 5:
            raise PluginError("Invalid speed")

        path = self._config_provider.get("gr-gsm", "apps_path")
        grgsm_scanner = imp.load_source("", os.path.join(path, "grgsm_scanner"))

        band = args.band
        sample_rate = args.samp_rate
        ppm = args.ppm
        gain = args.gain
        speed = args.speed

        if ppm is None:
            ppm = self._config_provider.getint("rtl_sdr", "ppm")
        if sample_rate is None:
            sample_rate = self._config_provider.getint("rtl_sdr", "sample_rate")
        if gain is None:
            gain = self._config_provider.getint("rtl_sdr", "gain")

        if band == 'DCS1800' or band == 'PCS1900':
            shmmni = self.get_shmmni()
            if shmmni < 32000:
                msg = "Unsufficient shared memory segments.\n"
                msg += "For scanning DCS1800 or PCS1900 you need to increase the value, i.e. using the following command:\n\n"
                msg += "sudo sysctl kernel.shmmni=32000"
                self.printmsg(msg)
                return

        channels_num = int(sample_rate / 0.2e6)

        for arfcn_range in grgsm.arfcn.get_arfcn_ranges(args.band):
            first_arfcn = arfcn_range[0]
            last_arfcn = arfcn_range[1]
            last_center_arfcn = last_arfcn - int((channels_num / 2) - 1)

            current_freq = grgsm.arfcn.arfcn2downlink(first_arfcn + int(channels_num / 2) - 1, band)
            last_freq = grgsm.arfcn.arfcn2downlink(last_center_arfcn, band)
            stop_freq = last_freq + 0.2e6 * channels_num

            while current_freq < stop_freq:
                # silence rtl_sdr output:
                with Silencer():
                    # instantiate scanner and processor
                    scanner = grgsm_scanner.wideband_scanner(rec_len=6 - speed,
                                                             sample_rate=sample_rate,
                                                             carrier_frequency=current_freq,
                                                             ppm=ppm, args="")
                    # start recording
                    scanner.start()
                    scanner.wait()
                    scanner.stop()

                    freq_offsets = numpy.fft.ifftshift(
                        numpy.array(
                            range(int(-numpy.floor(channels_num / 2)), int(numpy.floor((channels_num + 1) / 2)))) * 2e5)
                    detected_c0_channels = scanner.gsm_extract_system_info.get_chans()

                    found_list = []

                    if detected_c0_channels:
                        chans = numpy.array(scanner.gsm_extract_system_info.get_chans())
                        found_freqs = current_freq + freq_offsets[(chans)]

                        cell_ids = numpy.array(scanner.gsm_extract_system_info.get_cell_id())
                        lacs = numpy.array(scanner.gsm_extract_system_info.get_lac())
                        mccs = numpy.array(scanner.gsm_extract_system_info.get_mcc())
                        mncs = numpy.array(scanner.gsm_extract_system_info.get_mnc())
                        ccch_confs = numpy.array(scanner.gsm_extract_system_info.get_ccch_conf())
                        powers = numpy.array(scanner.gsm_extract_system_info.get_pwrs())

                        for i in range(0, len(chans)):
                            cell_arfcn_list = scanner.gsm_extract_system_info.get_cell_arfcns(chans[i])
                            neighbour_list = scanner.gsm_extract_system_info.get_neighbours(chans[i])

                            info = grgsm_scanner.channel_info(grgsm.arfcn.downlink2arfcn(found_freqs[i], band),
                                                              found_freqs[i],
                                                              cell_ids[i], lacs[i], mccs[i], mncs[i], ccch_confs[i],
                                                              powers[i],
                                                              neighbour_list, cell_arfcn_list)
                            found_list.append(info)

                    scanner = None

                for info in sorted(found_list):
                    self.printmsg(info.__repr__())

                current_freq += channels_num * 0.2e6

    def get_shmmni(self):
        result = subprocess.check_output(["sysctl kernel.shmmni"], shell=True, stderr=subprocess.STDOUT)
        if result.startswith("kernel.shmmni"):
            return int(result.strip("kernel.shmmni = "))
        else:
            return None
