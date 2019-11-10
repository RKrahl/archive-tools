"""Provide the subcommands of the archive-tool command line tool.
"""

import importlib

subcmds = [ "create", "verify", "ls", "info", "check", ]

def add_subparsers(argparser):
    subparsers = argparser.add_subparsers(title='subcommands', dest='subcmd')
    for sc in subcmds:
        m = importlib.import_module('archive.cli.%s' % sc)
        m.add_parser(subparsers)
