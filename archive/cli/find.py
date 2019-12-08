"""Implement the find subcommand.
"""

import fnmatch
from pathlib import Path
from archive.archive import Archive

class SearchFilter:

    def __init__(self, args):
        self.name = args.name

    def __call__(self, fileinfo):
        if self.name and not fnmatch.fnmatch(fileinfo.path.name, self.name):
            return False
        return True


def find(args):
    searchfilter = SearchFilter(args)
    for path in args.archives:
        with Archive().open(path) as archive:
            for fi in filter(searchfilter, archive.manifest):
                print("%s:%s" % (path, fi.path))

def add_parser(subparsers):
    parser = subparsers.add_parser('find',
                                   help=("search for files in archives"))
    parser.add_argument('--name', metavar="pattern",
                        help=("find entries whose file name (with leading "
                              "directories removed) matches pattern"))
    parser.add_argument('archives', metavar="archive", type=Path, nargs='+')
    parser.set_defaults(func=find)
