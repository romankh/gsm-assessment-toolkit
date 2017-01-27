# -*- coding: utf-8 -*-
import inspect
import shlex
import sys
from copy import deepcopy

from gat.core.common.completer import GatCompleter
from gat.core.common.parser import ConsoleArgumentParser, GatHelpFormatter, ArgumentParserError, HelpActionCall


class PluginBase(object):
    """
    Base class for plugins.
    """

    def __init__(self, controller):
        """
        Constructor for plugins.
        :param pmsg: the output function for printing messages to console.
        """
        self.controller = controller
        self._config_provider = controller.config
        self._data_access_provider = controller.data_access_provider
        self.__pmsg = controller.pmsg

    def printmsg(self, msg):
        """
        Print a message to command line interface.
        :param msg: message to print.
        """
        self.__pmsg(msg)


class PluginError(Exception):
    """
    Common exception for any errors in plugins.
    """
    pass


class PluginContainer(object):
    def __init__(self, clazz, controller):
        self.clazz = clazz
        self.controller = controller
        self.instance = None

    def get_plugin_name(self):
        return self.clazz.name

    def get_plugin_description(self):
        return self.clazz.description

    def get_func_description(self, func_name):
        function = self.clazz.cmds[func_name]
        return function.description

    def get_func_parser(self, func_name):
        function = self.clazz.cmds[func_name]
        parser = ConsoleArgumentParser(prog=function.name, description=function.description,
                                       formatter_class=GatHelpFormatter)
        if hasattr(function, "_arglist"):
            arglist = deepcopy(function._arglist)
            arglist.reverse()  # reverse the list, as user expects the upper most decorator be the first argument.
            try:
                for a in arglist:
                    optionlist = a.pop('option_strings', ())
                    parser.add_argument(*optionlist, **a)
            except TypeError as e:
                raise PluginError("Invalid argument definition in @arg of %s" % func_name)

        if hasattr(function, "_arg_group_list"):  # handle argument groups
            arggrouplist = deepcopy(function._arg_group_list)
            arggrouplist.reverse()  # reverse the list, as user expects the upper most decorator be the first argument.
            try:
                for a in arggrouplist:
                    groupname = a["name"]
                    groupargs = a["args"]
                    group = parser.add_argument_group(groupname)

                    for arg in groupargs:
                        optionlist = arg.pop('option_strings', ())
                        group.add_argument(*optionlist, **arg)

            except TypeError as e:
                raise PluginError("Invalid argument definition in @arg_group of %s" % func_name)

        if hasattr(function, "_arg_exclusive_list"):  # handle exclusive arguments
            argexclusivelist = deepcopy(function._arg_exclusive_list)
            argexclusivelist.reverse()  # reverse the list, as user expects the upper most decorator be the first argument.
            try:
                for a in argexclusivelist:
                    groupargs = a["args"]
                    group = parser.add_mutually_exclusive_group()

                    for arg in groupargs:
                        optionlist = arg.pop('option_strings', ())
                        group.add_argument(*optionlist, **arg)

            except TypeError as e:
                raise PluginError("Invalid argument definition in @arg_exclusive of %s" % func_name)

        return parser

    def get_completer(self, func_name):
        parser = self.get_func_parser(func_name)
        completer = GatCompleter(parser, self.controller.data_access_provider)
        return completer

    def get_all_func(self):
        return self.clazz.cmds.keys()

    def get_instance(self):
        if self.instance is None:
            self.instance = self.clazz(self.controller)
        return self.instance

    def execute_func(self, func_name, args):
        function = self.clazz.cmds[func_name]
        command_parser = self.get_func_parser(func_name)

        def do_func(self, cmd, args):
            if not command_parser:
                raise PluginError("Parser for %s not found." % cmd)
            try:
                arguments = command_parser.parse_args(shlex.split(args))
            except ArgumentParserError as e:
                self.printmsg(e.message)
                return
            except HelpActionCall:
                return

            if not function:
                raise PluginError("Function for %s not found." % cmd)
            try:
                return function(self, arguments)
            except ArgumentParserError as e:  # if Plugin raises an ArgumentParserError, print the output
                self.printmsg(e.message)
                return
            except:  # handle uncaught exceptions in plugins
                type, value, tb = sys.exc_info()
                self.printmsg("ERROR: unhandled exception in Plugin command %s." % cmd)
                self.printmsg("Message was: %s" % value.message)

        self.clazz.do_func = do_func
        instance = self.get_instance()
        return instance.do_func(func_name, args)


def arg(*d_args, **d_kwargs):
    """
    Decorator for arguments.
    Creates a list of arguments for the parser in the method.

    :param d_args: a dictionary of argparse options.
    :param d_kwargs:
    """
    if len(d_args) < 1 and len(d_kwargs) < 1:
        raise PluginError("No argument specification was provided in @arg")

    def wrapper(func):
        arguments = dict(option_strings=d_args, **d_kwargs)
        arglist = getattr(func, '_arglist', [])
        arglist.append(arguments)
        setattr(func, '_arglist', arglist)
        return func

    return wrapper


def arg_group(*d_args, **d_kwargs):
    try:
        name = d_kwargs['name']
    except KeyError as e:
        raise PluginError("Argument 'name' to @arg_group is missing")
    try:
        arg_functions = d_kwargs['args']
    except KeyError as e:
        raise PluginError("Argument 'args' to @arg_group is missing")

    dict_args = []
    for argument in arg_functions:
        func_d_args = argument.func_closure[0].cell_contents
        func_d_kwargs = argument.func_closure[1].cell_contents
        arguments = dict(option_strings=func_d_args, **func_d_kwargs)
        dict_args.append(arguments)

    group = {"name": name, "args": dict_args}

    def wrapper(func):
        arggrouplist = getattr(func, '_arg_group_list', [])
        arggrouplist.append(group)
        setattr(func, '_arg_group_list', arggrouplist)
        return func

    return wrapper


def arg_exclusive(*d_args, **d_kwargs):
    try:
        arg_functions = d_kwargs['args']
    except KeyError as e:
        raise PluginError("Argument 'args' to @arg_exclusive is missing")

    dict_args = []
    for argument in arg_functions:
        func_d_args = argument.func_closure[0].cell_contents
        func_d_kwargs = argument.func_closure[1].cell_contents
        arguments = dict(option_strings=func_d_args, **func_d_kwargs)
        dict_args.append(arguments)

    exclusive_group = {"args": dict_args}

    def wrapper(func):
        argexclusivelist = getattr(func, '_arg_exclusive_list', [])
        argexclusivelist.append(exclusive_group)
        setattr(func, '_arg_exclusive_list', argexclusivelist)
        return func

    return wrapper


def cmd(*d_args, **d_kwargs):
    try:
        name = d_kwargs['name']
    except KeyError as e:
        raise PluginError("Argument 'name' to @cmd is missing")

    try:
        description = d_kwargs['description']
    except KeyError as e:
        raise PluginError("Argument 'description' to @cmd is missing in %s" % name)

    if len(d_kwargs) > 2:
        raise PluginError("Unknown argument to @cmd in %s" % name)

    def wrapper(func):
        func.name = name
        func.description = description
        func._is_cmd = True
        return func

    return wrapper


def plugin(*d_args, **d_kwargs):
    try:
        name = d_kwargs['name']
    except KeyError as e:
        raise PluginError("Argument 'name' to @plugin is missing")

    try:
        description = d_kwargs['description']
    except KeyError as e:
        raise PluginError("Argument 'description' to @plugin is missing in %s" % name)

    if len(d_kwargs) > 2:
        raise PluginError("Unknown argument to @plugin in %s" % name)

    def wrapper(cls):
        members = dict(inspect.getmembers(cls, predicate=inspect.ismethod))  # get the class members for processing.
        cls._is_plugin = True
        cls.name = name
        cls.description = description
        cls.cmds = dict()

        for m in members:  # process every member function
            f = members[m]
            if hasattr(f, '_is_cmd'):
                # if function has attribute '_is_cmd',
                # we consider it a command we want to provide.

                # add command to the Plugin's list of provided commands
                if cls.cmds.has_key(f.name):
                    raise PluginError("Function %s already defined" % f.name)
                cls.cmds[f.name] = f
        return cls

    return wrapper
