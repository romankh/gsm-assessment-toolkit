#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import importlib
import os

from core.common.config import ConfigProvider

if __name__ == '__main__':
    """
    Instantiate and start the console.
    """

    """
    Install:
        - sudo apt-get install python-argcomplete
        - sudo pip install requests
    """
    # change to base directory
    filepath = os.path.realpath(__file__)
    basedir = os.path.dirname(filepath)
    os.chdir(basedir)

    # load config
    conf = ConfigProvider()

    parser = argparse.ArgumentParser(description='GSM Assessment Toolkit')
    parser.add_argument('--ui-class', action="store", dest="ui_class",
                        help="Override the UI class configured in config file.")
    args = parser.parse_args()

    ui_clazz_full = args.ui_class
    if ui_clazz_full is None:
        ui_clazz_full = conf.get("gat", "ui_class")

    # get the configured UI class
    ui_clazz_module, ui_clazz_name = ui_clazz_full.rsplit(".", 1)
    try:
        ui_clazz = getattr(importlib.import_module(ui_clazz_module), ui_clazz_name)
    except Exception as e:
        print "Failed to load UI: %s" % e.message
        exit(1)

    # instantiate UI class and start it.
    app = ui_clazz(basedir, conf)
    app.cmdloop()
