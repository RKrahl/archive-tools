"""Provide the subcommands of the archive-tool command line tool.
"""

import argparse
import importlib
import sys
import warnings
from archive.exception import *

subcmds = [ "create", "verify", "ls", "info", "check", "diff", "find", ]

def showwarning(message, category, filename, lineno, file=None, line=None):
    """Display ArchiveWarning in a somewhat more user friendly manner.
    All other warnings are formatted the standard way.
    """
    # This is a modified version of the function of the same name from
    # the Python standard library warnings module.
    if file is None:
        file = sys.stderr
        if file is None:
            # sys.stderr is None when run with pythonw.exe - warnings get lost
            return
    try:
        if issubclass(category, ArchiveWarning):
            s = "%s: %s\n" % (argparser.prog, message)
        else:
            s = warnings.formatwarning(message, category, 
                                       filename, lineno, line)
        file.write(s)
    except OSError:
        pass # the file (probably stderr) is invalid - this warning gets lost.

def archive_tool():
    warnings.showwarning = showwarning
    argparser = argparse.ArgumentParser()
    subparsers = argparser.add_subparsers(title='subcommands', dest='subcmd')
    for sc in subcmds:
        m = importlib.import_module('archive.cli.%s' % sc)
        m.add_parser(subparsers)
    args = argparser.parse_args()
    if not hasattr(args, "func"):
        argparser.error("subcommand is required")
    try:
        sys.exit(args.func(args))
    except ArgError as e:
        argparser.error(str(e))
    except ArchiveError as e:
        if isinstance(e, ArchiveCreateError):
            status = 1
        elif isinstance(e, ArchiveReadError):
            status = 1
        elif isinstance(e, ArchiveIntegrityError):
            status = 3
        else:
            raise
        print("%s %s: error: %s" % (argparser.prog, args.subcmd, e), 
              file=sys.stderr)
        sys.exit(status)
