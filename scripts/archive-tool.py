#! /usr/bin/python

import argparse
import datetime
from pathlib import Path
import sys
from archive import Archive
from archive.exception import *
from archive.manifest import FileInfo
from archive.tools import modstr

argparser = argparse.ArgumentParser()
subparsers = argparser.add_subparsers(title='subcommands', dest='subcmd')


suffix_map = {
    '.tar': 'none',
    '.tar.gz': 'gz',
    '.tar.bz2': 'bz2',
    '.tar.xz': 'xz',
}
"""Map path suffix to compression mode."""

def create(args):
    if args.compression is None:
        try:
            args.compression = suffix_map["".join(args.archive.suffixes)]
        except KeyError:
            # Last ressort default
            args.compression = 'gz'
    if args.compression == 'none':
        args.compression = ''
    mode = 'x:%s' % args.compression
    archive = Archive(args.archive, mode, args.files, args.basedir)

create_parser = subparsers.add_parser('create', help="create the archive")
create_parser.add_argument('--compression',
                           choices=['none', 'gz', 'bz2', 'xz'],
                           help=("compression mode"))
create_parser.add_argument('--basedir',
                           help=("common base directory in the archive"))
create_parser.add_argument('archive',
                           help=("path to the archive file"), type=Path)
create_parser.add_argument('files', nargs='+', type=Path,
                           help="files to add to the archive")
create_parser.set_defaults(func=create)


def verify(args):
    archive = Archive(args.archive, "r")
    archive.verify()

verify_parser = subparsers.add_parser('verify',
                                      help="verify integrity of the archive")
verify_parser.add_argument('archive',
                           help=("path to the archive file"), type=Path)
verify_parser.set_defaults(func=verify)


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
    archive = Archive(args.archive, "r")
    if args.format == 'ls':
        ls_ls_format(archive)
    elif args.format == 'checksum':
        if not args.checksum:
            args.checksum = archive.manifest.head['Checksums'][0]
        else:
            if args.checksum not in archive.manifest.head['Checksums']:
                raise ArchiveReadError("Checksums using '%s' hashes "
                                       "not available" % args.checksum)
        ls_checksum_format(archive, args.checksum)
    else:
        raise ValueError("invalid format '%s'" % args.format)

ls_parser = subparsers.add_parser('ls', help="list files in the archive")
ls_parser.add_argument('--format',
                       choices=['ls', 'checksum'], default='ls',
                       help=("output style"))
ls_parser.add_argument('--checksum',
                       help=("hash algorithm"))
ls_parser.add_argument('archive',
                       help=("path to the archive file"), type=Path)
ls_parser.set_defaults(func=ls)


def info(args):
    typename = {"f": "file", "d": "directory", "l": "symbolic link"}
    archive = Archive(args.archive, "r")
    fi = archive.manifest.find(args.entry)
    if not fi:
        raise ArchiveReadError("%s: not found in archive" % args.entry)
    infolines = []
    infolines.append("Path:   %s" % fi.path)
    infolines.append("Type:   %s" % typename[fi.type])
    infolines.append("Mode:   %s" % modstr(fi.type, fi.mode))
    infolines.append("Owner:  %s:%s (%d:%d)"
                     % (fi.uname, fi.gname, fi.uid, fi.gid))
    mtime = datetime.datetime.fromtimestamp(fi.mtime)
    infolines.append("Mtime:  %s" % mtime.strftime("%Y-%m-%d %H:%M:%S"))
    if fi.is_file():
        infolines.append("Size:   %d" % fi.size)
    if fi.is_symlink():
        infolines.append("Target: %s" % fi.target)
    print(*infolines, sep="\n")

info_parser = subparsers.add_parser('info',
                                    help=("show informations about "
                                          "an entry in the archive"))
info_parser.add_argument('archive',
                         help=("path to the archive file"), type=Path)
info_parser.add_argument('entry',
                         help=("path of the entry"), type=Path)
info_parser.set_defaults(func=info)


def _matches(fi, entry):
    if fi.path != entry.path or fi.type != entry.type:
        return False
    if fi.is_file():
        if (fi.size != entry.size or fi.checksum != entry.checksum or 
            fi.mtime > entry.mtime):
            return False
    if fi.is_symlink():
        if fi.target != entry.target:
            return False
    return True

def check(args):
    archive = Archive(args.archive, "r")
    FileInfo.Checksums = archive.manifest.head["Checksums"]
    file_iter = FileInfo.iterpaths(args.files)
    skip = None
    while True:
        try:
            fi = file_iter.send(skip)
        except StopIteration:
            break
        skip = False
        entry = archive.manifest.find(fi.path)
        if entry and _matches(fi, entry):
            if args.present and not fi.is_dir():
                print(str(fi.path))
        else:
            if not args.present:
                print(str(fi.path))
            if fi.is_dir():
                skip = True

check_parser = subparsers.add_parser('check',
                                     help="check if files are in the archive")
check_parser.add_argument('--present', action='store_true',
                          help=("show files present in the archive, "
                                "rather then missing ones"))
check_parser.add_argument('archive',
                          help=("path to the archive file"), type=Path)
check_parser.add_argument('files', nargs='+', type=Path,
                          help="files to be checked")
check_parser.set_defaults(func=check)


args = argparser.parse_args()
if not hasattr(args, "func"):
    argparser.error("subcommand is required")
try:
    args.func(args)
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
