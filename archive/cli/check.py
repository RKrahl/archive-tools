"""Implement the check subcommand.
"""

from pathlib import Path
import sys
from archive.archive import Archive
from archive.exception import ArgError
from archive.manifest import FileInfo


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
    return 0

def add_parser(subparsers):
    parser = subparsers.add_parser('check',
                                   help="check if files are in the archive")
    parser.add_argument('--prefix', type=Path, default=Path(""),
                        help=("prefix for the path in the archive "
                              "of files to be checked"))
    parser.add_argument('--present', action='store_true',
                        help=("show files present in the archive, "
                              "rather then missing ones"))
    parser.add_argument('--stdin', action='store_true',
                        help=("read files to be checked from stdin, "
                              "rather then from the command line"))
    parser.add_argument('archive', type=Path,
                        help=("path to the archive file"))
    parser.add_argument('files', nargs='*', type=Path,
                        help="files to be checked")
    parser.set_defaults(func=check)
