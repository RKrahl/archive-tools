"""Implement the find subcommand.
"""

from pathlib import Path
from archive.archive import Archive

class SearchFilter:

    def __init__(self, args):
        pass

    def __call__(self, fileinfo):
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
    parser.add_argument('archives', metavar="archive", type=Path, nargs='+')
    parser.set_defaults(func=find)
