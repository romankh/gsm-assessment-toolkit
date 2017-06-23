# -*- coding: utf-8 -*-
from abc import abstractmethod


class A5ReconstructionAdapter(object):
    lapdm_ui = [
        "100000010001110101010000000010100000000111111101010000001010000100010111010100000000101000010000010101010100000010",
        "101010111111111101000000101010101111111111110100000000100010111111111111010101000000001010101011011101010000001000",
        "000000011111010101010000100000010001010111010101000010100001010001111101010001000010000000000101110101010100000010",
        "000100001010101010111101110101010000000010101110111111010100010000001010101011011101010001000010001011101111010101"
    ]
    xor_match_unencrypted = "0" * 114

    @abstractmethod
    def __init__(self, config_provider):
        pass

    @abstractmethod
    def reconstruct(self, a5_burst_set):
        pass


class A5BurstSet(object):
    def __init__(self, frame_number, burst_data_cipher, burst_data_plain, check_frame_number, check_burst_data_cipher,
                 check_burst_data_plain):
        """

        :param burst: resulting burst of xor'ing plaintext and ciphertext burst
        :param frame_number:
        :param check_burst: resulting burst of xor'ing plaintext and ciphertext burst
        :param check_frame_number:
        """
        self.frame_number = frame_number
        self.burst_data_cipher = burst_data_cipher
        self.burst_data_plain = burst_data_plain
        self.check_frame_number = check_frame_number
        self.check_burst_data_cipher = check_burst_data_cipher
        self.check_burst_data_plain = check_burst_data_plain
