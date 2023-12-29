"""Implement the create subcommand.
"""

from pathlib import Path
from archive.archive import Archive, DedupMode


def create(args):
    if args.compression == 'none':
        args.compression = ''
    archive = Archive().create(args.archive, args.compression, args.files,
                               basedir=args.basedir, workdir=args.directory,
                               excludes=args.exclude,
                               dedup=DedupMode(args.deduplicate),
                               tags=args.tag)
    return 0

def add_parser(subparsers):
    parser = subparsers.add_parser('create', help="create the archive")
    parser.add_argument('--directory', type=Path,
                        help=("change directory prior creating the archive"))
    parser.add_argument('--tag', action='append',
                        help=("user defined tags to mark the archive"))
    parser.add_argument('--compression',
                        choices=['none', 'gz', 'bz2', 'xz'],
                        help=("compression mode"))
    parser.add_argument('--basedir', type=Path,
                        help=("common base directory in the archive"))
    parser.add_argument('--exclude', type=Path, action='append',
                        help=("exclude this path"))
    parser.add_argument('--deduplicate',
                        choices=[d.value for d in DedupMode], default='link',
                        help=("when to use hard links to duplicate files"))
    parser.add_argument('archive', type=Path,
                        help=("path to the archive file"))
    parser.add_argument('files', nargs='+', type=Path,
                        help="files to add to the archive")
    parser.set_defaults(func=create)
