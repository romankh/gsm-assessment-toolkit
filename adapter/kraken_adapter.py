# -*- coding: utf-8 -*-
import socket
import subprocess

from core.adapterinterfaces.a5 import A5ReconstructionAdapter


class KrakenA51ReconstructorAdapter(A5ReconstructionAdapter):
    def __init__(self, config_provider):
        super(KrakenA51ReconstructorAdapter, self).__init__(config_provider)

    def reconstruct(self, a5_burst_set):
        super(KrakenA51ReconstructorAdapter, self).reconstruct(a5_burst_set)

    def send2kraken(self, kraken_burst, verbose=False):
        host = "localhost"
        port = 9999
        cracked = False
        invalid = False
        failed = False
        found_key = None

        # Todo: Timeout for connection
        remote_address = (host, port)
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as e:
            print("Socket error")
            return None

        try:
            sock.connect(remote_address)
        except socket.error as e:
            sock.close()
            sock = None
            print("Connection error")
            return None

        burst_xored = KrakenA51ReconstructorAdapter.xor(kraken_burst.burst_data_cipher, kraken_burst.burst_data_plain)
        sock.send("crack " + burst_xored + "\n")

        while True:
            msg = sock.recv(1024)
            if not msg:
                break
            else:
                lines = msg.splitlines()
                for line in lines:
                    if "crack #" in line:
                        # not found:
                        failed = True
                    elif "Cracking #" in line:
                        pass
                    elif "Found " in line:
                        msg_parts = line.split(" ")
                        found_key = msg_parts[1]
                        bitpos = msg_parts[3]
                        table = msg_parts[7].replace("(table:", "").replace(")", "")

                        if verbose:
                            print "Candidate %s in table %s" % (found_key, table)

                        fn_count = KrakenA51ReconstructorAdapter.fn2count(kraken_burst.frame_number)
                        check_fn_count = KrakenA51ReconstructorAdapter.fn2count(kraken_burst.check_frame_number)
                        check_burst_xored = KrakenA51ReconstructorAdapter.xor(kraken_burst.check_burst_data_cipher,
                                                                              kraken_burst.check_burst_data_plain)

                        found_key = KrakenA51ReconstructorAdapter.verify_key(found_key, bitpos, fn_count,
                                                                             check_fn_count,
                                                                             check_burst_xored, verbose)
                        if found_key is not None:
                            cracked = True

                    if cracked or failed:
                        break

                if cracked or failed:
                    break

        if sock is not None:
            sock.close()
        if cracked:
            return found_key
        return None

    @staticmethod
    def verify_key(found_key, bitpos, framecount, check_framecount, check_burst, verbose=False):
        # todo: error handling if find_kc not found
        cmd = "find_kc %s %s %s %s %s " % (found_key, bitpos, framecount, check_framecount, check_burst)
        output = subprocess.check_output([cmd], shell=True, stderr=subprocess.STDOUT)
        # print(output)
        key = None
        if verbose:
            mismatch_count = output.count("mismatch")
            match_count = output.count("*** MATCHED ***")
            print "Backclocking results in %s possible keys, %s match" % (mismatch_count + match_count, match_count)

        if "*** MATCHED ***" in output:
            output_lines = output.split('\n')
            for line in output_lines:
                if "*** MATCHED ***" in line:
                    parts = line.split(' ')
                    key = parts[1] + parts[2] + parts[3] + parts[4] + parts[5] + parts[6] + parts[7] + parts[8]
            return key
        return None

    @staticmethod
    def xor(burst_unencrypted, burst_encrypted):
        r = ""
        for i in range(114):
            a = ord(burst_unencrypted[i])
            b = ord(burst_encrypted[i])
            r += chr(48 ^ a ^ b)
        return r

    @staticmethod
    def fn2count(fn):
        t1 = int(fn / 1326)
        t2 = fn % 26
        t3 = fn % 51
        return (t1 << 11) | (t3 << 5) | t2
