#! /usr/bin/python

import argparse
import datetime
from pathlib import Path
import stat
import sys
import warnings
from archive.archive import Archive, DedupMode
from archive.exception import *
from archive.manifest import FileInfo

argparser = argparse.ArgumentParser()
subparsers = argparser.add_subparsers(title='subcommands', dest='subcmd')


suffix_map = {
    '.tar': 'none',
    '.tar.gz': 'gz',
    '.tar.bz2': 'bz2',
    '.tar.xz': 'xz',
}
"""Map path suffix to compression mode."""

class ArgError(Exception):
    pass


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


def create(args):
    if args.compression is None:
        try:
            args.compression = suffix_map["".join(args.archive.suffixes)]
        except KeyError:
            # Last ressort default
            args.compression = 'gz'
    if args.compression == 'none':
        args.compression = ''
    archive = Archive().create(args.archive, args.compression, args.files, 
                               basedir=args.basedir, excludes=args.exclude, 
                               dedup=DedupMode(args.deduplicate))

create_parser = subparsers.add_parser('create', help="create the archive")
create_parser.add_argument('--compression',
                           choices=['none', 'gz', 'bz2', 'xz'],
                           help=("compression mode"))
create_parser.add_argument('--basedir', type=Path,
                           help=("common base directory in the archive"))
create_parser.add_argument('--exclude', type=Path, action='append',
                           help=("exclude this path"))
create_parser.add_argument('--deduplicate',
                           choices=[d.value for d in DedupMode], default='link',
                           help=("when to use hard links to duplicate files"))
create_parser.add_argument('archive', type=Path,
                           help=("path to the archive file"))
create_parser.add_argument('files', nargs='+', type=Path,
                           help="files to add to the archive")
create_parser.set_defaults(func=create)


def verify(args):
    with Archive().open(args.archive) as archive:
        archive.verify()

verify_parser = subparsers.add_parser('verify',
                                      help="verify integrity of the archive")
verify_parser.add_argument('archive', type=Path,
                           help=("path to the archive file"))
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

ls_parser = subparsers.add_parser('ls', help="list files in the archive")
ls_parser.add_argument('--format', choices=['ls', 'checksum'], default='ls',
                       help=("output style"))
ls_parser.add_argument('--checksum',
                       help=("hash algorithm"))
ls_parser.add_argument('archive', type=Path,
                       help=("path to the archive file"))
ls_parser.set_defaults(func=ls)


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

info_parser = subparsers.add_parser('info',
                                    help=("show informations about "
                                          "an entry in the archive"))
info_parser.add_argument('archive', type=Path,
                         help=("path to the archive file"))
info_parser.add_argument('entry', type=Path,
                         help=("path of the entry"))
info_parser.set_defaults(func=info)


def _matches(prefix, fi, entry):
    if prefix / fi.path != entry.path or fi.type != entry.type:
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
    if args.stdin:
        if args.files:
            raise ArgError("can't accept both, --stdin and the files argument")
        files = [Path(l.strip()) for l in sys.stdin]
    else:
        if not args.files:
            raise ArgError("either --stdin or the files argument is required")
        files = args.files
    with Archive().open(args.archive) as archive:
        metadata = { Path(md) for md in archive.manifest.metadata }
        FileInfo.Checksums = archive.manifest.checksums
        file_iter = FileInfo.iterpaths(files, set())
        skip = None
        while True:
            try:
                fi = file_iter.send(skip)
            except StopIteration:
                break
            skip = False
            entry = archive.manifest.find(args.prefix / fi.path)
            if (args.prefix / fi.path in metadata or 
                entry and _matches(args.prefix, fi, entry)):
                if args.present and not fi.is_dir():
                    print(str(fi.path))
            else:
                if not args.present:
                    print(str(fi.path))
                if fi.is_dir():
                    skip = True

check_parser = subparsers.add_parser('check',
                                     help="check if files are in the archive")
check_parser.add_argument('--prefix', type=Path, default=Path(""),
                          help=("prefix for the path in the archive "
                                "of files to be checked"))
check_parser.add_argument('--present', action='store_true',
                          help=("show files present in the archive, "
                                "rather then missing ones"))
check_parser.add_argument('--stdin', action='store_true',
                          help=("read files to be checked from stdin, "
                                "rather then from the command line"))
check_parser.add_argument('archive', type=Path,
                          help=("path to the archive file"))
check_parser.add_argument('files', nargs='*', type=Path,
                          help="files to be checked")
check_parser.set_defaults(func=check)


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
