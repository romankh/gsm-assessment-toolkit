# -*- coding: utf-8 -*-
import os
import pkgutil
import sys

from gat.core.common.data import DataAccessProvider
from gat.core.plugin.interface import PluginError, PluginContainer, cmd, PluginBase, plugin, arg, subcmd


class Controller(object):
    def __init__(self, basedir, config):
        import sys
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.config = config
        self.data_access_provider = DataAccessProvider(self.config)
        self.basedir = basedir
        self._system_plugin_containers = dict()
        # dict that holds the commands together with the Plugin container holding the Plugin.
        self._plugin_containers = dict()
        # Todo: move path to config file, add multipath support for custom plugins
        try:
            system_plugin_path = os.path.join(self.basedir, "gat/plugins")
            user_plugin_path = config.getfile("gat", "userplugins")
            self._load_plugins(system_plugin_path, user_plugin_path)
        except PluginError as e:
            # if any plugin error happens when loading, print the error message and exit.
            self.pmsg(e.message)
            exit(1)

    def _load_plugins(self, system_plugin_path, user_plugin_path=None):
        """
        Load all plugins found in the specified path.

        :param path_list: a list of path where the plugins are located.
        """

        sys_container = PluginContainer(self.SystemPlugin, self)
        sys_cmds = getattr(self.SystemPlugin, "cmds")
        for c in sys_cmds:
            if c in self._plugin_containers:
                raise PluginError('Found duplicate usage of command name %s' % c)
            self._system_plugin_containers[c] = sys_container

        def __load_modules(mods, is_user):
            prefix = ""
            if not is_user:
                prefix = "gat.plugins."

            for loader, mod_name, ispkg in mods:
                if mod_name not in sys.modules:  # Ensure that module isn't already loaded
                    loaded_mod = __import__(prefix + mod_name, fromlist=[mod_name])  # import the module
                    # get the name of the Plugin class
                    class_name = ""
                    # iterate through all loaded module
                    for name, cls in loaded_mod.__dict__.items():
                        # check if class has the the right attribute set
                        if hasattr(cls, '_is_plugin'):
                            class_name = name
                    try:
                        loaded_class = getattr(loaded_mod, class_name)
                        container = PluginContainer(loaded_class, self)

                        cmds = getattr(loaded_class, "cmds")

                        for c in cmds:
                            if c in self._plugin_containers:
                                raise PluginError('Found duplicate usage of command name %s' % c)
                            self._plugin_containers[c] = container
                    except AttributeError as e:
                        self.pmsg("WARNING: Failed to load Plugin %s. Skipping this Plugin." % class_name)
                        self.pmsg("Message was: %s" % e.message)

        # list modules in the Plugin path
        system_mods = pkgutil.iter_modules(path=[system_plugin_path])
        __load_modules(system_mods, False)
        if user_plugin_path is not None:
            sys.path.append(user_plugin_path)
            framework_mods = pkgutil.iter_modules(path=[user_plugin_path])
            __load_modules(framework_mods, True)

    def _complete_commandnames(self, command, *ignored):
        """
        Completes command names of both system commands from console and
        commands provided by plugins.

        :param command: the name of the command
        :param ignored: the arguments to the command, which are ignored for completion.
        :return: a list of command names for completion.
        """
        names = [c for c in self._system_plugin_containers if c.startswith(command)]  # add Sys Plugin commands
        names += [c for c in self._plugin_containers if c.startswith(command)]  # add Plugin commands
        return names

    def _complete_default(self, *ignored):
        """
        Completes input lines where no command-specific complete_*() method is available.

        :param ignored:
        :return: an empty list.
        """
        return []

    # todo: change this to be dependent from the console object. (or can be overridden)
    def pmsg(self, msg):
        """
        Print a message to stdout. This method is provided to plugins for message output.

        :param msg: message to print.
        """
        if msg:
            self.stdout.write(msg)
            if msg[-1] != '\n':
                self.stdout.write('\n')

    def _execute_command(self, cmd, arg):
        plugincontainer = None
        if cmd in self._plugin_containers:
            plugincontainer = self._plugin_containers[cmd]
        elif cmd in self._system_plugin_containers:
            plugincontainer = self._system_plugin_containers[cmd]

        if plugincontainer is None:
            self.pmsg("Command not found")
        else:
            try:
                return plugincontainer.execute_func(cmd, arg)
            except PluginError as e:
                self.pmsg(e.message)

    @plugin(name='System Plugin', description='....')
    class SystemPlugin(PluginBase):
        @cmd(name='clear', description='Clear the screen.')
        def do_clear(self, ignored):
            """
            Clear screen.
            :param ignored:
            :return:
            """
            pkgutil.os.system('clear')

        @cmd(name='quit', description='Quit the framework.')
        def do_quit(self, ignored):
            """
            System command for quitting the application.
            :param ignored: arguments to the command are ignored.
            :return: True.
            """
            return True

        @cmd(name='help', description='Prints an overview of the available commands.')
        def do_help(self, ignored):
            """
            System command for providing help text.
            Prints out a list of available commands to the cli.

            :param ignored: arguments to the command are ignored.
            """
            _indent = " " * 2

            self.printmsg("The following list gives an overview of the available commands.")
            self.printmsg("For a command specific help type '<command> -h'." + "\n\n")

            def print_plugin_help(plugin):
                plugin_header = plugin.get_plugin_name()
                if plugin.get_plugin_description() is not None:
                    plugin_header += ": " + plugin.get_plugin_description()
                self.printmsg(plugin_header)

                cmds = plugin.get_all_func()
                for cmd in cmds:
                    self.printmsg(_indent + cmd + ": " + plugin.get_func_description(cmd))
                self.printmsg('\n')

            for plugin in set(self.controller._system_plugin_containers.values()):  # get unique Plugin container
                print_plugin_help(plugin)

            for plugin in set(self.controller._plugin_containers.values()):  # get unique Plugin container
                print_plugin_help(plugin)

        @cmd(name='session', description='Manage sessions.', parent=True)
        def session(self, args):
            pass

        @subcmd(name='show', help='Show current session.', parent="session")
        def session_show(self, args):
            self.printmsg("Default session.")
            self.printmsg("Sessions are not implemented yet.")

        @subcmd(name='create', help='Create a new session.', parent="session")
        def session_create(self, args):
            self.printmsg("Sessions are not implemented yet.")

        @subcmd(name='switch', help='Switch to an existing session.', parent="session")
        def session_switch(self, args):
            self.printmsg("Sessions are not implemented yet.")

        @cmd(name='config', description='Manage configuration.', parent=True)
        def config(self, args):
            pass

        @subcmd(name='show', help='Show current configuration.', parent="config")
        def config_show(self, args):

            sections = self._config_provider.getSections()
            for section in sections:
                self.printmsg("[{}]".format(section))
                items = self._config_provider.getItems(section)
                for item in items:
                    self.printmsg("  {} = {}".format(item[0], item[1]))

        @arg("-s", action="store_true", dest="store",
             help="Save the changes to config file. If not set, the value is only changed for the current session.",
             default=False)
        @arg("section", action="store", type=str, help="Name of the section.")
        @arg("option", action="store", type=str, help="Name of the option.")
        @arg("value", action="store", type=str, help="Value to set.")
        @subcmd(name='set', help='Set the value of a config option.', parent="config")
        def config_set(self, args):
            self._config_provider.set(args.section, args.option, args.value)
            if args.store:
                self._config_provider.persist()
