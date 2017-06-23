# -*- coding: utf-8 -*-
import os

from core.plugin.interface import PluginError


# Todo: Implement Session Management
class DataAccessProvider(object):
    def __init__(self, config_provider):
        super(DataAccessProvider, self).__init__()
        self.__config_provider = config_provider
        # todo: if file store does not exist, create the dir

    def getstorepath(self):
        file_store_path = self.__config_provider.get("gat", "filestore")
        return os.path.expanduser(file_store_path)

    def getfile(self, filename):
        if not os.path.isabs(filename):
            filename = os.path.join(self.getstorepath(), filename)

        if os.path.isfile(filename):
            return filename
        else:
            raise FileNotFoundError("file not found")

    def getfilepath(self, filename):
        if not os.path.isabs(filename):
            filename = os.path.join(self.getstorepath(), filename)
        return filename

    def complete(self, filepath):
        path = os.path.dirname(filepath)
        prefix = os.path.basename(filepath)

        if not os.path.isabs(path):
            path = os.path.join(self.getstorepath(), path)

        if not os.path.isdir(path):
            raise FileNotFoundError("file not found")

        result = []
        for file in os.listdir(path):
            if file.startswith(prefix):
                if os.path.isdir(os.path.join(path, file)):
                    result.append(file + os.sep)
                else:
                    result.append(file)

        return result


class FileNotFoundError(PluginError):
    """
    Exception signalling that a file was not found by data management.
    """
    pass
