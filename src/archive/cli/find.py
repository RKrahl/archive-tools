"""Implement the find subcommand.
"""

import datetime
import fnmatch
from pathlib import Path
import re
from archive.archive import Archive
from archive.tools import parse_date


class timeinterval:
    """Represent a half-bounded time interval, e.g. all points in time
    earlier or later then a given moment.
    """

    @staticmethod
    def _parse_string(s):
        rel_string_re = re.compile(r"^([+-])(\d+(?:\.\d+)?)(d|h|m)?$")
        abs_string_re = re.compile(r"""^
            ([<>])\s*
            (\d{4})-(\d{2})-(\d{2})
            (?:[ T](\d{2}):(\d{2}):(\d{2}))?
        $""", re.X)
        m = rel_string_re.match(s)
        if m:
            (sign, num, unit) = m.groups()
            if unit is None:
                unit = 'd'
            direct = '<' if sign == '+' else '>'
            now = datetime.datetime.now()
            td_argmap = {'d': 'days', 'h': 'hours', 'm': 'minutes'}
            td_arg = {td_argmap[unit]: float(num)}
            point = now - datetime.timedelta(**td_arg)
            return (direct, point.timestamp())
        m = abs_string_re.match(s)
        if m:
            (direct, day, month, year, hour, minute, sec) = m.groups()
            if hour is None:
                point = datetime.datetime(int(day), int(month), int(year))
            else:
                point = datetime.datetime(int(day), int(month), int(year),
                                          int(hour), int(minute), int(sec))
            return (direct, point.timestamp())
        if s[0] in {'<', '>'}:
            direct = s[0]
            point = parse_date(s[1:].strip())
            return (direct, point.timestamp())
        raise ValueError("Invalid intervall string '%s'" % s)

    def __init__(self, s):
        self.direct, self.point = self._parse_string(s)

    def match(self, timestamp):
        if self.direct == '<':
            return timestamp < self.point
        elif self.direct == '>':
            return timestamp > self.point

class SearchFilter:

    def __init__(self, args):
        self.name = args.name
        self.type = args.type
        self.mtime = args.mtime

    def __call__(self, fileinfo):
        if self.name and not fnmatch.fnmatch(fileinfo.path.name, self.name):
            return False
        if self.type and fileinfo.type != self.type:
            return False
        if self.mtime and not self.mtime.match(fileinfo.mtime):
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
    parser.add_argument('--type', choices=['f', 'd', 'l'],
                        help="find entries by type")
    parser.add_argument('--name', metavar="pattern",
                        help=("find entries whose file name (with leading "
                              "directories removed) matches pattern"))
    parser.add_argument('--mtime', metavar="time",
                        help="find entries by modification time",
                        type=timeinterval)
    parser.add_argument('archives', metavar="archive", type=Path, nargs='+')
    parser.set_defaults(func=find)
