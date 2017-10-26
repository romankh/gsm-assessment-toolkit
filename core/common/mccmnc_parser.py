# -*- coding: utf-8 -*-
import csv
import urllib2
from bs4 import BeautifulSoup

wiki_url = "https://en.wikipedia.org/wiki/Mobile_country_code"
csv_header_data = ["MCC", "MNC", "Country", "Country Code", "Brand", "Operator", "Status", "Bands", "Note"]


class MccMncParser(object):
    def parse(self, destination):
        write_header = False

        response = urllib2.urlopen(wiki_url)
        html = response.read()

        html_soup = BeautifulSoup(html, "lxml")
        content_container = html_soup.find(id="mw-content-text")
        content = content_container.find("div", {"class": "mw-parser-output"})

        try:
            destination_file = open(destination, "w")
        except (OSError, IOError) as e:
            return "Error: cannot open destination file %s" % destination

        mode = ""
        country = ""
        country_code = ""

        counter = 0
        try:
            writer = csv.writer(destination_file, delimiter=";")
            if write_header:
                writer.writerow(csv_header_data)

            for element in content:
                if element.name == "h2":
                    mode, country, country_code = self.__handle_h2(mode)
                elif element.name == "h3" and mode == "nationaloperators":
                    country_tag = element.find("span", class_="mw-headline")
                    if country_tag is not None:
                        country, country_code = self.__parse_h3_tag(country_tag)
                elif element.name == "table":
                    csv_data = self.__parse_table(element, country, country_code)
                    counter += len(csv_data)
                    for csv_data_row in csv_data:
                        writer.writerow(csv_data_row)
        finally:
            destination_file.close()
            return "Updated database (%s entries)" % counter

    def __handle_h2(self, mode):
        if mode == "":
            return "testnetworks", "Test Networks", ""
        elif mode == "testnetworks":
            return "nationaloperators", "", ""
        else:
            return "internationaloperators", "International Operators", ""

    def __parse_h3_tag(self, country_tag):
        country_parts = country_tag["id"]
        country_parts = country_parts.replace("_", " ")
        country_parts = country_parts.replace(".27", "'").replace(".28", "(").replace(".29", ")")
        country_parts = country_parts.replace(".2C", ",").replace(".2F", "/")
        country_parts = country_parts.split("-", 1)

        country = country_parts[0].strip().encode("UTF-8")
        if len(country_parts) > 1:
            country_code = country_parts[1].strip().encode("UTF-8")
        else:
            country_code = ""
        return country, country_code

    def __parse_table(self, element, country, country_code):
        rows = element.find_all("tr")
        row_entries = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) > 0:
                mcc = self.__parse_td(cells[0]).encode("UTF-8")
                mnc = self.__parse_td(cells[1]).encode("UTF-8")
                if len(mcc) > 0 and len(mnc) > 0:
                    brand = self.__parse_td(cells[2]).encode("UTF-8")
                    operator = self.__parse_td(cells[3]).encode("UTF-8")
                    status = self.__parse_td(cells[4]).encode("UTF-8")
                    bands = self.__parse_td(cells[5]).encode("UTF-8")
                    note = self.__parse_td(cells[6]).encode("UTF-8")
                    row_entries.append([mcc, mnc, country, country_code, brand, operator, status, bands, note])
        return row_entries

    def __parse_td(self, td):
        [sup.extract() for sup in td.find_all("sup")]

        anchor = td.find("a")
        if anchor is not None:
            return anchor.string
        elif td.string is not None:
            return td.string
        else:
            return ""
