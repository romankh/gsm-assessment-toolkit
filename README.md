# GSM Assessment Toolkit - GAT

GAT is an evaluation framework for assessing security-related aspects of mobile networks based on the GSM standard.

The framework mainly relies on [gr-gsm](https://github.com/ptrkrysik/gr-gsm) for the processing of GSM-related information.


## Installation

There is no install script (yet), so the following steps are necessary:

- A working [gr-gsm](https://github.com/ptrkrysik/gr-gsm) installation
- Install Python argcomplete (sudo apt-get install python-argcomplete for example)
- Install Python requests (sudo pip install requests)
- Checkout master branch
- Make gat.py executable
- Execute gat.py

## Plugin List

- A51ReconstructionPlugin: Performs a reconstruction of A5/1 session keys using Kraken
- ArfcnPlugin: Provides information and conversion between ARFCN and frequencies
- CapturePlugin: Capturing transmissions with RTL-SDR
- DecoderPlugin: Decoding GSM transmissions
- GatAppSmsPlugin: Sending SMS (regular, silent or other) via [GAT-App](https://github.com/romankh/gat-app)
- HlrlookupPlugin: Performing HLR lookups. Currently only hlrlookups.com supported.
- ScanPlugin: Scanning a GSM band for base stations.
- TmsiPlugin: Extract TMSIs (and some IMSIs) from a capture.
- TmsiIdentificationPlugin: Identification of the TMSI of a subscriber.
- WiresharkPlugin: Starts a pre-configured wireshark for sniffing gsmtap traffic.
- AnalysisPlugin: Analyze different aspects of a capture (e.g. Immediate Assignments, Cipher Mode Commands, used encryption, stats, ...).

