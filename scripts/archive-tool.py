#! /usr/bin/python

import argparse
import warnings
import sys
import archive.cli
from archive.exception import *


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
warnings.showwarning = showwarning


argparser = argparse.ArgumentParser()
archive.cli.add_subparsers(argparser)
args = argparser.parse_args()
if not hasattr(args, "func"):
    argparser.error("subcommand is required")
try:
    args.func(args)
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
