# -*- coding: utf-8 -*-
import readline
import string

from core.plugin.controller import Controller
from core.plugin.interface import PluginError

__all__ = ["Cmd"]

PROMPT = 'gat > '
IDENTCHARS = string.ascii_letters + string.digits + '_'


class ConsoleUI(Controller):
    """
    Console provides the command line interface to the framework.

    This class is a customized variant of cmd.cmd module.
    It loads the plugins, and forwards command handling to the responsible Plugin.
    """
    prompt = PROMPT
    identchars = IDENTCHARS
    ruler = '='
    lastcmd = ''
    intro = """
   ______ _____  __  ___
  / ____// ___/ /  |/  /
 / / __  \__ \ / /|_/ /
/ /_/ / ___/ // /  / /
\____/ /____//_/  /_/
    ___                                                           __
   /   |   _____ _____ ___   _____ _____ ____ ___   ___   ____   / /_
  / /| |  / ___// ___// _ \ / ___// ___// __ `__ \ / _ \ / __ \ / __/
 / ___ | (__  )(__  )/  __/(__  )(__  )/ / / / / //  __// / / // /_
/_/  |_|/____//____/ \___//____//____//_/ /_/ /_/ \___//_/ /_/ \__/
  ______               __ __    _  __
 /_  __/____   ____   / // /__ (_)/ /_
  / /  / __ \ / __ \ / // //_// // __/
 / /  / /_/ // /_/ // // ,<  / // /_
/_/   \____/ \____//_//_/|_|/_/ \__/
"""
    outro = "Bye bye."
    help_footer = "type \"<command> -h\" for command specific help"

    def __init__(self, basedir, config, completekey='tab', stdin=None, stdout=None):
        """Instantiate a line-oriented interpreter framework.

        The optional argument 'completekey' is the readline name of a
        completion key; it defaults to the Tab key. If completekey is
        not None and the readline module is available, command completion
        is done automatically. The optional arguments stdin and stdout
        specify alternate input and output file objects; if not specified,
        sys.stdin and sys.stdout are used.
        """
        super(ConsoleUI, self).__init__(basedir, config)
        self.old_completer = None  # Saves the old completer for restoring at shutdown.
        self.cmdqueue = []
        self.completekey = completekey
        self._completion_matches = []

    def cmdloop(self):
        """
        Issue a prompt, parse input and dispatch to the corresponding method.
        """
        self.old_completer = readline.get_completer()  # save the old completer
        readline.set_completer(self.complete)
        readline.parse_and_bind(self.completekey + ": complete")  # set the autocomplete key for readline.
        readline.set_completer_delims(readline.get_completer_delims().replace('-', ''))  # remove "-" because options
        readline.set_completion_display_matches_hook(self.rl_display_hook)  # set our display hook
        # read history file if exists
        historyfile = self.config.getfile("gat", "historyfile", True)
        readline.read_history_file(historyfile)

        try:
            # print the intro after startup, if config entry show_intro is True.
            if self.config.getboolean("gat", "show_intro"):
                self.stdout.write(str(self.intro) + "\n")
            stop = None
            while not stop:
                if self.cmdqueue:  # TODO: check if we still need that.
                    line = self.cmdqueue.pop(0)
                else:
                    try:
                        line = raw_input(self.prompt)
                    except EOFError:
                        line = 'EOF'
                stop = self.handle_cmd(line)
            self.postloop()  # we are done, execute the post loop method.
        except KeyboardInterrupt:
            self.stdout.write("\nPlease use quit to exit the framework. Exiting now.\n")
            self.postloop()
        finally:
            readline.set_completer(self.old_completer)
            readline.write_history_file(historyfile)

    def postloop(self):
        """
        Hook method executed once when the cmdloop() method is about to return.

        We just print the outro message here.
        """
        self.stdout.write(str(self.outro) + "\n")

    def parseline(self, line):
        """
        Parse the line into a command name and a string containing the arguments.

        :param line: The line entered in the cli.
        :return: a tuple containing (command, args, line).
        'command' and 'args' may be None if the line couldn't be parsed.
        """
        line = line.strip()
        if not line:
            return None, None, line

        i, n = 0, len(line)
        while i < n and line[i] in self.identchars:
            i += 1
        cmd, arg = line[:i], line[i:].strip()
        return cmd, arg, line

    def handle_cmd(self, line):
        """
        Provides command handling.
        Uses parseline to parse the input, and hands the command and
        its arguments to the right method in the Plugin or the console.
        :param line: the input line from command line interface.
        :return: True, if the the console should break out the loop and exit, else False.
        """
        cmd, arg, line = self.parseline(line)

        if not line:
            return False  # do nothing on empty lines.
        if line == 'EOF':
            return False  # do nothing on EOF.

        return self._execute_command(cmd, arg)

    # replaces readline's original hook
    def rl_display_hook(self, substitution, matches, longest_match_length):
        """
        A replacement of readline's display hook.
        Customizes the output of completion.

        :param substitution:
        :param matches: a list of completion matches.
        :param longest_match_length:
        """
        self.stdout.write('\n')
        self.stdout.write('  '.join(matches) + '\n'),
        self.stdout.write(PROMPT + readline.get_line_buffer()),
        readline.redisplay()

    def complete(self, text, state):
        """
        Get the next possible completion for 'text'.
        If no complete command has been entered, then it completes against
        the commands provided by console and plugins. Otherwise it calls the
        complete_<command> method of the command.

        :param text: the input to complete.
        :param state: how many times has the method been called with the same 'text'.
        :return: the available completion for 'text' with state 'state'.
        """
        if state == 0:  # method has not been called for 'text', build a list of candidates.

            origline = readline.get_line_buffer()
            line = origline.lstrip()
            stripped = len(origline) - len(line)
            begidx = readline.get_begidx() - stripped

            if begidx > 0:  # we have a prefix, hence search for a command completer.
                cmd, args, foo = self.parseline(line)
                if cmd == '':  # no command has been entered, complete against available commands.
                    compfunc = self._complete_default
                elif cmd in self._plugin_containers or cmd in self._system_plugin_containers:  # command is provided by a Plugin, get the completer from there.
                    if cmd in self._plugin_containers:
                        container = self._plugin_containers[cmd]
                    else:
                        container = self._system_plugin_containers[cmd]
                    try:
                        # we need to get the completer from the container
                        completer = container.get_completer(cmd)
                        compfunc = completer.complete
                    except (AttributeError, PluginError):
                        compfunc = self._complete_default  # no completer found for the command, defaulting.
                else:  # command is provided by console.
                    try:
                        compfunc = getattr(self, 'complete_' + cmd)
                    except AttributeError:
                        compfunc = self._complete_default  # no completer found, defaulting.
            else:  # no prefix, we complete against the command names.
                compfunc = self._complete_commandnames

            self._completion_matches = compfunc(line)  # get the list from the chosen completer.
        try:
            return self._completion_matches[state]  # return the completion entry for 'state'.
        except IndexError:
            return None
