import csv

from core.common.mccmnc_parser import MccMncParser
from core.plugin.interface import PluginBase, plugin, cmd, subcmd, arg


@plugin(name='MCC/MNC info', description='Provides details for MCC / MNC.')
class MccPlugin(PluginBase):
    @cmd(name="mccmnc", description="Print MCC and MNC details.", parent=True)
    def mccmnc(self, args):
        pass

    @subcmd(name="update", help="Update the MCC / MNC database from wikipedia", parent="mccmnc")
    def update(self, args):
        parser = MccMncParser()
        destination = self._config_provider.getfile("gat", "mcc-mnc-file", True)
        result = parser.parse(destination)
        self.printmsg(result)

    @arg('mcc', action="store", type=int, help="Mobile Country Code")
    @arg('mnc', action="store", type=int, nargs="?",
         help="Mobile Network Code. Optional. If none provided, only the MCC info will be printed")
    @subcmd(name="show", help="Prints the details for a MCC or MNC", parent="mccmnc")
    def show(self, args):
        database_path = self._config_provider.getfile("gat", "mcc-mnc-file", False)
        try:
            database_file = open(database_path, "r")
        except (OSError, IOError) as e:
            self.printmsg("Database not found. You may have to create the database using 'mccmnc update'")
            return

        mcc = str(args.mcc)
        read_mnc = args.mnc is not None
        if read_mnc:
            mnc = str(args.mnc).zfill(2)
        else:
            mnc = None

        country_name = None
        country_code = None
        network_brand = None
        network_operator = None
        network_status = ""
        network_bands = ""
        network_notes = ""

        try:
            reader = csv.reader(database_file, delimiter=";")

            for row in reader:
                if row[0] == mcc:
                    country_name = row[2]
                    country_code = row[3]
                    if not read_mnc:
                        break
                    elif row[1] == mnc:
                        network_brand = row[4]
                        network_operator = row[5]
                        network_status = row[6]
                        network_bands = row[7]
                        network_notes = row[8]

            if country_name is None:
                self.printmsg("No data found for MCC %s" % mcc)
                return
            else:
                self.printmsg("MCC %s: %s (%s)" % (mcc, country_name, country_code))

            if read_mnc:
                if network_operator is None:
                    self.printmsg("No data found for MNC %s" % mnc)
                    return
                else:
                    if network_brand is not None and network_brand is not "":
                        self.printmsg("MNC %s: Operator: %s" % (mnc, network_operator))
                    else:
                        self.printmsg("MNC %s: Operator: %s (Brand: %s)" % (mnc, network_operator, network_brand))

                    self.printmsg("Status: %s" % network_status)
                    self.printmsg("Bands: %s" % network_bands)
                    if network_notes != "":
                        self.printmsg("Notes: %s" % network_notes)

        finally:
            database_file.close()
