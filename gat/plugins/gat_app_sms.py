# -*- coding: utf-8 -*-
import Queue
import time

from gat.adapter.gat_app_sms_adapter import GatAppSmsAdapter
from gat.core.adapterinterfaces.types import SmsType
from gat.core.plugin.interface import plugin, arg, PluginBase, cmd


@plugin(name='GAT-App SMS', description='SMS sending.')
class GatAppSmsPlugin(PluginBase):
    @arg('recipient', action="store", type=str, help="Phone number of recipient.")
    @arg('-t', action="store", dest="smstype", choices=(SmsType.get_names()), help="Type of message to send.")
    @arg('-c', action="store", dest="text", type=str, help="Text to send.")
    @arg('-w', '--wait-for-response', action="store", dest="wait", type=int, default=5,
         help="Wait n seconds for a response.")
    @cmd(name='sendsms', description='Send different types of SMS using GAT-App.')
    def send(self, args):
        response_queue = Queue.Queue()

        def callback(msg):
            response_queue.put(msg)

        adapter = GatAppSmsAdapter(self._config_provider, args.wait)
        adapter.register_read_callback(callback)

        smstext = ''
        if args.text:
            smstext = args.text

        smstype = SmsType[args.smstype]

        try:
            adapter.send(sms_type=smstype, msisdn=args.recipient, text=smstext)

            if args.wait > 0:
                start = time.time()
                now = start
                msg_counter = 0

                while (now - start) < args.wait:
                    while not response_queue.empty():
                        response = response_queue.get()
                        response_msg = response.strip('\n').split("#")

                        response_type = response_msg[0]
                        response_msisdn = response_msg[1]

                        if response_type == "sms-status":
                            response_status = response_msg[2]
                            if response_status != "OK":
                                self.printmsg("Sending to %s failed" % response_msisdn)
                            else:
                                self.printmsg("SMS message to %s was sent." % response_msisdn)
                        elif response_type == "sms-rcv":
                            self.printmsg("Response from %s received." % response_msisdn)
                        else:
                            self.printmsg("Got unexpected response: %s" % response)

                        msg_counter += 1

                    if smstype == SmsType.SMS_Report or smstype == SmsType.CLASS0_Report or smstype == SmsType.TYPE0_Report or smstype == SmsType.MWID_Report:
                        if msg_counter == 2:
                            break
                    else:
                        if msg_counter == 1:
                            break

                    time.sleep(0.2)  # ToDo: No busy waiting !
                    now = time.time()

                if msg_counter == 0:
                    self.printmsg("No response from GAT-App")
        except:
            pass
        finally:
            adapter.unregister_read_callback()
