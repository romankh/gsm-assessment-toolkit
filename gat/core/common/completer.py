# -*- coding: utf-8 -*-
import argcomplete
import argparse
import shlex

from gat.core.common.parser import _FilePathAction


class ArgcompleteException(Exception):
    """
    Common exception for completion.
    """
    pass


# Todo: check if split_line and default_validator are in use

def split_line(line, point):
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    words = []

    def split_word(word):
        # TODO: make this less ugly
        point_in_word = len(word) + point - lexer.instream.tell()
        if isinstance(lexer.state, basestring) and lexer.state in lexer.whitespace:
            point_in_word += 1
        if point_in_word > len(word):
            words.append(word)
            word = ''
        prefix, suffix = word[:point_in_word], word[point_in_word:]
        prequote = ''
        if lexer.state is not None and lexer.state in lexer.quotes:
            prequote = lexer.state

        first_colon_pos = lexer.first_colon_pos if ':' in word else None

        return prequote, prefix, suffix, words, first_colon_pos

    while True:
        try:
            word = lexer.get_token()
            if word == lexer.eof:
                return "", "", "", words, None
            if lexer.instream.tell() >= point:
                return split_word(word)
            words.append(word)
        except ValueError:
            if lexer.instream.tell() >= point:
                return split_word(lexer.token)
            else:
                raise ArgcompleteException("Unexpected internal state.")


def default_validator(completion, prefix):
    return completion.startswith(prefix)


class GatCompleter(object):
    def __init__(self, parser, data_access_provider):
        self.__parser = parser
        self.__data_access_provider = data_access_provider
        self.last_positional = []
        self.used_options = []
        self.option_display_str = []

    def complete(self, line):
        comp_line = line
        comp_point = len(line)
        cword_prequote, cword_prefix, cword_suffix, comp_words, first_colon_pos = argcomplete.split_line(comp_line,
                                                                                                         comp_point)
        # reset display strings for options
        self.option_display_str = []

        # actions already chosen, we don't provide them anymore
        visited_actions = []

        # list of possible completion values
        completions = []

        # is the last action completed ?
        last_action_finished = True

        # if the last word starts with a '-', it was an option,
        # we need to check if this option takes an argument
        if comp_words[-1].startswith(self.__parser.prefix_chars):
            last_action_finished = False

        # collect visisted actions
        for action in self.__parser._actions:
            for option in action.option_strings:
                if option in line:
                    visited_actions.append(action)
                    # if last_action_finished is False, the last word was an option
                    # then we check if the current option is this option
                    # if so, we check if the option needs an argument
                    if not last_action_finished and comp_words[-1] in action.option_strings:
                        if action.choices is not None:  # last action was choices action, we return those choices
                            for c in action.choices:
                                if c.startswith(cword_prefix) or unicode(c).startswith(cword_prefix):
                                    completions.append(c)
                            return completions
                        elif isinstance(action, _FilePathAction):
                            file_completion_result = self.__data_access_provider.complete(cword_prefix)
                            # print file_completion_result
                            completions.extend(file_completion_result)
                            return completions
                        if action.type is None:
                            last_action_finished = True

        if not last_action_finished:
            if action.choices is not None:
                pass
            else:
                return []

        # get options from parser
        for action in self.__parser._actions:
            if action not in visited_actions:
                # ensure it is no subparser instance
                if not isinstance(action, argparse._SubParsersAction):
                    for option in action.option_strings:
                        if option.startswith(cword_prefix):
                            completions.append(option)

        return completions
