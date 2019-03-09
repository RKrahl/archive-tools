#! /usr/bin/python

import argparse
from pathlib import Path
from archive import Archive

argparser = argparse.ArgumentParser()
subparsers = argparser.add_subparsers(title='subcommands')


def create(args):
    if args.compression == 'none':
        args.compression = ''
    mode = 'x:%s' % args.compression
    archive = Archive(args.archive, mode, args.files, args.basedir)

create_parser = subparsers.add_parser('create', help="create the archive")
create_parser.add_argument('--compression',
                           choices=['none', 'gz', 'bz2', 'xz'], default='gz',
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


def ls(args):
    archive = Archive(args.archive, "r")
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

ls_parser = subparsers.add_parser('ls', help="list files in the archive")
ls_parser.add_argument('archive',
                       help=("path to the archive file"), type=Path)
ls_parser.set_defaults(func=ls)


args = argparser.parse_args()
if not hasattr(args, "func"):
    argparser.error("subcommand is required")
args.func(args)
