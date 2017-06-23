# -*- coding: utf-8 -*-
import subprocess

from core.plugin.interface import plugin, PluginBase, cmd


@plugin(name="Wireshark", description="Wireshark related commands.")
class WiresharkPlugin(PluginBase):
    @cmd(name="wireshark", description="Launch wireshark and start sniffing.")
    def wireshark(self, args):
        subprocess.Popen(["wireshark", "-i", "lo", "-f", "udp port 4729 && !icmp", "-k"])
