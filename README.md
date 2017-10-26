# GSM Assessment Toolkit - GAT

GAT is an evaluation framework for assessing security-related aspects of mobile networks based on the GSM standard.

The framework mainly relies on [gr-gsm](https://github.com/ptrkrysik/gr-gsm) for the processing of GSM-related information.

More information can be found in the [wiki](https://github.com/romankh/gsm-assessment-toolkit/wiki)

## Feature List

- Capturing transmissions, currently only using RTL-SDR. Support for UHD coming soon.
- Scanning for base stations, currently only using RTL-SDR. Support for UHD coming soon.
- Decoding captured transmissions (Control channels, voice channels).
- A5/1 key reconstruction using Kraken.
- Sending SMS (regular, silent and others) via [GAT-App](https://github.com/romankh/gat-app)
- Performing HLR lookups. Currently only hlrlookups.com supported.
- TMSI (and some IMSIs) sniffing / extraction
- Subscriber identification (TMSI - MSISDN correlation)
- Analysis of captured transmissions (e.g. Immediate Assignments, Cipher Mode Commands, used encryption). More coming soon.
- Utilities: Starting a preconfigured Wireshark, info about and conversion of ARFCN and frequencies, manipulation of burst-files, info lookup for MCC and MNC
