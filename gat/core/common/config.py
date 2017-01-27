# -*- coding: utf-8 -*-
import os
import shutil
from ConfigParser import SafeConfigParser
from os.path import expanduser


class ConfigError(Exception):
    """
    Common exception for any errors in configuration.
    """
    pass


class ConfigProvider(object):
    __config = SafeConfigParser()

    def __init__(self):
        home = expanduser('~')
        config_path = os.path.join(home, '.gat')

        # provide configuration directory to console and plugins
        self.config_dir = config_path

        self.__config_file_path = os.path.join(config_path, 'gat.conf')
        # create default config directory and file if there is none
        if not os.path.isdir(config_path):
            os.makedirs(config_path, 0755)
            if not os.path.isfile(config_path):
                shutil.copy('core/misc/default.conf', self.__config_file_path)

        # read config
        self.__config.read(self.__config_file_path)

        # get usersessions and userplugins directories
        self.sessions_dir = expanduser(self.get('gat', 'usersessions'))
        self.userplugins_dir = expanduser(self.get('gat', 'userplugins'))

        # create directories if not exist
        if not os.path.isdir(self.sessions_dir):
            os.makedirs(self.sessions_dir, 0755)

        if not os.path.isdir(self.userplugins_dir):
            os.makedirs(self.userplugins_dir, 0755)

    def get(self, section, option):
        """
        Pass the arguments to the ConfigParser and get the
        option value from there.

        :param section: the section of the desired option
        :param option: the option that shall be retrieved
        :return:
        """
        return self.__config.get(section, option)

    def getint(self, section, option):
        return self.__config.getint(section, option)

    def getboolean(self, section, option):
        return self.__config.getboolean(section, option)

    def getfile(self, section, option):
        file = expanduser(self.get(section, option))
        if not os.path.isfile(file) and not os.path.isdir(file):
            return None
        return file

    def set(self, section, option, value):
        if self.__config.has_option(section, option):
            self.__config.set(section, option, value)
        else:
            raise ConfigError("Section or option not found.")

    def getOptions(self, section):
        return self.__config.options(section)

    def getSections(self):
        return self.__config.sections()

    def getItems(self, section):
        return self.__config.items(section)

    def persist(self):
        with open(self.__config_file_path, "wb") as configfile:
            self.__config.write(configfile)
