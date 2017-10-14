# -*- coding: utf-8 -*-
from string import ljust


def columnize(string_list, columns):
    """
    Creates a table for a list of strings with a given number of columns
    :param string_list: the list with the strings
    :param columns: the number of columns
    :return: string representation of the columnized input strings
    """
    result = ""
    separator = "|"

    if not string_list:
        return result

    nonstrings = [i for i in range(len(string_list))
                  if not isinstance(string_list[i], str)]
    if nonstrings:
        raise TypeError, ("string_list[i] not a string for i in %s" %
                          ", ".join(map(str, nonstrings)))

    lists = [[] for i in range(columns)]
    column_lengths = [0 for i in range(columns)]
    tab_length = 1

    for i in range(len(string_list)):
        lists[i % columns].append(string_list[i])
        if len(string_list[i]) > column_lengths[i % columns]:
            column_lengths[i % columns] = len(string_list[i])

    for i in range(columns):
        tab_length += column_lengths[i] + 4

    result += "\n" + "=" * tab_length + "\n"
    for i in range(len(string_list)):
        col = i % columns
        result += separator + " " + "".join(ljust(string_list[i], column_lengths[col] + 2))
        if col == columns - 1:
            if i < columns:
                result += separator + "\n" + "=" * tab_length + "\n"
            else:
                result += separator + "\n" + "-" * tab_length + "\n"

    return result
