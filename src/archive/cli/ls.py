"""Implement the ls subcommand.
"""

from pathlib import Path
from archive.archive import Archive
from archive.exception import ArchiveReadError


def ls_ls_format(archive):
    items = []
    l_ug = 0
    l_s = 0
    for fi in archive.manifest:
        elems = tuple(str(fi).split("  "))
        l_ug = max(l_ug, len(elems[1]))
        l_s = max(l_s, len(elems[2]))
        items.append(elems)
    format_str = "%%s  %%%ds  %%%ds  %%s  %%s" % (l_ug, l_s)
    for i in items:
        print(format_str % i)

def ls_checksum_format(archive, algorithm):
    for fi in archive.manifest:
        if not fi.is_file():
            continue
        print("%s  %s" % (fi.checksum[algorithm], fi.path))

def ls(args):
    with Archive().open(args.archive) as archive:
        if args.format == 'ls':
            ls_ls_format(archive)
        elif args.format == 'checksum':
            if not args.checksum:
                args.checksum = archive.manifest.checksums[0]
            else:
                if args.checksum not in archive.manifest.checksums:
                    raise ArchiveReadError("Checksums using '%s' hashes "
                                           "not available" % args.checksum)
            ls_checksum_format(archive, args.checksum)
        else:
            raise ValueError("invalid format '%s'" % args.format)
    return 0

def add_parser(subparsers):
    parser = subparsers.add_parser('ls', help="list files in the archive")
    parser.add_argument('--format', choices=['ls', 'checksum'], default='ls',
                        help=("output style"))
    parser.add_argument('--checksum',
                        help=("hash algorithm"))
    parser.add_argument('archive', type=Path,
                        help=("path to the archive file"))
    parser.set_defaults(func=ls)
