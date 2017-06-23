# -*- coding: utf-8 -*-

import argparse
import re as _re


class ArgumentParserError(Exception):
    """
    Common exception for errors during argument parsing.
    """
    pass


class GatHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """
    Help message formatter which adds default values to argument help.
    """

    def __init__(self, prog, indent_increment=2, max_help_position=30, width=140):
        super(GatHelpFormatter, self).__init__(prog, indent_increment, max_help_position, width)

    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not None and action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


class HelpActionCall(Exception):
    """
    Exception type for calls on the help action.
    Was used to prevent side effects when calling help.
    """
    # TODO: evaluate if we still need this.
    pass


class _HelpAction(argparse.Action):
    """
    A customized action to print help output to command line interface.
    """

    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None):
        super(_HelpAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        """
        Print help if the help action is called.
        """
        parser.print_help()


class _FilePathAction(argparse._StoreAction):
    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 type="r",
                 required=False,
                 help=None):
        self.dest = dest
        self.default = default
        self.type = type
        self.required = required
        self.help = help

        self.file_type = argparse.FileType(type)

        super(_FilePathAction, self).__init__(
            option_strings,
            dest=dest,
            default=default,
            required=required,
            help=help)


def _ActionsContainer__init__(self,
                              description,
                              prefix_chars,
                              argument_default,
                              conflict_handler):
    '''
    override action container init to register file action
    :param self:
    :param description:
    :param prefix_chars:
    :param argument_default:
    :param conflict_handler:
    :return:
    '''

    super(argparse._ActionsContainer, self).__init__()

    self.description = description
    self.argument_default = argument_default
    self.prefix_chars = prefix_chars
    self.conflict_handler = conflict_handler

    # set up registries
    self._registries = {}

    # register actions
    self.register('action', None, argparse._StoreAction)
    self.register('action', 'store', argparse._StoreAction)
    self.register('action', 'store_const', argparse._StoreConstAction)
    self.register('action', 'store_true', argparse._StoreTrueAction)
    self.register('action', 'store_false', argparse._StoreFalseAction)
    self.register('action', 'append', argparse._AppendAction)
    self.register('action', 'append_const', argparse._AppendConstAction)
    self.register('action', 'count', argparse._CountAction)
    self.register('action', 'help', argparse._HelpAction)
    self.register('action', 'version', argparse._VersionAction)
    self.register('action', 'parsers', argparse._SubParsersAction)
    self.register('action', 'store_path', _FilePathAction)

    # raise an exception if the conflict handler is invalid
    self._get_handler()

    # action storage
    self._actions = []
    self._option_string_actions = {}

    # groups
    self._action_groups = []
    self._mutually_exclusive_groups = []

    # defaults storage
    self._defaults = {}

    # determines whether an "option" looks like a negative number
    self._negative_number_matcher = _re.compile(r'^-\d+$|^-\d*\.\d+$')

    # whether or not there are any optionals that look like negative
    # numbers -- uses a list so it can be shared and edited
    self._has_negative_number_optionals = []


def error(self, message):
    """
    Error handler that prints usage info of the command to command line interface.
    :param message: a message that is printed in front of the usage info.
    """
    raise ArgumentParserError(message + "\n" + self.format_usage())


def _parse_known_args(self, arg_strings, namespace):
    """
    Patch for _parse_known_args, we only add two lines in consume_optional
    """
    # replace Arg strings that are file references
    if self.fromfile_prefix_chars is not None:
        arg_strings = self._read_args_from_files(arg_strings)

    # map all mutually exclusive arguments to the other arguments
    # they can't occur with
    action_conflicts = {}
    for mutex_group in self._mutually_exclusive_groups:
        group_actions = mutex_group._group_actions
        for i, mutex_action in enumerate(mutex_group._group_actions):
            conflicts = action_conflicts.setdefault(mutex_action, [])
            conflicts.extend(group_actions[:i])
            conflicts.extend(group_actions[i + 1:])

    # find all option indices, and determine the arg_string_pattern
    # which has an 'O' if there is an option at an index,
    # an 'A' if there is an argument, or a '-' if there is a '--'
    option_string_indices = {}
    arg_string_pattern_parts = []
    arg_strings_iter = iter(arg_strings)
    for i, arg_string in enumerate(arg_strings_iter):

        # all args after -- are non-options
        if arg_string == '--':
            arg_string_pattern_parts.append('-')
            for arg_string in arg_strings_iter:
                arg_string_pattern_parts.append('A')

        # otherwise, add the Arg to the Arg strings
        # and note the index if it was an option
        else:
            option_tuple = self._parse_optional(arg_string)
            if option_tuple is None:
                pattern = 'A'
            else:
                option_string_indices[i] = option_tuple
                pattern = 'O'
            arg_string_pattern_parts.append(pattern)

    # join the pieces together to form the pattern
    arg_strings_pattern = ''.join(arg_string_pattern_parts)

    # converts Arg strings to the appropriate and then takes the action
    seen_actions = set()
    seen_non_default_actions = set()

    def take_action(action, argument_strings, option_string=None):
        seen_actions.add(action)
        argument_values = self._get_values(action, argument_strings)

        # error if this argument is not allowed with other previously
        # seen arguments, assuming that actions that use the default
        # value don't really count as "present"
        if argument_values is not action.default:
            seen_non_default_actions.add(action)
            for conflict_action in action_conflicts.get(action, []):
                if conflict_action in seen_non_default_actions:
                    msg = argparse._('not allowed with argument %s')
                    action_name = argparse._get_action_name(conflict_action)
                    raise argparse.ArgumentError(action, msg % action_name)

        # take the action if we didn't receive a SUPPRESS value
        # (e.g. from a default)
        if argument_values is not argparse.SUPPRESS:
            action(self, namespace, argument_values, option_string)

    # function to convert arg_strings into an optional action
    def consume_optional(start_index):

        # get the optional identified at this index
        option_tuple = option_string_indices[start_index]
        action, option_string, explicit_arg = option_tuple

        # identify additional optionals in the same Arg string
        # (e.g. -xyz is the same as -x -y -z if no args are required)
        match_argument = self._match_argument
        action_tuples = []
        while True:

            # if we found no optional action, skip it
            if action is None:
                extras.append(arg_strings[start_index])
                return start_index + 1

            # if there is an explicit argument, try to match the
            # optional's string arguments to only this
            if explicit_arg is not None:
                arg_count = match_argument(action, 'A')

                # if the action is a single-dash option and takes no
                # arguments, try to parse more single-dash options out
                # of the tail of the option string
                chars = self.prefix_chars
                if arg_count == 0 and option_string[1] not in chars:
                    action_tuples.append((action, [], option_string))
                    char = option_string[0]
                    option_string = char + explicit_arg[0]
                    new_explicit_arg = explicit_arg[1:] or None
                    optionals_map = self._option_string_actions
                    if option_string in optionals_map:
                        action = optionals_map[option_string]
                        explicit_arg = new_explicit_arg
                    else:
                        msg = argparse._('ignored explicit argument %r')
                        raise argparse.ArgumentError(action, msg % explicit_arg)

                # if the action expect exactly one argument, we've
                # successfully matched the option; exit the loop
                elif arg_count == 1:
                    stop = start_index + 1
                    args = [explicit_arg]
                    action_tuples.append((action, args, option_string))
                    break

                # error if a double-dash option did not use the
                # explicit argument
                else:
                    msg = argparse._('ignored explicit argument %r')
                    raise argparse.ArgumentError(action, msg % explicit_arg)

            # if there is no explicit argument, try to match the
            # optional's string arguments with the following strings
            # if successful, exit the loop
            else:
                start = start_index + 1
                selected_patterns = arg_strings_pattern[start:]
                arg_count = match_argument(action, selected_patterns)
                stop = start + arg_count
                args = arg_strings[start:stop]
                action_tuples.append((action, args, option_string))
                break

        # add the Optional to the list and return the index at which
        # the Optional's string args stopped
        assert action_tuples
        for action, args, option_string in action_tuples:
            take_action(action, args, option_string)
            # we return throw a HelpActionCall to signal a call of _HelpAction
            # this because orginal parser would exit after call of optional -h
            if issubclass(type(action), _HelpAction):
                raise HelpActionCall()
        return stop

    # the list of Positionals left to be parsed; this is modified
    # by consume_positionals()
    positionals = self._get_positional_actions()

    # function to convert arg_strings into positional actions
    def consume_positionals(start_index):
        # match as many Positionals as possible
        match_partial = self._match_arguments_partial
        selected_pattern = arg_strings_pattern[start_index:]
        arg_counts = match_partial(positionals, selected_pattern)

        # slice off the appropriate Arg strings for each Positional
        # and add the Positional and its args to the list
        for action, arg_count in zip(positionals, arg_counts):
            args = arg_strings[start_index: start_index + arg_count]
            start_index += arg_count
            take_action(action, args)

        # slice off the Positionals that we just parsed and return the
        # index at which the Positionals' string args stopped
        positionals[:] = positionals[len(arg_counts):]
        return start_index

    # consume Positionals and Optionals alternately, until we have
    # passed the last option string
    extras = []
    start_index = 0
    if option_string_indices:
        max_option_string_index = max(option_string_indices)
    else:
        max_option_string_index = -1
    while start_index <= max_option_string_index:

        # consume any Positionals preceding the next option
        next_option_string_index = min([
                                           index
                                           for index in option_string_indices
                                           if index >= start_index])
        if start_index != next_option_string_index:
            positionals_end_index = consume_positionals(start_index)

            # only try to parse the next optional if we didn't consume
            # the option string during the positionals parsing
            if positionals_end_index > start_index:
                start_index = positionals_end_index
                continue
            else:
                start_index = positionals_end_index

        # if we consumed all the positionals we could and we're not
        # at the index of an option string, there were extra arguments
        if start_index not in option_string_indices:
            strings = arg_strings[start_index:next_option_string_index]
            extras.extend(strings)
            start_index = next_option_string_index

        # consume the next optional and any arguments for it
        start_index = consume_optional(start_index)

    # consume any positionals following the last Optional
    stop_index = consume_positionals(start_index)

    # if we didn't consume all the argument strings, there were extras
    extras.extend(arg_strings[stop_index:])

    # if we didn't use all the Positional objects, there were too few
    # Arg strings supplied.
    if positionals:
        self.error(argparse._('too few arguments'))

    # make sure all required actions were present, and convert defaults.
    for action in self._actions:
        if action not in seen_actions:
            if action.required:
                name = argparse._get_action_name(action)
                self.error(argparse._('argument %s is required') % name)
            else:
                # Convert action default now instead of doing it before
                # parsing arguments to avoid calling convert functions
                # twice (which may fail) if the argument was given, but
                # only if it was defined already in the namespace
                if (action.default is not None and
                        isinstance(action.default, basestring) and
                        hasattr(namespace, action.dest) and
                            action.default is getattr(namespace, action.dest)):
                    setattr(namespace, action.dest,
                            self._get_value(action, action.default))

    # make sure all required groups had one option present
    for group in self._mutually_exclusive_groups:
        if group.required:
            for action in group._group_actions:
                if action in seen_non_default_actions:
                    break

            # if no actions were used, report the error
            else:
                names = [argparse._get_action_name(action)
                         for action in group._group_actions
                         if action.help is not argparse.SUPPRESS]
                msg = argparse._('one of the arguments %s is required')
                self.error(msg % ' '.join(names))

    # return the updated namespace and the extra arguments
    return namespace, extras


# monkey-patching
argparse._HelpAction = _HelpAction
argparse._FileAction = _FilePathAction
argparse._ActionsContainer.__init__ = _ActionsContainer__init__
argparse.ArgumentParser.error = error
argparse.ArgumentParser._parse_known_args = _parse_known_args


class ConsoleArgumentParser(argparse.ArgumentParser):
    """
    Subclass of ArgumentParser.
    """
    pass
