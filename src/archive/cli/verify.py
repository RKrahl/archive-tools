"""Implement the verify subcommand.
"""

from pathlib import Path
from archive.archive import Archive


def verify(args):
    with Archive().open(args.archive) as archive:
        archive.verify()
    return 0

def add_parser(subparsers):
    parser = subparsers.add_parser('verify',
                                   help="verify integrity of the archive")
    parser.add_argument('archive', type=Path,
                        help=("path to the archive file"))
    parser.set_defaults(func=verify)
