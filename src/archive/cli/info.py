"""Implement the info subcommand.
"""

import datetime
from pathlib import Path
import stat
from archive.archive import Archive
from archive.exception import ArchiveReadError


def info(args):
    typename = {"f": "file", "d": "directory", "l": "symbolic link"}
    with Archive().open(args.archive) as archive:
        fi = archive.manifest.find(args.entry)
        if not fi:
            raise ArchiveReadError("%s: not found in archive" % args.entry)
        infolines = []
        infolines.append("Path:   %s" % fi.path)
        infolines.append("Type:   %s" % typename[fi.type])
        infolines.append("Mode:   %s" % stat.filemode(fi.st_mode))
        infolines.append("Owner:  %s:%s (%d:%d)"
                         % (fi.uname, fi.gname, fi.uid, fi.gid))
        mtime = datetime.datetime.fromtimestamp(fi.mtime)
        infolines.append("Mtime:  %s" % mtime.strftime("%Y-%m-%d %H:%M:%S"))
        if fi.is_file():
            infolines.append("Size:   %d" % fi.size)
        if fi.is_symlink():
            infolines.append("Target: %s" % fi.target)
        print(*infolines, sep="\n")
    return 0

def add_parser(subparsers):
    parser = subparsers.add_parser('info',
                                   help=("show informations about "
                                         "an entry in the archive"))
    parser.add_argument('archive', type=Path,
                        help=("path to the archive file"))
    parser.add_argument('entry', type=Path,
                        help=("path of the entry"))
    parser.set_defaults(func=info)
